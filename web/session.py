"""
web/session.py — Estado por usuario, en memoria del servidor.

Cada navegador recibe una cookie aleatoria (httponly) que apunta a su Session. El CV, la API key y
el perfil viven solo acá, nunca en disco ni en variables globales compartidas entre usuarios
(CLAUDE.md, regla 2). Las sesiones vencen por inactividad.
"""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass, field
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
    data: bytes
    id: str


@dataclass
class Session:
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
    search_ready: bool = False
    # La búsqueda en curso (o la última), con su progreso y su resultado.
    run: Optional["Run"] = None
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


def count() -> int:
    """Sesiones vivas. El chequeo de salud avisa si el proceso está en el tope."""
    with _lock:
        return len(_store)


def reset() -> None:
    """Solo para tests."""
    with _lock:
        _store.clear()
