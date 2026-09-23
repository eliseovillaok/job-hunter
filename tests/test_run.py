"""Tests de la corrida de búsqueda (web/run.py). Sin red ni IA: los portales y el matching se reemplazan."""

import time

import pytest

import matching
import scrapers
from helpers import make_job
from web import portals
from web import run as runner
from web import session as sessions
from web.session import Session

REAL_SCRAPERS = dict(scrapers.PORTAL_SCRAPERS)   # antes de que el fixture lo reemplace


def wait(run, timeout=5.0):
    """Espera a que la corrida termine; los hilos no deberían tardar nada con los dobles de test."""
    limit = time.time() + timeout
    while run.active and time.time() < limit:
        time.sleep(0.01)
    assert not run.active, f"la corrida quedó en {run.phase}"
    return run


@pytest.fixture
def session():
    s = Session(api_key="AIza-test", terms=["contadora"], portals=["remotive", "jobicy"])
    s.profile = None
    return s


@pytest.fixture(autouse=True)
def fake_pipeline(monkeypatch):
    """Portales que devuelven una oferta cada uno y un matching que no llama a nadie."""
    def portal(name):
        return lambda keywords, max_results=0: [make_job(title=f"Oferta {name}", company=name)]

    monkeypatch.setattr(scrapers, "PORTAL_SCRAPERS", {k: portal(k) for k in ("remotive", "jobicy", "wwr")})
    monkeypatch.setattr(matching, "match_jobs", lambda jobs, *a, **k: matching.MatchResult(scored=[], total_found=len(jobs)))


def test_registry_covers_every_portal_offered():
    """Si un portal se ofrece en el asistente, tiene que existir quien lo lea, y al revés."""
    assert {p.key for p in portals.PORTALS} == set(REAL_SCRAPERS)


def test_run_goes_through_every_portal_and_finishes(session):
    run = wait(runner.start(session, "es"))
    assert run.outcome == runner.SUCCESS
    assert [p.status for p in run.portals] == [runner.DONE, runner.DONE]
    assert run.found == 2 and run.result.total_found == 2
    assert session.run is run and run.finished > 0


def test_a_failing_portal_does_not_break_the_run(session, monkeypatch):
    def boom(keywords, max_results=0):
        raise RuntimeError("502 del portal")

    monkeypatch.setitem(scrapers.PORTAL_SCRAPERS, "jobicy", boom)
    run = wait(runner.start(session, "es"))
    assert run.outcome == runner.PARTIAL
    assert [p.key for p in run.failed_portals] == ["jobicy"]
    assert run.found == 1


def test_every_portal_failing_ends_as_error(session, monkeypatch):
    def boom(keywords, max_results=0):
        raise RuntimeError("sin red")

    for key in ("remotive", "jobicy"):
        monkeypatch.setitem(scrapers.PORTAL_SCRAPERS, key, boom)
    run = wait(runner.start(session, "es"))
    assert run.outcome == runner.ERROR and run.result is None


def test_portals_that_find_nothing_end_as_empty(session, monkeypatch):
    for key in ("remotive", "jobicy"):
        monkeypatch.setitem(scrapers.PORTAL_SCRAPERS, key, lambda keywords, max_results=0: [])
    run = wait(runner.start(session, "es"))
    assert run.outcome == runner.EMPTY


def test_cancel_stops_the_run(session, monkeypatch):
    started = {}

    def slow(keywords, max_results=0):
        started["yes"] = True
        time.sleep(0.2)
        return [make_job()]

    monkeypatch.setitem(scrapers.PORTAL_SCRAPERS, "remotive", slow)
    run = runner.start(session, "es")
    while not started:
        time.sleep(0.01)
    run.cancel()
    wait(run)
    assert run.outcome == runner.CANCELED and run.result is None


def test_the_time_limit_ends_the_run(session, monkeypatch):
    monkeypatch.setattr(runner.settings, "RUN_TIMEOUT", 0.05)
    monkeypatch.setitem(scrapers.PORTAL_SCRAPERS, "remotive",
                        lambda keywords, max_results=0: time.sleep(0.2) or [make_job()])
    run = wait(runner.start(session, "es"))
    assert run.outcome == runner.TIMEOUT


def test_a_second_search_reuses_the_one_already_running(session, monkeypatch):
    monkeypatch.setitem(scrapers.PORTAL_SCRAPERS, "remotive",
                        lambda keywords, max_results=0: time.sleep(0.1) or [make_job()])
    first = runner.start(session, "es")
    second = runner.start(session, "es")
    assert first is second
    wait(first)
    # Terminada, una búsqueda nueva sí arranca de cero.
    assert runner.start(session, "es") is not first


def test_the_run_takes_a_snapshot_of_the_search(session):
    """El hilo no lee la sesión: cambiar el paso 4 mientras corre no altera la búsqueda en marcha."""
    cfg = runner.RunConfig.from_session(session, "es")
    session.terms.append("otra cosa")
    session.portals.append("wwr")
    assert cfg.terms == ["contadora"] and cfg.portals == ["remotive", "jobicy"]


def test_unknown_portal_keys_are_ignored(session):
    session.portals = ["remotive", "portal-que-no-existe"]
    cfg = runner.RunConfig.from_session(session, "es")
    assert cfg.portals == ["remotive"]


def test_a_finished_run_feeds_the_estimate(session, monkeypatch):
    from web import wizard
    seen = []
    monkeypatch.setattr(wizard, "record_run", lambda minutes, eval_limit: seen.append((minutes, eval_limit)))
    wait(runner.start(session, "es"))
    assert len(seen) == 1 and seen[0][1] == session.eval_limit


def test_the_process_limit_makes_the_extra_run_wait(session, monkeypatch):
    """Con un solo lugar libre, la segunda búsqueda espera en cola en vez de degradar a las dos."""
    import threading
    monkeypatch.setattr(runner, "_slots", threading.BoundedSemaphore(1))
    monkeypatch.setitem(scrapers.PORTAL_SCRAPERS, "remotive",
                        lambda keywords, max_results=0: time.sleep(0.2) or [make_job()])
    other = Session(api_key="AIza-test", terms=["x"], portals=["remotive"])
    first = runner.start(session, "es")
    second = runner.start(other, "es")
    while first.phase == runner.QUEUED:
        time.sleep(0.01)
    assert second.phase == runner.QUEUED       # todavía no empezó: no hay lugar
    wait(first, timeout=10)
    wait(second, timeout=10)
    assert second.outcome == runner.SUCCESS    # arrancó al liberarse el lugar


def test_sessions_do_not_share_their_run():
    sessions.reset()
    a, b = Session(terms=["x"], portals=["remotive"]), Session(terms=["y"], portals=["jobicy"])
    wait(runner.start(a, "es"))
    wait(runner.start(b, "es"))
    assert a.run is not b.run
    assert [p.key for p in a.run.portals] == ["remotive"]
    assert [p.key for p in b.run.portals] == ["jobicy"]
