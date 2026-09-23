"""Tests de la interfaz web (FastAPI). Sin red ni IA: usa los datos de demo o una oferta armada a mano."""

import pytest
from fastapi.testclient import TestClient

import demo
from ai_engine import ScoredJob
from helpers import make_job
from web import main as web
from web import session as sessions


@pytest.fixture
def client():
    return TestClient(web.app)


@pytest.fixture
def demo_on(monkeypatch):
    monkeypatch.setattr(demo, "enabled", lambda: True)


def test_landing_renders_in_both_languages(client):
    es = client.get("/")
    assert es.status_code == 200 and "Encuentra el trabajo" in es.text
    en = client.get("/?lang=en")
    assert "Find the" in en.text
    assert en.cookies.get("lang") == "en"


def test_results_redirect_home_without_a_search(client, monkeypatch):
    monkeypatch.setattr(demo, "enabled", lambda: False)
    r = client.get("/resultados", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/"


def test_results_show_recommended_by_default(client, demo_on):
    r = client.get("/resultados")
    assert r.status_code == 200
    _, scored, _ = web.demo_results()
    shown = [sj for sj in scored if sj.evaluated and sj.score >= web.DEFAULT_MIN_SCORE]
    assert r.text.count('<article class="job">') == len(shown)


def test_filter_fragment_keeps_unknown_modality(client, demo_on):
    r = client.get("/resultados/lista?show=all&mod=remote", headers={"HX-Request": "true"})
    _, scored, _ = web.demo_results()
    expected = [sj for sj in scored if sj.job.modality in ("remote", "unknown")]
    assert r.text.count('<article class="job">') == len(expected)
    assert 'hx-swap-oob="true"' in r.text


def test_card_escapes_external_content_and_drops_unsafe_links(client, monkeypatch):
    job = make_job(title="<script>alert(1)</script>", company="Evil & Co <b>")
    job.url = "javascript:alert(1)"
    sj = ScoredJob(job=job, score=90, match_reasons=["<img src=x onerror=alert(1)>"], missing_skills=[],
                   cover_letter=None, summary="<svg onload=1>")
    monkeypatch.setattr(web, "current_results", lambda: (demo.load()[0], [sj], None))
    html = client.get("/resultados").text
    for raw in ("<script>alert", "<img src=x", "<b>", "javascript:alert"):
        assert raw not in html
    assert "&lt;script&gt;" in html and "Evil &amp; Co" in html


def test_security_headers(client):
    r = client.get("/")
    assert "frame-ancestors 'self'" in r.headers["content-security-policy"]
    assert r.headers["x-content-type-options"] == "nosniff"


def test_safe_url_allows_only_http():
    assert web.safe_url("https://example.com/x") == "https://example.com/x"
    for bad in ("javascript:alert(1)", "data:text/html,x", "", None, "//evil.com"):
        assert web.safe_url(bad) is None


def test_health_endpoints_answer_without_creating_a_session(client):
    """La plataforma late cada pocos segundos: si cada latido creara una sesión, expulsaría usuarios."""
    sessions.reset()
    live = client.get("/health/live")
    assert live.status_code == 200 and live.json()["status"] == "ok"
    ready = client.get("/health/ready")
    assert ready.status_code == 200 and ready.json()["checks"]["templates"] is True
    assert sessions.count() == 0
    assert not [k for k in ready.headers if k.lower() == "set-cookie"]
    # Las cabeceras de seguridad valen también acá.
    assert ready.headers["x-content-type-options"] == "nosniff"


def test_health_ready_reports_degraded_when_the_session_store_is_full(client, monkeypatch):
    monkeypatch.setattr(sessions, "count", lambda: sessions.MAX_SESSIONS)
    r = client.get("/health/ready")
    assert r.status_code == 503 and r.json()["status"] == "degraded"
    assert r.json()["checks"]["sessions"] is False
