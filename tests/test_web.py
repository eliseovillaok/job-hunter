"""Tests de la interfaz web (FastAPI). Sin red ni IA: usa los datos de demo o una oferta armada a mano."""

import pytest
from fastapi.testclient import TestClient

import demo
from ai_engine import ScoredJob
from helpers import make_job, sign_up
from web import main as web
from web import session as sessions


@pytest.fixture
def client():
    return sign_up(TestClient(web.app))


@pytest.fixture
def demo_on(monkeypatch):
    monkeypatch.setattr(demo, "enabled", lambda: True)


def test_landing_renders_in_both_languages():
    client = TestClient(web.app)
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
    monkeypatch.setattr(web, "current_results", lambda request: (demo.load()[0], [sj], None))
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


# ─── Resultados de una búsqueda real ─────────────────────────────────────────
def searched(monkeypatch, client, *, scored=None, stop_reason=None, min_score=65, api_key="AIza-test"):
    """Deja en la sesión del cliente una búsqueda terminada, sin haberla corrido."""
    import matching
    from web import run as runner
    from web import session as sessions

    sessions.reset()
    client.get("/")                                   # crea la sesión y su cookie
    s = next(iter(sessions._store.values()))
    s.api_key, s.profile = api_key, demo.load()[0]
    jobs = scored if scored is not None else demo.load()[1][:3]
    s.run = runner.Run(id="test", portals=[], eval_limit=40, min_score=min_score, phase=runner.FINISHED,
                       outcome=runner.SUCCESS)
    s.run.result = matching.MatchResult(scored=jobs, total_found=80, duplicates_removed=5,
                                        excluded={"modality": 7}, pre_ranked_out=28, stop_reason=stop_reason)
    return s


def test_results_come_from_the_session_search(client, monkeypatch):
    monkeypatch.setattr(demo, "enabled", lambda: False)
    s = searched(monkeypatch, client)
    html = client.get("/resultados").text
    assert s.run.result.scored[0].job.title in html
    assert "80" in html and "28" in html        # el embudo sale de la corrida, no de números fijos


def test_results_without_a_search_send_you_home(client, monkeypatch):
    monkeypatch.setattr(demo, "enabled", lambda: False)
    r = client.get("/resultados", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/"


def test_the_minimum_match_comes_from_step4(client, monkeypatch):
    monkeypatch.setattr(demo, "enabled", lambda: False)
    searched(monkeypatch, client, min_score=90)
    html = client.get("/resultados").text
    assert 'value="90"' in html


def test_an_exhausted_quota_is_explained(client, monkeypatch):
    monkeypatch.setattr(demo, "enabled", lambda: False)
    searched(monkeypatch, client, stop_reason="quota")
    assert "cuota" in client.get("/resultados").text


def test_the_letter_uses_the_session_key(client, monkeypatch):
    monkeypatch.setattr(demo, "enabled", lambda: False)
    s = searched(monkeypatch, client)
    sj = s.run.result.scored[0]
    seen = {}

    def fake_letter(job, reasons, profile, *, api_key, model, signature=""):
        seen.update(job=job.title, key=api_key, firma=signature)
        return "Estimado equipo: me interesa el puesto."

    monkeypatch.setattr(web.ai_engine, "generate_cover_letter", fake_letter)
    html = client.post(f"/carta/{web.dom_id(sj.job)}").text
    assert "me interesa el puesto" in html
    assert seen["key"] == "AIza-test" and seen["job"] == sj.job.title
    assert sj.cover_letter                      # queda guardada: no se paga dos veces


def test_the_letter_needs_a_key(client, monkeypatch):
    monkeypatch.setattr(demo, "enabled", lambda: False)
    s = searched(monkeypatch, client, api_key="")
    r = client.post(f"/carta/{web.dom_id(s.run.result.scored[0].job)}")
    assert "conectar tu acceso" in r.text


def test_an_unknown_job_asks_for_nothing(client, monkeypatch):
    monkeypatch.setattr(demo, "enabled", lambda: False)
    searched(monkeypatch, client)
    assert client.post("/carta/nada").status_code == 204


def test_the_export_carries_the_session_results(client, monkeypatch):
    monkeypatch.setattr(demo, "enabled", lambda: False)
    s = searched(monkeypatch, client)
    payload = client.get("/resultados/export.json").json()
    assert [j["title"] for j in payload] == [sj.job.title for sj in s.run.result.scored]


def test_the_level_filter_only_shows_that_level(client, monkeypatch):
    """Antes, lo que no tenía nivel detectado pasaba siempre y el filtro parecía no hacer nada."""
    monkeypatch.setattr(demo, "enabled", lambda: False)
    jobs = []
    for level in ("senior", "junior", "unknown"):
        job = make_job(title=f"Puesto {level}")
        job.seniority = level
        jobs.append(ScoredJob(job=job, score=90, match_reasons=[], missing_skills=[], cover_letter=None, summary=""))
    searched(monkeypatch, client, scored=jobs)
    html = client.get("/resultados?lvl=senior").text
    assert "Puesto senior" in html and "Puesto junior" not in html and "Puesto unknown" not in html
    # Lo no detectado es una opción propia, no una excepción escondida.
    html = client.get("/resultados?lvl=senior&lvl=unknown").text
    assert "Puesto senior" in html and "Puesto unknown" in html


def test_the_filters_panel_has_every_label(client, monkeypatch):
    monkeypatch.setattr(demo, "enabled", lambda: False)
    searched(monkeypatch, client)
    html = client.get("/resultados").text
    for text in ("Modalidad", "Nivel", "Afinidad mínima", "Qué mostrar", "No especificado"):
        assert text in html
    assert "flt_" not in html          # ninguna clave sin traducir


def test_an_empty_result_offers_a_way_out(client, monkeypatch):
    monkeypatch.setattr(demo, "enabled", lambda: False)
    searched(monkeypatch, client)
    html = client.get("/resultados?lvl=intern").text
    assert "Ninguna oferta coincide" in html and "data-clear-filters" in html


def test_the_email_outcome_is_told_on_the_results(client, monkeypatch):
    monkeypatch.setattr(demo, "enabled", lambda: False)
    s = searched(monkeypatch, client)
    s.email_recipient = "yo@gmail.com"
    s.run.email = "sent"
    assert "Te enviamos el resumen a yo@gmail.com" in client.get("/resultados").text
    s.run.email = "auth"
    assert "rechazó la contraseña" in client.get("/resultados").text


def test_the_email_body_is_branded_and_escapes_its_content():
    import notifier
    job = make_job(title="<script>alert(1)</script>", company="Evil & Co")
    sj = ScoredJob(job=job, score=88, match_reasons=["Python"], missing_skills=["Kubernetes"],
                   cover_letter=None, summary="")
    html = notifier.build_html([sj], [sj], lang="es", min_score=65, logo_cid="logo@test")
    assert "JobHunter" in html and "cid:logo@test" in html
    assert "#1F6F54" in html                       # color de marca, no inventado
    assert "<script>alert" not in html and "Evil &amp; Co" in html
    assert "88" in html and "Afinidad alta" in html
