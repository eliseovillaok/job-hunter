"""
web/supa.py — `SupabaseStore`: cuentas y datos sobre Supabase (Auth, Postgres con RLS y Storage).

Habla HTTP directo con las APIs documentadas de Supabase (Auth /auth/v1, PostgREST /rest/v1,
Storage /storage/v1) usando `requests`. El cliente oficial de Python guarda la sesión dentro de la
instancia: en un servidor que atiende a varias personas a la vez eso es estado compartido. Acá cada
llamada lleva su propio token y nada del usuario queda en el objeto.

Qué clave va en cada pedido:
- Lo que hace el usuario (su perfil, su CV, sus ofertas): clave publicable + su JWT → aplica RLS.
- Lo que no debe poder falsear (cupo, corridas) o lo que hace el sistema (borrar la cuenta):
  clave secreta, solo en el servidor.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
import uuid
from datetime import datetime
from http.cookiejar import DefaultCookiePolicy
from pathlib import PurePosixPath
from typing import Optional

import requests

from web.persist import (CV_BUCKET, FREE_PLAN, Account, AuthError, Plan, StoreError, Tokens, User, month_start,
                         now_utc)

log = logging.getLogger("jobhunter.supabase")

TIMEOUT = 10
TOKEN_CACHE_SECONDS = 60
TOKEN_CACHE_MAX = 5000
PLAN_CACHE_SECONDS = 60

_AUTH_CODES = {
    "invalid_credentials": "invalid_credentials",
    "invalid_grant": "invalid_credentials",
    "refresh_token_not_found": "invalid_credentials",
    "refresh_token_already_used": "invalid_credentials",
    "session_not_found": "invalid_credentials",
    "user_not_found": "invalid_credentials",
    "email_not_confirmed": "email_not_confirmed",
    "weak_password": "weak_password",
    "validation_failed": "invalid_email",
    "email_address_invalid": "invalid_email",
    "over_email_send_rate_limit": "rate_limited",
    "over_request_rate_limit": "rate_limited",
    "otp_expired": "link_invalid",
    "flow_state_expired": "link_invalid",
    "flow_state_not_found": "link_invalid",
}

_CV_COLUMNS = "id,original_filename,mime_type,content_sha256,file_size_bytes,status,created_at"
_RUN_COLUMNS = ("id,status,started_at,finished_at,query,sources_requested,sources_succeeded,jobs_seen,"
                "matches_created,error_summary,funnel,lang")


def _when(value) -> Optional[datetime]:
    return datetime.fromisoformat(value) if isinstance(value, str) and value else None


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False


class SupabaseStore:
    def __init__(self, url: str, publishable_key: str, secret_key: str, timeout: int = TIMEOUT):
        self.url = url.rstrip("/")
        self._pub = publishable_key
        self._secret = secret_key
        self.timeout = timeout
        self._http = requests.Session()
        # Supabase no usa cookies en estas APIs; si alguna llegara, no debe viajar al pedido de otro usuario.
        self._http.cookies.set_policy(DefaultCookiePolicy(allowed_domains=[]))
        self._tokens: dict[str, tuple[User, float]] = {}
        self._tokens_lock = threading.Lock()
        self._plan_cache: tuple[Plan, float] | None = None
        self._ping_cache: tuple[bool, float] | None = None

    # ─── HTTP ────────────────────────────────────────────────────────────
    def _headers(self, token: str | None, service: bool) -> dict:
        if service:
            h = {"apikey": self._secret}
            # Las claves nuevas (sb_secret_…) no son JWT: van solo en `apikey`. Las legacy, en los dos.
            if self._secret.startswith("eyJ"):
                h["Authorization"] = f"Bearer {self._secret}"
            return h
        h = {"apikey": self._pub}
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    def _call(self, method: str, path: str, *, token: str | None = None, service: bool = False,
              json=None, params=None, data: bytes | None = None, headers: dict | None = None) -> requests.Response:
        h = self._headers(token, service)
        if headers:
            h.update(headers)
        try:
            return self._http.request(method, f"{self.url}{path}", headers=h, json=json, params=params, data=data,
                                      timeout=self.timeout)
        except requests.RequestException as e:
            raise StoreError(f"{method} {path}: {type(e).__name__}") from None

    def _ok(self, r: requests.Response, what: str) -> requests.Response:
        if r.status_code >= 400:
            # Nunca el cuerpo completo: podría traer datos del usuario.
            code = ""
            try:
                code = str(r.json().get("code") or r.json().get("error_code") or "")
            except ValueError:
                pass
            raise StoreError(f"{what}: HTTP {r.status_code} {code}".strip())
        return r

    def _rest(self, method: str, table: str, user: User | None = None, *, service: bool = False,
              params=None, json=None, prefer: str = "") -> list | dict | None:
        headers = {"Prefer": prefer} if prefer else None
        r = self._ok(self._call(method, f"/rest/v1/{table}", token=user.access_token if user else None,
                                service=service, params=params, json=json, headers=headers), f"{method} {table}")
        if r.status_code == 204 or not r.content:
            return None
        return r.json()

    # ─── Auth ────────────────────────────────────────────────────────────
    def _auth(self, method: str, path: str, *, json=None, token: str | None = None, service: bool = False):
        r = self._call(method, f"/auth/v1/{path}", json=json, token=token, service=service)
        if r.status_code >= 500:
            raise AuthError("unavailable")
        if r.status_code >= 400:
            try:
                body = r.json()
            except ValueError:
                body = {}
            raise AuthError(_AUTH_CODES.get(str(body.get("error_code") or body.get("error") or ""), "unavailable"))
        return r.json() if r.content else {}

    def _auth_safe(self, *args, **kwargs):
        try:
            return self._auth(*args, **kwargs)
        except StoreError:
            raise AuthError("unavailable") from None

    @staticmethod
    def _tokens_from(body: dict) -> Tokens:
        u = body.get("user") or {}
        user = User(str(u.get("id")), str(u.get("email") or ""), body["access_token"])
        return Tokens(body["access_token"], body["refresh_token"], int(body.get("expires_in") or 3600), user)

    def sign_up(self, email: str, password: str, locale: str) -> Optional[Tokens]:
        body = self._auth_safe("POST", "signup", json={"email": email.strip(), "password": password,
                                                       "data": {"locale": locale}})
        # Con confirmación por correo activada no vuelve sesión. Si la cuenta ya existía, Supabase
        # responde igual (sin revelarlo): en los dos casos se pide revisar el correo.
        return self._tokens_from(body) if body.get("access_token") else None

    def sign_in(self, email: str, password: str) -> Tokens:
        return self._tokens_from(self._auth_safe("POST", "token?grant_type=password",
                                                 json={"email": email.strip(), "password": password}))

    def refresh(self, refresh_token: str) -> Tokens:
        return self._tokens_from(self._auth_safe("POST", "token?grant_type=refresh_token",
                                                 json={"refresh_token": refresh_token}))

    def verify_link(self, token_hash: str, kind: str) -> Tokens:
        return self._tokens_from(self._auth_safe("POST", "verify", json={"type": kind, "token_hash": token_hash}))

    def resend_confirmation(self, email: str) -> None:
        self._auth_safe("POST", "resend", json={"type": "signup", "email": email.strip()})

    def send_password_reset(self, email: str) -> None:
        self._auth_safe("POST", "recover", json={"email": email.strip()})

    def set_password(self, user: User, password: str) -> None:
        self._auth_safe("PUT", "user", json={"password": password}, token=user.access_token)

    def user_for_token(self, access_token: str) -> Optional[User]:
        """El usuario de este token, o None si venció o se revocó. Se valida contra Auth (que también
        rechaza sesiones cerradas) y el resultado se recuerda un minuto."""
        if not access_token:
            return None
        key = hashlib.sha256(access_token.encode()).hexdigest()
        now = time.monotonic()
        with self._tokens_lock:
            hit = self._tokens.get(key)
            if hit and hit[1] > now:
                return hit[0]
        r = self._call("GET", "/auth/v1/user", token=access_token)
        if r.status_code in (401, 403):
            return None
        self._ok(r, "GET user")
        body = r.json()
        user = User(str(body["id"]), str(body.get("email") or ""), access_token)
        with self._tokens_lock:
            if len(self._tokens) >= TOKEN_CACHE_MAX:
                for k in [k for k, (_, exp) in self._tokens.items() if exp <= now] or list(self._tokens)[:500]:
                    self._tokens.pop(k, None)
            self._tokens[key] = (user, now + TOKEN_CACHE_SECONDS)
        return user

    def _forget(self, user_id: str) -> None:
        with self._tokens_lock:
            for k in [k for k, (u, _) in self._tokens.items() if u.id == user_id]:
                del self._tokens[k]

    def sign_out(self, user: User) -> None:
        self._forget(user.id)
        try:
            self._call("POST", "/auth/v1/logout?scope=local", token=user.access_token)
        except StoreError:
            log.warning("logout: Auth no respondió; las cookies se borran igual")

    # ─── Plan ────────────────────────────────────────────────────────────
    def plan(self, user: User | None = None) -> Plan:
        """Todos están en el plan gratuito hasta que existan las suscripciones (Fase 6)."""
        now = time.monotonic()
        if self._plan_cache and self._plan_cache[1] > now:
            return self._plan_cache[0]
        rows = self._rest("GET", "plans", service=True, params={"id": f"eq.{FREE_PLAN}", "select": "*"}) or []
        if not rows:
            raise StoreError("the free plan is missing from the catalog")
        row = rows[0]
        plan = Plan(row["id"], row.get("monthly_search_limit"), row.get("sources_per_search_limit"),
                    row.get("results_per_search_limit"))
        self._plan_cache = (plan, now + PLAN_CACHE_SECONDS)
        return plan

    # ─── Cuenta y perfil ─────────────────────────────────────────────────
    def account(self, user: User) -> Account:
        rows = self._rest("GET", "profiles", user, params={
            "select": (f"id,cv:cv_documents!cv_documents_user_id_fkey({_CV_COLUMNS}),"
                       "candidate_profiles(profile,source,confirmed),search_preferences(*)"),
            "cv.is_current": "is.true", "cv.deleted_at": "is.null",
        }) or []
        row = rows[0] if rows else {}
        cvs = row.get("cv") or []
        cp = row.get("candidate_profiles") or None
        sp = row.get("search_preferences") or None
        cv = cvs[0] if cvs else None
        return Account(
            plan=self.plan(user),
            cv={"id": cv["id"], "name": cv["original_filename"], "mime": cv["mime_type"], "sha": cv["content_sha256"],
                "size": cv.get("file_size_bytes") or 0, "parsed": cv["status"] == "parsed",
                "created_at": _when(cv["created_at"])} if cv else None,
            profile=cp.get("profile") if cp else None,
            profile_source=(cp or {}).get("source") or "cv",
            profile_confirmed=bool((cp or {}).get("confirmed")),
            preferences=self._prefs_from_row(sp) if sp else None,
        )

    def _current_cvs(self, user: User) -> list[dict]:
        return self._rest("GET", "cv_documents", user, params={
            "select": "id,storage_path", "is_current": "is.true", "deleted_at": "is.null"}) or []

    def _remove_files(self, user: User, paths: list[str]) -> None:
        paths = [p for p in paths if p]
        if paths:
            self._ok(self._call("DELETE", f"/storage/v1/object/{CV_BUCKET}", token=user.access_token,
                                json={"prefixes": paths}), "delete cv file")

    def _retire_current(self, user: User) -> None:
        """El CV anterior deja de ser el vigente y su archivo se borra en el acto (no hay copia que
        retener). El perfil que la IA sacó de ese CV se va con él."""
        old = self._current_cvs(user)
        if not old:
            return
        self._remove_files(user, [c.get("storage_path") for c in old])
        self._rest("PATCH", "cv_documents", user, params={"id": f"in.({','.join(c['id'] for c in old)})"},
                   json={"is_current": False, "deleted_at": now_utc().isoformat(), "storage_path": None,
                         "raw_text": None, "parsed_profile": None}, prefer="return=minimal")
        self._rest("DELETE", "candidate_profiles", user, params={"source": "eq.cv"}, prefer="return=minimal")

    def save_cv(self, user: User, *, name: str, mime: str, data: bytes, sha: str) -> str:
        self._retire_current(user)
        cv_id = str(uuid.uuid4())
        path = f"{user.id}/{cv_id}{PurePosixPath(name).suffix.lower()}"
        self._ok(self._call("POST", f"/storage/v1/object/{CV_BUCKET}/{path}", token=user.access_token, data=data,
                            headers={"Content-Type": mime, "x-upsert": "false"}), "upload cv")
        self._rest("POST", "cv_documents", user, prefer="return=minimal", json={
            "id": cv_id, "user_id": user.id, "storage_path": path, "original_filename": name, "mime_type": mime,
            "file_size_bytes": len(data), "content_sha256": sha, "status": "uploaded", "is_current": True})
        return cv_id

    def cv_bytes(self, user: User) -> Optional[bytes]:
        cvs = self._current_cvs(user)
        if not cvs or not cvs[0].get("storage_path"):
            return None
        r = self._ok(self._call("GET", f"/storage/v1/object/{CV_BUCKET}/{cvs[0]['storage_path']}",
                                token=user.access_token), "download cv")
        return r.content

    def mark_cv_parsed(self, user: User, cv_id: str, parsed: dict, parser_version: str) -> None:
        self._rest("PATCH", "cv_documents", user, params={"id": f"eq.{cv_id}"}, prefer="return=minimal",
                   json={"parsed_profile": parsed, "parser_version": parser_version, "status": "parsed"})

    def delete_cv(self, user: User) -> None:
        self._retire_current(user)

    def save_profile(self, user: User, profile: dict, *, confirmed: bool, source: str,
                     cv_id: str | None = None) -> None:
        langs = [{"language": x.get("language"), "level": x.get("level")} for x in profile.get("languages") or []]
        location = profile.get("location")
        self._rest("POST", "candidate_profiles", user, params={"on_conflict": "user_id"},
                   prefer="resolution=merge-duplicates,return=minimal", json={
                       "user_id": user.id, "cv_document_id": cv_id if source == "cv" and _is_uuid(cv_id or "") else None,
                       "source": source, "confirmed": confirmed,
                       "summary": profile.get("summary") or None,
                       "years_experience": profile.get("years_experience"),
                       "seniority": profile.get("seniority"),
                       "skills": [s.get("name") for s in profile.get("skills") or []],
                       "languages": langs,
                       "target_titles": profile.get("target_roles") or [],
                       "locations": [location] if location and location != "unknown" else [],
                       "profile": profile,
                   })

    @staticmethod
    def _prefs_from_row(row: dict) -> dict:
        return {"terms": row.get("keywords") or [], "modalities": row.get("work_modes") or [],
                "locations": ", ".join(row.get("locations") or []), "job_languages": row.get("job_languages") or [],
                "portals": row.get("source_ids") or [], "min_score": row.get("min_score"),
                "eval_limit": row.get("results_limit")}

    def save_preferences(self, user: User, prefs: dict) -> None:
        self._rest("POST", "search_preferences", user, params={"on_conflict": "user_id"},
                   prefer="resolution=merge-duplicates,return=minimal", json={
                       "user_id": user.id, "keywords": prefs.get("terms") or [],
                       "work_modes": prefs.get("modalities") or [],
                       "remote_only": prefs.get("modalities") == ["remote"],
                       "locations": [x.strip() for x in (prefs.get("locations") or "").split(",") if x.strip()],
                       "job_languages": prefs.get("job_languages") or [],
                       "source_ids": prefs.get("portals") or [],
                       "min_score": prefs.get("min_score"), "results_limit": prefs.get("eval_limit"),
                   })

    # ─── Búsquedas ───────────────────────────────────────────────────────
    def searches_used(self, user: User) -> int:
        rows = self._rest("GET", "usage_events", user, params={
            "select": "quantity", "event_type": "eq.search_run", "created_at": f"gte.{month_start().isoformat()}"})
        return sum(int(r.get("quantity") or 0) for r in rows or [])

    def start_run(self, user_id: str, plan: Plan, meta: dict) -> Optional[str]:
        """Reserva una búsqueda del cupo mensual y crea la corrida. None = no quedan búsquedas."""
        result = self._rest("POST", "rpc/start_search_run", service=True, json={
            "p_user": user_id, "p_monthly_limit": plan.monthly_search_limit, "p_run": meta})
        return str(result) if result else None

    def finish_run(self, user_id: str, run_id: str, fields: dict) -> None:
        self._rest("PATCH", "search_runs", service=True, prefer="return=minimal",
                   params={"id": f"eq.{run_id}", "user_id": f"eq.{user_id}"},
                   json={**fields, "finished_at": now_utc().isoformat()})

    @staticmethod
    def _run_row(row: dict) -> dict:
        return {**row, "started_at": _when(row.get("started_at")), "finished_at": _when(row.get("finished_at"))}

    def runs(self, user: User, limit: int = 30) -> list[dict]:
        rows = self._rest("GET", "search_runs", user, params={
            "select": _RUN_COLUMNS, "order": "started_at.desc", "limit": str(limit)}) or []
        return [self._run_row(r) for r in rows]

    def run(self, user: User, run_id: str) -> Optional[dict]:
        if not _is_uuid(run_id):
            return None
        rows = self._rest("GET", "search_runs", user, params={"select": f"{_RUN_COLUMNS},results",
                                                              "id": f"eq.{run_id}"}) or []
        return self._run_row(rows[0]) if rows else None

    def latest_run_with_results(self, user: User) -> Optional[dict]:
        rows = self._rest("GET", "search_runs", user, params={
            "select": f"{_RUN_COLUMNS},results", "results": "not.is.null",
            "order": "started_at.desc", "limit": "1"}) or []
        return self._run_row(rows[0]) if rows else None

    # ─── Ofertas guardadas o descartadas ─────────────────────────────────
    def job_states(self, user: User) -> dict[str, str]:
        rows = self._rest("GET", "saved_jobs", user, params={"select": "job_key,state"}) or []
        return {r["job_key"]: r["state"] for r in rows}

    def set_job_state(self, user: User, key: str, state: Optional[str], job: dict, run_id: Optional[str]) -> None:
        if state is None:
            self._rest("DELETE", "saved_jobs", user, params={"job_key": f"eq.{key}"}, prefer="return=minimal")
            return
        self._rest("POST", "saved_jobs", user, params={"on_conflict": "user_id,job_key"},
                   prefer="resolution=merge-duplicates,return=minimal", json={
                       "user_id": user.id, "job_key": key, "state": state, "job": job,
                       "search_run_id": run_id if _is_uuid(run_id or "") else None})

    def saved_jobs(self, user: User) -> list[dict]:
        rows = self._rest("GET", "saved_jobs", user, params={
            "select": "job_key,job,search_run_id,updated_at", "state": "eq.saved", "order": "updated_at.desc"}) or []
        return [{"key": r["job_key"], "job": r["job"], "search_run_id": r.get("search_run_id"),
                 "updated_at": _when(r.get("updated_at"))} for r in rows]

    # ─── Privacidad ──────────────────────────────────────────────────────
    def export(self, user: User) -> dict:
        """Todo lo que la cuenta tiene guardado, en JSON. El archivo del CV no va: es el que subió."""
        out: dict = {"email": user.email}
        for table in ("profiles", "candidate_profiles", "search_preferences", "cv_documents", "search_runs",
                      "saved_jobs", "usage_events"):
            out[table] = self._rest("GET", table, user, params={"select": "*"}) or []
        for cv in out["cv_documents"]:
            cv.pop("storage_path", None)
        return out

    def delete_account(self, user: User) -> None:
        """Borrado orquestado (spec §4.4, §21.17). Si un paso falla, el registro queda con el error y el
        usuario puede reintentar: sigue con su sesión porque la cuenta todavía existe."""
        record = self._rest("POST", "account_deletions", service=True, json={"user_id": user.id},
                            prefer="return=representation")
        deletion_id = record[0]["id"]
        try:
            self._rest("PATCH", "profiles", service=True, params={"id": f"eq.{user.id}"},
                       json={"deletion_requested_at": now_utc().isoformat()}, prefer="return=minimal")
            # Automatización y cobros todavía no existen (fases 5 y 6): no hay nada que cancelar.
            listed = self._ok(self._call("POST", f"/storage/v1/object/list/{CV_BUCKET}", service=True,
                                         json={"prefix": user.id, "limit": 1000}), "list cv files").json()
            files = [f"{user.id}/{f['name']}" for f in listed or [] if f.get("name")]
            if files:
                self._ok(self._call("DELETE", f"/storage/v1/object/{CV_BUCKET}", service=True,
                                    json={"prefixes": files}), "delete cv files")
            # Borrar el usuario de Auth revoca sus sesiones y, en cascada, todas sus filas.
            r = self._call("DELETE", f"/auth/v1/admin/users/{user.id}", service=True)
            if r.status_code not in (200, 204, 404):
                self._ok(r, "delete auth user")
        except Exception as e:
            self._rest("PATCH", "account_deletions", service=True, params={"id": f"eq.{deletion_id}"},
                       json={"last_error": str(e)[:300]}, prefer="return=minimal")
            raise
        self._forget(user.id)
        self._rest("PATCH", "account_deletions", service=True, params={"id": f"eq.{deletion_id}"},
                   json={"user_id": None, "completed_at": now_utc().isoformat(), "last_error": None},
                   prefer="return=minimal")

    def ping(self) -> bool:
        now = time.monotonic()
        if self._ping_cache and self._ping_cache[1] > now:
            return self._ping_cache[0]
        try:
            ok = self._call("GET", "/rest/v1/plans", service=True,
                            params={"select": "id", "limit": "1"}).status_code == 200
        except StoreError:
            ok = False
        self._ping_cache = (ok, now + 10)
        return ok
