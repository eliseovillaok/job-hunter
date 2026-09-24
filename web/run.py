"""
web/run.py — La búsqueda de un usuario, corriendo en un hilo del proceso.

La petición que la lanza responde al instante; la búsqueda sigue al costado y va dejando su estado
en un `Run` que vive en la sesión de quien la pidió, nunca en una variable compartida. La pantalla
de progreso solo lee ese estado.

Qué asume:
- La búsqueda se pasa el tiempo esperando (portales, Gemini), así que un hilo alcanza.
- Al lanzarla se reserva una búsqueda del cupo mensual y se crea su fila en `search_runs`; al terminar
  se guarda ahí la foto de los resultados (historial). Si el proceso se reinicia a mitad de camino, la
  corrida en curso se pierde y queda como `running` en la base.
- Límites en web/settings.py: una corrida por sesión, unas pocas en el proceso y un tiempo máximo.

Cancelar y el tiempo máximo cortan entre portales y al terminar cada tanda de evaluación: la tanda
en curso se deja terminar en vez de dejar llamadas a medio camino.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from typing import Optional

import demo
import matching
import notifier
import scrapers
from candidate import CandidateProfile
from web import persist, portals, settings
from web.session import Session

log = logging.getLogger("jobhunter.run")

PER_PORTAL = 40   # tope de ofertas por portal; el filtrado fino lo hace matching

# Fases de la corrida y estados de cada portal.
QUEUED, SCRAPING, EVALUATING, FINISHED = "queued", "scraping", "evaluating", "finished"
PENDING, RUNNING, DONE, FAILED, SKIPPED = "pending", "running", "done", "failed", "skipped"
# Cómo terminó: éxito, éxito con portales caídos, sin nada, o cortada por el usuario o el reloj.
SUCCESS, PARTIAL, EMPTY, ERROR, CANCELED, TIMEOUT = "success", "partial", "empty", "error", "canceled", "timeout"

_slots = threading.BoundedSemaphore(settings.MAX_RUNS)


class _Stopped(Exception):
    """Cancelación o tiempo agotado, lanzada desde el progreso para no seguir evaluando."""


class MonthlyLimit(Exception):
    """El plan ya no tiene búsquedas este mes."""


# Cómo queda cada final en search_runs.status.
_DB_STATUS = {SUCCESS: "succeeded", PARTIAL: "partial", EMPTY: "succeeded", CANCELED: "canceled",
              ERROR: "failed", TIMEOUT: "failed"}


@dataclass
class PortalRun:
    key: str
    label: str
    status: str = PENDING
    found: int = 0
    started: float = 0.0
    finished: float = 0.0

    @property
    def elapsed(self) -> float:
        """Cuánto lleva (o llevó) este portal: sin esto, uno lento parece trabado."""
        if not self.started:
            return 0.0
        return (self.finished or time.time()) - self.started


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
    send_email: bool
    email_sender: str
    email_password: str
    email_recipient: str

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
            send_email=s.send_email,
            email_sender=s.email_sender,
            email_password=s.email_password,
            email_recipient=s.email_recipient,
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
    email: str = ""           # "" | sent | empty | auth | smtp: cómo terminó el envío del resumen
    result: Optional[matching.MatchResult] = None
    started: float = field(default_factory=time.time)
    finished: float = 0.0
    user_id: str = ""         # dueño de la corrida; vacío = no se guarda
    db_id: str = ""           # search_runs.id
    _stop: threading.Event = field(default_factory=threading.Event, repr=False)

    @property
    def funnel(self) -> Optional[dict]:
        """Qué pasó con las ofertas, para el encabezado de resultados (y el historial)."""
        r = self.result
        if r is None:
            return None
        return {"found": r.total_found, "dups": r.duplicates_removed, "excluded": dict(r.excluded),
                "out": r.pre_ranked_out, "evaluated": sum(1 for sj in r.scored if sj.evaluated),
                "top_n": self.eval_limit, "stop_reason": r.stop_reason}

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
        return sum(1 for p in self.portals if p.status in (DONE, FAILED, SKIPPED))

    @property
    def portals_ok(self) -> int:
        return sum(1 for p in self.portals if p.status == DONE)

    @property
    def failed_portals(self) -> list[PortalRun]:
        return [p for p in self.portals if p.status == FAILED]

    def cancel(self) -> None:
        self._stop.set()


def start(s: Session, lang: str) -> Run:
    """Lanza la búsqueda de esta sesión. Si ya hay una corriendo, devuelve esa.

    Con una cuenta, antes reserva la búsqueda en el cupo del mes: `MonthlyLimit` si no quedan,
    `persist.StoreError` si la base no respondió (y entonces no se busca: el cupo no se puede saltear)."""
    if s.run is not None and s.run.active:
        return s.run
    cfg = RunConfig.from_session(s, lang)
    run_id = uuid.uuid4().hex[:12]
    db_id = ""
    store = persist.get()
    if s.user_id and store is not None:
        db_id = store.start_run(s.user_id, s.plan or persist.Plan(persist.FREE_PLAN), {
            "sources_requested": len(cfg.portals), "trace_id": run_id, "lang": lang,
            "model_name": None if demo.enabled() else cfg.model,
            "query": {"terms": cfg.terms, "portals": cfg.portals, "modalities": sorted(cfg.prefs.modalities),
                      "locations": cfg.prefs.locations, "job_languages": cfg.prefs.job_languages,
                      "min_score": cfg.min_score, "eval_limit": cfg.eval_limit},
        })
        if db_id is None:
            raise MonthlyLimit
    labels = {p.key: p.label for p in portals.PORTALS}
    run = Run(
        id=run_id,
        portals=[PortalRun(key=k, label=labels.get(k, k)) for k in cfg.portals],
        eval_limit=cfg.eval_limit,
        min_score=cfg.min_score,
        user_id=s.user_id if db_id else "",
        db_id=db_id,
    )
    s.history_view = None
    s.run = run
    threading.Thread(target=_execute, args=(run, cfg), name=f"run-{run.id}", daemon=True).start()
    return run


def _execute(run: Run, cfg: RunConfig) -> None:
    """Corre en su propio hilo: nada de acá toca la petición que la lanzó."""
    deadline = run.started + settings.RUN_TIMEOUT
    slots = _slots   # el mismo objeto para tomar y devolver el lugar
    if not slots.acquire(timeout=max(1.0, deadline - time.time())):
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
        _mail(run, cfg)
        _finish(run, PARTIAL if run.failed_portals else SUCCESS)
    except _Stopped:
        _finish(run, TIMEOUT if time.time() >= deadline else CANCELED)
    except Exception:
        log.exception("run=%s falló", run.id)
        _finish(run, ERROR)
    finally:
        slots.release()


def _read_portal(run: Run, portal: PortalRun, cfg: RunConfig) -> list[scrapers.JobPosting]:
    """Un portal, en su propio hilo. Si falla, queda marcado y no arrastra a los demás."""
    portal.started, portal.status = time.time(), RUNNING
    try:
        jobs = scrapers.PORTAL_SCRAPERS[portal.key](cfg.terms, PER_PORTAL)
        portal.found, portal.status = len(jobs), DONE
        return jobs
    except Exception as e:
        portal.status = FAILED
        log.warning("run=%s portal=%s falló: %s", run.id, portal.key, e)
        return []
    finally:
        portal.finished = time.time()


def _scrape(run: Run, cfg: RunConfig, deadline: float) -> list[scrapers.JobPosting]:
    """Los portales se leen en paralelo y con presupuesto propio: el más lento no se come la corrida.

    Al agotarse ese presupuesto se evalúa lo ya traído en vez de terminar sin nada."""
    run.phase = SCRAPING
    budget = min(deadline, time.time() + settings.SCRAPE_TIMEOUT)
    found: list[scrapers.JobPosting] = []
    pool = ThreadPoolExecutor(max_workers=settings.SCRAPE_WORKERS, thread_name_prefix=f"scrape-{run.id}")
    try:
        pending = {pool.submit(_read_portal, run, p, cfg): p for p in run.portals}
        while pending:
            _check(run, deadline)
            if time.time() >= budget:
                for portal in pending.values():
                    if portal.status in (PENDING, RUNNING):
                        portal.status, portal.finished = SKIPPED, time.time()
                log.info("run=%s sin tiempo de lectura: %d portales sin terminar", run.id, len(pending))
                break
            done, _ = wait(list(pending), timeout=0.5, return_when=FIRST_COMPLETED)
            for fut in done:
                found.extend(fut.result())
                pending.pop(fut, None)
            run.found = len(found)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
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
        portal.started, portal.status = time.time(), RUNNING
        time.sleep(0.35)
        portal.found, portal.status, portal.finished = 4 + (i * 3) % 11, DONE, time.time()
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


def _mail(run: Run, cfg: RunConfig) -> None:
    """Resumen por correo, si el usuario lo pidió. Un fallo acá no invalida la búsqueda."""
    if not (cfg.send_email and cfg.email_sender and cfg.email_password and cfg.email_recipient):
        return
    if run.result is None or demo.enabled():
        run.email = "sent" if demo.enabled() else ""
        return
    try:
        sent = notifier.send_digest(run.result.scored, sender=cfg.email_sender, password=cfg.email_password,
                                    recipient=cfg.email_recipient, min_score=cfg.min_score, lang=cfg.lang)
        run.email = "sent" if sent else "empty"
    except notifier.EmailError as e:
        run.email = str(e)
        log.warning("run=%s no se pudo enviar el correo: %s", run.id, e)
    except Exception:
        run.email = "smtp"
        log.exception("run=%s error inesperado al enviar el correo", run.id)


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
    _save(run)


def _save(run: Run) -> None:
    """Deja la corrida en el historial. Si la base no responde, los resultados siguen en la sesión."""
    store = persist.get()
    if not run.db_id or store is None:
        return
    fields = {"status": _DB_STATUS.get(run.outcome, "failed"), "sources_succeeded": run.portals_ok,
              "jobs_seen": run.found, "error_summary": None}
    if run.outcome in (ERROR, TIMEOUT) or run.failed_portals:
        failed = ",".join(p.key for p in run.failed_portals)
        fields["error_summary"] = (run.outcome if run.outcome in (ERROR, TIMEOUT) else "portals") + (f":{failed}" if failed else "")
    if run.result is not None:
        fields["funnel"] = run.funnel
        fields["results"] = [persist.scored_to_dict(sj) for sj in run.result.scored]
        fields["matches_created"] = sum(1 for sj in run.result.scored if sj.evaluated and sj.score >= run.min_score)
    try:
        store.finish_run(run.user_id, run.db_id, fields)
    except Exception:  # noqa: BLE001 — el historial no puede tumbar el final de la búsqueda
        log.warning("run=%s no se pudo guardar en el historial", run.id, exc_info=True)
