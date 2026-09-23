"""
web/run.py — La búsqueda de un usuario, corriendo en un hilo del proceso.

La petición que la lanza responde al instante; la búsqueda sigue al costado y va dejando su estado
en un `Run` que vive en la sesión de quien la pidió, nunca en una variable compartida. La pantalla
de progreso solo lee ese estado.

Qué asume:
- La búsqueda se pasa el tiempo esperando (portales, Gemini), así que un hilo alcanza.
- El estado vive en memoria: si el proceso se reinicia, la corrida se pierde y hay que repetirla.
  Se resuelve con la persistencia de la Fase 1, no antes.
- Límites en web/settings.py: una corrida por sesión, unas pocas en el proceso y un tiempo máximo.

Cancelar y el tiempo máximo cortan entre portales y al terminar cada tanda de evaluación: la tanda
en curso se deja terminar en vez de dejar llamadas a medio camino.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

import demo
import matching
import scrapers
from candidate import CandidateProfile
from web import portals, settings
from web.session import Session

log = logging.getLogger("jobhunter.run")

PER_PORTAL = 40   # tope de ofertas por portal; el filtrado fino lo hace matching

# Fases de la corrida y estados de cada portal.
QUEUED, SCRAPING, EVALUATING, FINISHED = "queued", "scraping", "evaluating", "finished"
PENDING, RUNNING, DONE, FAILED = "pending", "running", "done", "failed"
# Cómo terminó: éxito, éxito con portales caídos, sin nada, o cortada por el usuario o el reloj.
SUCCESS, PARTIAL, EMPTY, ERROR, CANCELED, TIMEOUT = "success", "partial", "empty", "error", "canceled", "timeout"

_slots = threading.BoundedSemaphore(settings.MAX_RUNS)


class _Stopped(Exception):
    """Cancelación o tiempo agotado, lanzada desde el progreso para no seguir evaluando."""


@dataclass
class PortalRun:
    key: str
    label: str
    status: str = PENDING
    found: int = 0


@dataclass
class RunConfig:
    """Foto de la búsqueda al lanzarla: el hilo no lee una sesión que el usuario puede seguir editando."""
    terms: list[str]
    portals: list[str]
    profile: CandidateProfile
    prefs: matching.SearchPreferences
    api_key: str
    model: str
    lang: str
    eval_limit: int
    min_score: int

    @classmethod
    def from_session(cls, s: Session, lang: str) -> "RunConfig":
        return cls(
            terms=list(s.terms),
            portals=[k for k in s.portals if k in scrapers.PORTAL_SCRAPERS],
            profile=s.profile or CandidateProfile(),
            prefs=matching.SearchPreferences(
                modalities=set(s.modalities),
                locations=[x.strip() for x in s.locations.split(",") if x.strip()],
                job_languages=list(s.job_languages),
            ),
            api_key=s.api_key,
            model=s.model,
            lang=lang,
            eval_limit=s.eval_limit,
            min_score=s.min_score,
        )


@dataclass
class Run:
    id: str
    portals: list[PortalRun]
    eval_limit: int
    min_score: int
    phase: str = QUEUED
    outcome: str = ""
    found: int = 0            # ofertas traídas por los portales
    evaluated: int = 0        # evaluadas por la IA hasta ahora
    to_evaluate: int = 0
    stage: str = ""           # screen | recheck, dentro de la evaluación
    result: Optional[matching.MatchResult] = None
    started: float = field(default_factory=time.time)
    finished: float = 0.0
    _stop: threading.Event = field(default_factory=threading.Event, repr=False)

    # ─── Lectura (la usa la pantalla de progreso) ────────────────────────────
    @property
    def active(self) -> bool:
        return self.phase != FINISHED

    @property
    def elapsed(self) -> float:
        return (self.finished or time.time()) - self.started

    @property
    def progress(self) -> int:
        """Avance 0-100. Leer los portales pesa menos que evaluar con IA, que es lo que tarda."""
        if self.phase == QUEUED:
            return 0
        if self.phase == SCRAPING:
            return int(5 + 35 * self.portals_done / max(1, len(self.portals)))
        if self.phase == EVALUATING:
            return int(45 + 55 * self.evaluated / max(1, self.to_evaluate))
        return 100

    @property
    def eta(self) -> Optional[int]:
        """Segundos que faltan, a partir de lo que ya tardó. None mientras no haya con qué estimar."""
        done = self.progress
        if not self.active or done < 10:
            return None
        return int(self.elapsed * (100 - done) / done)

    @property
    def portals_done(self) -> int:
        return sum(1 for p in self.portals if p.status in (DONE, FAILED))

    @property
    def portals_ok(self) -> int:
        return sum(1 for p in self.portals if p.status == DONE)

    @property
    def failed_portals(self) -> list[PortalRun]:
        return [p for p in self.portals if p.status == FAILED]

    def cancel(self) -> None:
        self._stop.set()


def start(s: Session, lang: str) -> Run:
    """Lanza la búsqueda de esta sesión. Si ya hay una corriendo, devuelve esa."""
    if s.run is not None and s.run.active:
        return s.run
    cfg = RunConfig.from_session(s, lang)
    labels = {p.key: p.label for p in portals.PORTALS}
    run = Run(
        id=uuid.uuid4().hex[:12],
        portals=[PortalRun(key=k, label=labels.get(k, k)) for k in cfg.portals],
        eval_limit=cfg.eval_limit,
        min_score=cfg.min_score,
    )
    s.run = run
    threading.Thread(target=_execute, args=(run, cfg), name=f"run-{run.id}", daemon=True).start()
    return run


def _execute(run: Run, cfg: RunConfig) -> None:
    """Corre en su propio hilo: nada de acá toca la petición que la lanzó."""
    deadline = run.started + settings.RUN_TIMEOUT
    if not _slots.acquire(timeout=max(1.0, deadline - time.time())):
        return _finish(run, TIMEOUT)   # el proceso está lleno y no se liberó a tiempo
    try:
        if demo.enabled():
            _demo(run, cfg, deadline)
        else:
            jobs = _scrape(run, cfg, deadline)
            _check(run, deadline)
            if not jobs:
                return _finish(run, EMPTY if run.portals_ok else ERROR)
            _evaluate(run, cfg, jobs, deadline)
        _finish(run, PARTIAL if run.failed_portals else SUCCESS)
    except _Stopped:
        _finish(run, TIMEOUT if time.time() >= deadline else CANCELED)
    except Exception:
        log.exception("run=%s falló", run.id)
        _finish(run, ERROR)
    finally:
        _slots.release()


def _scrape(run: Run, cfg: RunConfig, deadline: float) -> list[scrapers.JobPosting]:
    """Un portal que falla no corta la corrida: queda marcado y se sigue con el resto."""
    run.phase = SCRAPING
    found: list[scrapers.JobPosting] = []
    for portal in run.portals:
        _check(run, deadline)
        portal.status = RUNNING
        try:
            jobs = scrapers.PORTAL_SCRAPERS[portal.key](cfg.terms, PER_PORTAL)
            portal.found = len(jobs)
            portal.status = DONE
            found.extend(jobs)
        except Exception as e:
            portal.status = FAILED
            log.warning("run=%s portal=%s falló: %s", run.id, portal.key, e)
        run.found = len(found)
    return found


def _evaluate(run: Run, cfg: RunConfig, jobs: list[scrapers.JobPosting], deadline: float) -> None:
    run.phase = EVALUATING
    run.to_evaluate = min(len(jobs), cfg.eval_limit)

    def on_progress(stage: str, done: int, total: int) -> None:
        run.stage, run.evaluated, run.to_evaluate = stage, done, total
        _check(run, deadline)

    run.result = matching.match_jobs(
        jobs, cfg.profile, cfg.prefs,
        api_key=cfg.api_key, model=cfg.model, lang=cfg.lang,
        top_n=cfg.eval_limit, on_progress=on_progress,
    )


def _demo(run: Run, cfg: RunConfig, deadline: float) -> None:
    """Modo demo (JOB_HUNTER_DEMO=1): recorre las fases con los datos ficticios de demo.py.

    Sin red ni IA, para poder mirar y probar la pantalla de progreso entera."""
    profile, scored = demo.load()
    run.phase = SCRAPING
    for i, portal in enumerate(run.portals):
        _check(run, deadline)
        portal.status = RUNNING
        time.sleep(0.35)
        portal.found = 4 + (i * 3) % 11
        portal.status = DONE
        run.found += portal.found
    run.phase = EVALUATING
    run.to_evaluate = min(cfg.eval_limit, max(len(scored), 12))
    step = max(1, run.to_evaluate // 10)
    while run.evaluated < run.to_evaluate:
        _check(run, deadline)
        time.sleep(0.3)
        run.evaluated = min(run.to_evaluate, run.evaluated + step)
    run.result = matching.MatchResult(
        scored=scored, total_found=run.found, duplicates_removed=4,
        excluded={"modality": 3}, pre_ranked_out=max(0, run.found - run.to_evaluate))


def _check(run: Run, deadline: float) -> None:
    if run._stop.is_set() or time.time() >= deadline:
        raise _Stopped


def _finish(run: Run, outcome: str) -> None:
    run.phase, run.outcome, run.finished = FINISHED, outcome, time.time()
    minutes = run.elapsed / 60
    if outcome in (SUCCESS, PARTIAL):
        from web import wizard   # tarde a propósito: evita un import circular al cargar el módulo
        wizard.record_run(minutes, run.eval_limit)
    log.info("run=%s fin=%s portales=%d/%d ofertas=%d evaluadas=%d minutos=%.1f",
             run.id, outcome, run.portals_done, len(run.portals), run.found, run.evaluated, minutes)
