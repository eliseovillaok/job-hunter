"""
web/persist.py — Cuentas y datos guardados: lo que sobrevive a cerrar el navegador.

Las rutas hablan con un `Store`. Hay dos:
- `SupabaseStore` (web/supa.py): Supabase Auth + Postgres con RLS + Storage. Es el de verdad.
- `MemoryStore` (acá): mismo contrato en memoria del proceso, para los tests y para el modo demo sin
  Supabase. Un reinicio lo borra todo.

Reglas que valen para los dos:
- La identidad sale siempre del token de la sesión (`User`), nunca de un dato que mande el navegador.
- Lo que el usuario no debe poder falsear ni borrar (uso del cupo, corridas) lo escribe solo el servidor.
- La clave de Gemini y la contraseña de correo no se guardan nunca.
"""

from __future__ import annotations

import copy
import hashlib
import secrets
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional

import normalize
from ai_engine import FactorScore, ScoredJob
from scrapers import JobPosting

CV_BUCKET = "cv-documents"
FREE_PLAN = "free"


# ─── Tipos que cruzan la frontera ────────────────────────────────────────────
@dataclass(frozen=True)
class User:
    id: str
    email: str
    access_token: str = field(default="", repr=False)


@dataclass(frozen=True)
class Tokens:
    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    expires_in: int
    user: User


@dataclass(frozen=True)
class Plan:
    """Límites del plan. None = sin límite."""
    id: str
    monthly_search_limit: Optional[int] = None
    sources_per_search_limit: Optional[int] = None
    results_per_search_limit: Optional[int] = None


@dataclass
class Account:
    """Lo guardado de un usuario, para rearmar su sesión al volver."""
    plan: Plan
    cv: Optional[dict] = None             # {id, name, mime, sha, parsed, created_at}
    profile: Optional[dict] = None        # CandidateProfile.to_dict()
    profile_source: str = "cv"            # cv | manual
    profile_confirmed: bool = False
    preferences: Optional[dict] = None    # {terms, modalities, locations, job_languages, portals, min_score, eval_limit}


class AuthError(Exception):
    """Un pedido de cuentas que no salió. `code` es estable y se traduce en la interfaz."""
    CODES = ("invalid_credentials", "email_not_confirmed", "weak_password", "invalid_email",
             "rate_limited", "link_invalid", "unavailable")

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code if code in self.CODES else "unavailable"


class StoreError(Exception):
    """La base de datos o el almacenamiento no respondieron como se esperaba."""


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def month_start(now: datetime | None = None) -> datetime:
    now = now or now_utc()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def next_month_start(now: datetime | None = None) -> datetime:
    start = month_start(now)
    return start.replace(year=start.year + 1, month=1) if start.month == 12 else start.replace(month=start.month + 1)


# ─── Ofertas: identidad y foto para el historial ─────────────────────────────
def job_key(job: JobPosting) -> str:
    """Huella de una oferta mientras no exista el inventario (Fase 3): empresa + título normalizados,
    la misma regla con la que se deduplica."""
    def norm(text: str) -> str:
        return " ".join(normalize.strip_accents((text or "").lower()).split())
    return hashlib.sha256(f"{norm(job.title)}|{norm(job.company)}".encode()).hexdigest()[:32]


def scored_to_dict(sj: ScoredJob) -> dict:
    """Lo mínimo para volver a mostrar la oferta: sin la descripción (se lee en el portal original)."""
    job = {k: v for k, v in asdict(sj.job).items() if k != "description"}
    return {
        "job": job, "score": sj.score, "evaluated": sj.evaluated, "summary": sj.summary,
        "match_reasons": list(sj.match_reasons), "missing_skills": list(sj.missing_skills),
        "factors": {k: asdict(v) for k, v in sj.factors.items()} if sj.factors else None,
    }


def scored_from_dict(d: dict) -> ScoredJob:
    j = dict(d.get("job") or {})
    job = JobPosting(
        id=str(j.get("id") or ""), title=str(j.get("title") or ""), company=str(j.get("company") or ""),
        description="", location=str(j.get("location") or ""), remote=bool(j.get("remote")),
        url=str(j.get("url") or ""), source=str(j.get("source") or ""), published_at=j.get("published_at"),
        salary=j.get("salary"), tags=list(j.get("tags") or []), language=j.get("language") or "unknown",
        seniority=j.get("seniority") or "unknown", modality=j.get("modality") or "unknown",
    )
    factors = d.get("factors")
    return ScoredJob(
        job=job, score=int(d.get("score") or 0), match_reasons=list(d.get("match_reasons") or []),
        missing_skills=list(d.get("missing_skills") or []), cover_letter=None, summary=str(d.get("summary") or ""),
        evaluated=bool(d.get("evaluated", True)),
        factors={k: FactorScore(int(v.get("score") or 0), v.get("evidence_job") or "", v.get("evidence_cv") or "")
                 for k, v in factors.items()} if isinstance(factors, dict) else None,
    )


# ─── En memoria ──────────────────────────────────────────────────────────────
@dataclass
class _MemUser:
    id: str
    email: str
    password_hash: str
    locale: str
    confirmed: bool
    created_at: datetime = field(default_factory=now_utc)


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


class MemoryStore:
    """El mismo contrato que SupabaseStore, en memoria. Para tests y para el modo demo sin Supabase.

    No es para producción: no persiste nada y las contraseñas no llevan un hash lento."""

    def __init__(self, plan: Plan | None = None, confirm_signups: bool = False, min_password: int = 8):
        self.plan_row = plan or Plan(FREE_PLAN)
        self.confirm_signups = confirm_signups
        self.min_password = min_password
        self.fail = False            # los tests lo prenden para simular una caída
        self.sent_links: list[tuple[str, str, str]] = []   # (email, tipo, token_hash): lo que "se envió"
        self._lock = threading.RLock()
        self._users: dict[str, _MemUser] = {}
        self._access: dict[str, str] = {}
        self._refresh: dict[str, str] = {}
        self._links: dict[str, tuple[str, str]] = {}
        self._data: dict[str, dict] = {}
        self.deletions: list[dict] = []

    # ─── Auth ────────────────────────────────────────────────────────────
    def _check(self) -> None:
        if self.fail:
            raise StoreError("memory store is down")

    def _issue(self, u: _MemUser) -> Tokens:
        access, refresh = f"mem-a-{secrets.token_urlsafe(16)}", f"mem-r-{secrets.token_urlsafe(16)}"
        self._access[access], self._refresh[refresh] = u.id, u.id
        return Tokens(access, refresh, 3600, User(u.id, u.email, access))

    def _by_email(self, email: str) -> Optional[_MemUser]:
        return next((u for u in self._users.values() if u.email == email.strip().lower()), None)

    def _send(self, email: str, kind: str, user_id: str) -> None:
        token = secrets.token_hex(16)
        self._links[token] = (user_id, kind)
        self.sent_links.append((email, kind, token))

    def sign_up(self, email: str, password: str, locale: str) -> Optional[Tokens]:
        with self._lock:
            self._check()
            email = email.strip().lower()
            if "@" not in email or "." not in email.split("@")[-1]:
                raise AuthError("invalid_email")
            if len(password) < self.min_password or password.isalpha() or password.isdigit():
                raise AuthError("weak_password")
            existing = self._by_email(email)
            if existing:
                return None            # como Supabase: no revela que la cuenta existe
            u = _MemUser(secrets.token_hex(16), email, _hash(password), locale if locale in ("es", "en") else "en",
                         confirmed=not self.confirm_signups)
            self._users[u.id] = u
            if self.confirm_signups:
                self._send(email, "email", u.id)
                return None
            return self._issue(u)

    def sign_in(self, email: str, password: str) -> Tokens:
        with self._lock:
            self._check()
            u = self._by_email(email)
            if not u or u.password_hash != _hash(password):
                raise AuthError("invalid_credentials")
            if not u.confirmed:
                raise AuthError("email_not_confirmed")
            return self._issue(u)

    def refresh(self, refresh_token: str) -> Tokens:
        with self._lock:
            self._check()
            # Como Supabase, tolera que dos pedidos paralelos renueven con el mismo token.
            uid = self._refresh.get(refresh_token)
            if not uid or uid not in self._users:
                raise AuthError("invalid_credentials")
            return self._issue(self._users[uid])

    def verify_link(self, token_hash: str, kind: str) -> Tokens:
        with self._lock:
            self._check()
            uid, link_kind = self._links.pop(token_hash, (None, None))
            if not uid or link_kind != kind or uid not in self._users:
                raise AuthError("link_invalid")
            self._users[uid].confirmed = True
            return self._issue(self._users[uid])

    def resend_confirmation(self, email: str) -> None:
        with self._lock:
            u = self._by_email(email)
            if u and not u.confirmed:
                self._send(u.email, "email", u.id)

    def send_password_reset(self, email: str) -> None:
        with self._lock:
            u = self._by_email(email)
            if u:
                self._send(u.email, "recovery", u.id)

    def set_password(self, user: User, password: str) -> None:
        with self._lock:
            if len(password) < self.min_password or password.isalpha() or password.isdigit():
                raise AuthError("weak_password")
            self._users[user.id].password_hash = _hash(password)

    def user_for_token(self, access_token: str) -> Optional[User]:
        with self._lock:
            self._check()
            uid = self._access.get(access_token or "")
            u = self._users.get(uid) if uid else None
            return User(u.id, u.email, access_token) if u else None

    def sign_out(self, user: User) -> None:
        with self._lock:
            self._access.pop(user.access_token, None)

    # ─── Datos ───────────────────────────────────────────────────────────
    def _d(self, user_id: str) -> dict:
        return self._data.setdefault(user_id, {"cvs": [], "files": {}, "profile": None, "prefs": None,
                                               "runs": [], "usage": [], "jobs": {}})

    def account(self, user: User) -> Account:
        with self._lock:
            self._check()
            d = self._d(user.id)
            cv = next((c for c in d["cvs"] if c["is_current"]), None)
            prof = d["profile"] or {}
            return Account(
                plan=self.plan_row,
                cv={k: cv[k] for k in ("id", "name", "mime", "sha", "size", "parsed", "created_at")} if cv else None,
                profile=copy.deepcopy(prof.get("profile")), profile_source=prof.get("source", "cv"),
                profile_confirmed=bool(prof.get("confirmed")), preferences=copy.deepcopy(d["prefs"]),
            )

    def plan(self, user: User) -> Plan:
        return self.plan_row

    def _retire_current(self, d: dict) -> None:
        for old in d["cvs"]:
            if old["is_current"]:
                old.update(is_current=False, deleted_at=now_utc(), parsed_profile=None)
                d["files"].pop(old["id"], None)
                if (d["profile"] or {}).get("source") == "cv":
                    d["profile"] = None

    def save_cv(self, user: User, *, name: str, mime: str, data: bytes, sha: str) -> str:
        with self._lock:
            self._check()
            d = self._d(user.id)
            self._retire_current(d)
            cv_id = secrets.token_hex(16)
            d["cvs"].append({"id": cv_id, "name": name, "mime": mime, "sha": sha, "size": len(data), "parsed": False,
                             "parsed_profile": None, "parser_version": None, "is_current": True,
                             "deleted_at": None, "created_at": now_utc()})
            d["files"][cv_id] = data
            return cv_id

    def cv_bytes(self, user: User) -> Optional[bytes]:
        with self._lock:
            d = self._d(user.id)
            cv = next((c for c in d["cvs"] if c["is_current"]), None)
            return d["files"].get(cv["id"]) if cv else None

    def mark_cv_parsed(self, user: User, cv_id: str, parsed: dict, parser_version: str) -> None:
        with self._lock:
            for c in self._d(user.id)["cvs"]:
                if c["id"] == cv_id:
                    c.update(parsed=True, parsed_profile=copy.deepcopy(parsed), parser_version=parser_version)

    def delete_cv(self, user: User) -> None:
        with self._lock:
            self._check()
            self._retire_current(self._d(user.id))

    def save_profile(self, user: User, profile: dict, *, confirmed: bool, source: str,
                     cv_id: str | None = None) -> None:
        with self._lock:
            self._check()
            self._d(user.id)["profile"] = {"profile": copy.deepcopy(profile), "confirmed": confirmed, "source": source}

    def save_preferences(self, user: User, prefs: dict) -> None:
        with self._lock:
            self._check()
            self._d(user.id)["prefs"] = copy.deepcopy(prefs)

    def searches_used(self, user: User) -> int:
        with self._lock:
            start = month_start()
            return sum(1 for e in self._d(user.id)["usage"] if e >= start)

    def start_run(self, user_id: str, plan: Plan, meta: dict) -> Optional[str]:
        with self._lock:
            self._check()
            d = self._d(user_id)
            limit = plan.monthly_search_limit
            if limit is not None and sum(1 for e in d["usage"] if e >= month_start()) >= limit:
                return None
            run_id = secrets.token_hex(16)
            d["runs"].insert(0, {"id": run_id, "status": "running", "started_at": now_utc(), "finished_at": None,
                                 "query": copy.deepcopy(meta.get("query") or {}),
                                 "sources_requested": meta.get("sources_requested", 0), "sources_succeeded": 0,
                                 "jobs_seen": 0, "matches_created": 0, "error_summary": None,
                                 "funnel": None, "results": None, "lang": meta.get("lang")})
            d["usage"].append(now_utc())
            return run_id

    def finish_run(self, user_id: str, run_id: str, fields: dict) -> None:
        with self._lock:
            for r in self._d(user_id)["runs"]:
                if r["id"] == run_id:
                    r.update(copy.deepcopy(fields), finished_at=now_utc())

    def runs(self, user: User, limit: int = 30) -> list[dict]:
        with self._lock:
            return [{k: v for k, v in r.items() if k != "results"} for r in self._d(user.id)["runs"][:limit]]

    def run(self, user: User, run_id: str) -> Optional[dict]:
        with self._lock:
            r = next((r for r in self._d(user.id)["runs"] if r["id"] == run_id), None)
            return copy.deepcopy(r)

    def latest_run_with_results(self, user: User) -> Optional[dict]:
        with self._lock:
            r = next((r for r in self._d(user.id)["runs"] if r.get("results")), None)
            return copy.deepcopy(r)

    def job_states(self, user: User) -> dict[str, str]:
        with self._lock:
            return {k: v["state"] for k, v in self._d(user.id)["jobs"].items()}

    def set_job_state(self, user: User, key: str, state: Optional[str], job: dict, run_id: Optional[str]) -> None:
        with self._lock:
            self._check()
            jobs = self._d(user.id)["jobs"]
            if state is None:
                jobs.pop(key, None)
            else:
                jobs[key] = {"state": state, "job": copy.deepcopy(job), "search_run_id": run_id, "updated_at": now_utc()}

    def saved_jobs(self, user: User) -> list[dict]:
        with self._lock:
            items = [{"key": k, **copy.deepcopy(v)} for k, v in self._d(user.id)["jobs"].items() if v["state"] == "saved"]
            return sorted(items, key=lambda x: x["updated_at"], reverse=True)

    def export(self, user: User) -> dict:
        with self._lock:
            d = copy.deepcopy(self._d(user.id))
            for c in d["cvs"]:
                c.pop("parsed_profile", None)
            d.pop("files")
            return {"email": user.email, **d}

    def delete_account(self, user: User) -> None:
        with self._lock:
            self._check()
            record = {"requested_at": now_utc(), "completed_at": None}
            self.deletions.append(record)
            self._data.pop(user.id, None)
            self._users.pop(user.id, None)
            for table in (self._access, self._refresh):
                for tok in [t for t, uid in table.items() if uid == user.id]:
                    del table[tok]
            record["completed_at"] = now_utc()

    def ping(self) -> bool:
        return not self.fail


# ─── Cuál se usa ─────────────────────────────────────────────────────────────
_store = None
_store_lock = threading.Lock()


def get():
    """El store de la app: Supabase si está configurado; en memoria solo en modo demo; si no, None."""
    global _store
    with _store_lock:
        if _store is None:
            import demo
            from web import settings
            if settings.SUPABASE_URL and settings.SUPABASE_PUBLISHABLE_KEY and settings.SUPABASE_SECRET_KEY:
                from web.supa import SupabaseStore
                _store = SupabaseStore(settings.SUPABASE_URL, settings.SUPABASE_PUBLISHABLE_KEY,
                                       settings.SUPABASE_SECRET_KEY)
            elif demo.enabled():
                _store = MemoryStore(plan=demo.PLAN)
        return _store


def use(store) -> None:
    """Reemplaza el store (tests)."""
    global _store
    with _store_lock:
        _store = store
