"""
web/session.py — Estado de trabajo por navegador, en memoria del servidor.

Cada navegador recibe una cookie aleatoria (httponly) que apunta a su Session. Lo guardado de la
cuenta (CV, perfil, preferencias, historial) vive en la base (web/persist.py) y se copia acá al
entrar; acá queda además lo que no se guarda nunca: la API key, la contraseña de correo y la búsqueda
en curso. Una Session pertenece a una sola cuenta: si en el navegador entra otra, se descarta
(AGENTS.md, regla 2). Las sesiones vencen por inactividad.
"""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import ai_engine
import matching
from candidate import CandidateProfile
from web import portals, settings

if TYPE_CHECKING:   # solo para tipos: web/run.py sí importa este módulo
    from web.run import Run

COOKIE = "jh_sid"
TTL_SECONDS = settings.SESSION_TTL_SECONDS
MAX_SESSIONS = settings.MAX_SESSIONS


@dataclass
class CVFile:
    name: str
    mime: str
    data: bytes          # vacío si se recargó de la cuenta: se baja del almacenamiento solo si hace falta
    id: str
    size: int = 0


@dataclass
class HistoryView:
    """Una búsqueda anterior que se está mirando en /resultados (sale de search_runs)."""
    run_id: str
    scored: list
    funnel: Optional[dict]
    min_score: int
    eval_limit: int
    started_at: Optional[datetime] = None


@dataclass
class Session:
    # Dueño: la cuenta con la que se armó. Vacío = nadie ingresó en este navegador.
    user_id: str = ""
    plan: Optional[object] = None      # persist.Plan, leído al entrar
    cv_doc_id: str = ""                # cv_documents.id del CV vigente
    # Paso 1
    cv: Optional[CVFile] = None
    manual_profile: bool = False
    # Paso 2
    api_key: str = ""
    key_ok: Optional[bool] = None
    model: str = ai_engine.DEFAULT_MODEL
    send_email: bool = False
    email_sender: str = ""
    email_password: str = ""
    email_recipient: str = ""
    analyzed_cv_id: str = ""
    # Paso 3
    profile: Optional[CandidateProfile] = None
    profile_confirmed: bool = False   # el usuario revisó el perfil y continuó
    # Paso 4
    terms: list[str] = field(default_factory=list)
    modalities: list[str] = field(default_factory=list)
    locations: str = ""
    job_languages: list[str] = field(default_factory=list)
    portals: list[str] = field(default_factory=portals.default_selection)
    min_score: int = 65
    eval_limit: int = matching.DEFAULT_TOP_N
    # La búsqueda en curso (o la última), con su progreso y su resultado.
    run: Optional["Run"] = None
    history_view: Optional[HistoryView] = None
    touched: float = field(default_factory=time.time)

    # ─── Hasta qué paso puede llegar (no se saltean pasos) ───────────────
    def max_step(self) -> int:
        if not (self.cv or self.manual_profile):
            return 1
        # Sin clave conectada no se pasa del paso 2, aunque el perfil ya esté escrito a mano.
        if self.profile is None or not self.api_key or self.key_ok is False:
            return 2
        if self.profile.is_empty() or not self.profile_confirmed:
            return 3
        return 4


_store: dict[str, Session] = {}
_lock = threading.Lock()


def _prune(now: float) -> None:
    for sid in [s for s, v in _store.items() if now - v.touched > TTL_SECONDS]:
        del _store[sid]
    while len(_store) >= MAX_SESSIONS:
        del _store[min(_store, key=lambda s: _store[s].touched)]


def get(sid: str | None) -> tuple[str, Session, bool]:
    """(id, sesión, es_nueva). Un id desconocido o vencido crea una sesión nueva."""
    now = time.time()
    with _lock:
        sess = _store.get(sid) if sid else None
        if sess and now - sess.touched <= TTL_SECONDS:
            sess.touched = now
            return sid, sess, False
        _prune(now)
        sid = secrets.token_urlsafe(32)
        sess = _store[sid] = Session()
        return sid, sess, True


def replace(sid: str, sess: Session) -> Session:
    """Pone una sesión nueva en el lugar de `sid` (otra cuenta entró en este navegador)."""
    with _lock:
        _store[sid] = sess
        return sess


def drop(sid: str | None) -> None:
    """Al salir de la cuenta: nada de lo que había en memoria sobrevive."""
    if sid:
        with _lock:
            _store.pop(sid, None)


def count() -> int:
    """Sesiones vivas. El chequeo de salud avisa si el proceso está en el tope."""
    with _lock:
        return len(_store)


def reset() -> None:
    """Solo para tests."""
    with _lock:
        _store.clear()
