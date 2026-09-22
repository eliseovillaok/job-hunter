"""Tests del asistente web (web/wizard.py). Sin red ni IA: check_key y extract_profile se reemplazan."""

import pytest
from fastapi.testclient import TestClient

import ai_engine
import candidate as cand
import demo
from candidate import CandidateProfile, Language, Skill
from web import session as sessions
from web import wizard
from web.main import app

KEY = "AIza-test-key-0000"


@pytest.fixture(autouse=True)
def no_demo_no_ai(monkeypatch):
    monkeypatch.setattr(demo, "enabled", lambda: False)
    monkeypatch.setattr(ai_engine, "check_key", lambda key, model=None: key.startswith("AIza"))
    sessions.reset()


def profile(**kw) -> CandidateProfile:
    base = dict(summary="Contadora junior", target_roles=["Contadora"], seniority="junior",
                seniority_evidence="Asistente contable junior", skills=[Skill("Excel", "Manejo de Excel")],
                languages=[Language("Español", "nativo"), Language("Inglés")], location="Mendoza",
                search_terms={"es": ["Contadora"], "en": ["Accountant"]})
    base.update(kw)
    return CandidateProfile(**base)


@pytest.fixture
def client():
    return TestClient(app)


def upload(client, name="cv.txt", data=b"Contadora junior", origin="wizard"):
    return client.post("/asistente/cv", files={"cv": (name, data, "application/octet-stream")},
                       data={"origin": origin}, follow_redirects=False)


def through_step2(client, monkeypatch, p=None):
    monkeypatch.setattr(cand, "extract_profile", lambda *a, **k: p or profile())
    upload(client)
    return client.post("/asistente/ia", data={"key": KEY, "model": ai_engine.DEFAULT_MODEL}, follow_redirects=False)


# ─── Paso 1 ──────────────────────────────────────────────────────────────────
def test_steps_cannot_be_skipped(client):
    for step in (2, 3, 4):
        r = client.get(f"/asistente/{step}", follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/asistente/1"


@pytest.mark.parametrize("name,data", [
    ("cv.exe", b"MZ..."),            # extensión no permitida
    ("cv.pdf", b"no es un pdf"),     # la extensión no coincide con el contenido
    ("cv.docx", b"texto plano"),
    ("cv.txt", b"   "),              # vacío
])
def test_upload_rejects_invalid_files(client, name, data):
    r = upload(client, name, data)
    assert r.status_code == 400
    assert client.get("/asistente/2", follow_redirects=False).status_code == 303


def test_upload_rejects_files_over_the_limit(client, monkeypatch):
    monkeypatch.setattr(wizard, "MAX_CV_BYTES", 10)
    assert upload(client, data=b"x" * 11).status_code == 400


def test_upload_from_landing_goes_to_step_2(client):
    r = upload(client, "cv.pdf", b"%PDF-1.4 fake", origin="landing")
    assert r.headers["location"] == "/asistente/2"
    assert client.get("/asistente/2").status_code == 200


def test_sessions_are_isolated():
    a, b = TestClient(app), TestClient(app)
    upload(a)
    assert a.get("/asistente/2", follow_redirects=False).status_code == 200
    assert b.get("/asistente/2", follow_redirects=False).status_code == 303


# ─── Paso 2 ──────────────────────────────────────────────────────────────────
def test_key_fragment_enables_button_only_for_valid_key(client):
    upload(client)
    bad = client.post("/asistente/clave", data={"key": "nope"}, headers={"HX-Request": "true"}).text
    assert "disabled" in bad and 'hx-swap-oob="true"' in bad
    good = client.post("/asistente/clave", data={"key": KEY}, headers={"HX-Request": "true"}).text
    assert "disabled" not in good.split('id="s2-actions"')[1]


def test_key_is_never_rendered_back(client, monkeypatch):
    through_step2(client, monkeypatch)
    assert KEY not in client.get("/asistente/2").text


def test_analysis_fills_profile_terms_and_languages(client, monkeypatch):
    r = through_step2(client, monkeypatch)
    assert r.headers["location"] == "/asistente/3"
    s = next(iter(sessions._store.values()))
    assert s.terms == ["Contadora", "Accountant"] and set(s.job_languages) == {"es", "en"}


@pytest.mark.parametrize("exc,status,key", [
    (ai_engine.AuthError("API_KEY_INVALID"), 400, "wz_err_key"),
    (ai_engine.QuotaExceeded("quota"), 429, "wz_err_quota"),
    (RuntimeError("stack trace secreto"), 502, "wz_err_analyze"),
])
def test_analysis_errors_are_friendly(client, monkeypatch, exc, status, key):
    def boom(*a, **k):
        raise exc
    monkeypatch.setattr(cand, "extract_profile", boom)
    upload(client)
    r = client.post("/asistente/ia", data={"key": KEY})
    assert r.status_code == status
    assert "stack trace secreto" not in r.text and "API_KEY_INVALID" not in r.text


def test_email_fields_are_validated(client, monkeypatch):
    upload(client)
    r = client.post("/asistente/ia", data={"key": KEY, "send_email": "1", "email_sender": "x",
                                          "email_recipient": "y", "email_password": "corta"})
    assert r.status_code == 400


# ─── Paso 3 ──────────────────────────────────────────────────────────────────
def test_profile_page_escapes_cv_content_and_flags_missing_data(client, monkeypatch):
    through_step2(client, monkeypatch, profile(summary="<script>alert(1)</script>", location=cand.UNKNOWN))
    html = client.get("/asistente/3").text
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html
    review = html.split('class="review"')[1].split("</button>")[0]
    assert "ubicación" in review and "nivel de Inglés" in review and 'data-goto="f-' in html


def test_profile_form_keeps_evidence_and_marks_user_additions(client, monkeypatch):
    through_step2(client, monkeypatch)
    r = client.post("/asistente/perfil", data={
        "summary": "Contadora", "roles": ["Contadora", "Analista contable"], "seniority": "junior",
        "years": "2,5", "location": "", "langs": ["Español (nativo)", "Inglés (B2)"],
        "skills": ["Excel", "Tango"], "notes": ""}, follow_redirects=False)
    assert r.headers["location"] == "/asistente/4"
    p = next(iter(sessions._store.values())).profile
    assert p.years_experience == 2.5 and p.location == cand.UNKNOWN
    assert [(x.language, x.level) for x in p.languages] == [("Español", "nativo"), ("Inglés", "B2")]
    assert p.skills[0].evidence == "Manejo de Excel" and p.skills[1].evidence == "Agregado por ti"


def test_empty_profile_is_rejected(client, monkeypatch):
    upload(client)
    client.post("/asistente/manual")
    client.post("/asistente/ia", data={"key": KEY})
    assert client.post("/asistente/perfil", data={"notes": "  "}).status_code == 400


# ─── Paso 4 ──────────────────────────────────────────────────────────────────
def test_search_form_sanitizes_and_bounds_values(client, monkeypatch):
    through_step2(client, monkeypatch)
    client.post("/asistente/perfil", data={"summary": "x", "roles": ["Contadora"]})
    r = client.post("/asistente/busqueda", data={
        "terms": ["Contadora", "contadora", "  "], "modality": ["remote", "spaceship"], "portal": ["remotive", "evil"],
        "job_lang": ["es", "xx"], "min_score": "5", "eval_limit": "9999"}, follow_redirects=False)
    assert r.headers["location"] == "/buscando"
    s = next(iter(sessions._store.values()))
    assert s.terms == ["Contadora"] and s.modalities == ["remote"] and s.portals == ["remotive"]
    assert s.job_languages == ["es"] and s.min_score == 30 and s.eval_limit == 200


def test_search_requires_terms_and_portals(client, monkeypatch):
    through_step2(client, monkeypatch)
    client.post("/asistente/perfil", data={"summary": "x", "roles": ["Contadora"]})
    assert client.post("/asistente/busqueda", data={}).status_code == 400


def test_estimate_grows_with_listings_and_portals():
    assert wizard.estimate_minutes(10, 5) <= wizard.estimate_minutes(40, 5) <= wizard.estimate_minutes(200, 5)
    assert wizard.estimate_minutes(40, 5) <= wizard.estimate_minutes(40, 19)


# ─── ai_engine.check_key ─────────────────────────────────────────────────────
class _FakeModels:
    def __init__(self, exc=None):
        self.exc = exc

    def get(self, model):
        if self.exc:
            raise self.exc


class _FakeClient:
    def __init__(self, exc=None):
        self.models = _FakeModels(exc)


@pytest.mark.parametrize("exc,expected", [
    (None, True),
    (RuntimeError("400 API_KEY_INVALID"), False),
    (RuntimeError("connection reset"), None),
])
def test_check_key(monkeypatch, exc, expected):
    monkeypatch.undo()   # usa el check_key real
    monkeypatch.setattr(ai_engine, "_client", lambda key: _FakeClient(exc))
    assert ai_engine.check_key("AIza-x") is expected


def test_check_key_rejects_malformed_keys_without_network(monkeypatch):
    monkeypatch.undo()
    monkeypatch.setattr(ai_engine, "_client", lambda key: pytest.fail("no debe llamar a la API"))
    assert ai_engine.check_key("sk-no-es-de-google") is False


# ─── Solidez: borradores, sesión vencida, clave guardada ─────────────────────
def test_draft_survives_language_switch(client, monkeypatch):
    through_step2(client, monkeypatch)
    r = client.post("/asistente/borrador/3", data={"summary": "Resumen a medio escribir", "roles": ["Contadora"]})
    assert r.status_code == 204
    html = client.get("/asistente/3?lang=en").text
    assert "Resumen a medio escribir" in html


def test_draft_does_not_validate_or_skip_steps(client):
    upload(client)
    # Sin clave todavía: el borrador del paso 4 se ignora y el paso 4 sigue bloqueado.
    assert client.post("/asistente/borrador/4", data={"terms": ["x"]}).status_code == 204
    assert client.get("/asistente/4", follow_redirects=False).headers["location"] == "/asistente/2"


def test_manual_profile_is_written_in_step_1_and_still_needs_a_key(client):
    r = client.post("/asistente/manual", follow_redirects=False)
    assert r.headers["location"] == "/asistente/1?escribir=1"
    assert client.post("/asistente/manual", data={"notes": "  "}).status_code == 400
    r = client.post("/asistente/manual", data={"notes": "Electricista matriculado, 5 años"}, follow_redirects=False)
    assert r.headers["location"] == "/asistente/2"
    assert client.get("/asistente/3", follow_redirects=False).headers["location"] == "/asistente/2"
    client.post("/asistente/ia", data={"key": KEY})
    assert "Electricista matriculado" in client.get("/asistente/3").text


def test_new_cv_invalidates_previous_profile(client, monkeypatch):
    through_step2(client, monkeypatch)
    upload(client, data=b"Otro CV distinto")
    s = next(iter(sessions._store.values()))
    assert s.profile is None and s.terms == []
    assert client.get("/asistente/3", follow_redirects=False).headers["location"] == "/asistente/2"


def test_expired_session_explains_instead_of_silently_resetting(client):
    client.cookies.set(sessions.COOKIE, "sesion-que-ya-no-existe")
    r = client.post("/asistente/perfil", data={"summary": "x"}, follow_redirects=False)
    assert r.headers["location"] == "/asistente/1?sesion=vencida"
    assert "venció" in client.get("/asistente/1?sesion=vencida").text


def test_saved_key_is_masked_and_can_be_changed(client, monkeypatch):
    through_step2(client, monkeypatch)
    html = client.get("/asistente/2").text
    assert KEY not in html and f"{KEY[:4]}…{KEY[-4:]}" in html
    client.post("/asistente/clave/cambiar")
    assert client.get("/asistente/3", follow_redirects=False).headers["location"] == "/asistente/2"


def test_boosted_navigation_pushes_final_url_but_not_language_switches(client):
    boosted = {"HX-Request": "true", "HX-Boosted": "true"}
    assert client.get("/asistente/1", headers=boosted).headers.get("HX-Push-Url") == "/asistente/1"
    assert "HX-Push-Url" not in client.get("/asistente/1?lang=en", headers=boosted).headers


def test_step_4_requires_confirming_the_profile(client, monkeypatch):
    through_step2(client, monkeypatch)
    assert client.get("/asistente/4", follow_redirects=False).headers["location"] == "/asistente/3"
    client.post("/asistente/borrador/3", data={"summary": "x", "roles": ["Contadora"]})   # un borrador no confirma
    assert client.get("/asistente/4", follow_redirects=False).status_code == 303
    client.post("/asistente/perfil", data={"summary": "x", "roles": ["Contadora"]})
    assert client.get("/asistente/4", follow_redirects=False).status_code == 200
