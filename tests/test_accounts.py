"""Cuentas y persistencia (Fase 1): muro de ingreso, CSRF, datos que sobreviven, cupo, historial y borrado.

Sin red: el store es el de memoria (conftest.py), con el mismo contrato que el de Supabase."""

import time

import pytest
from fastapi.testclient import TestClient

import ai_engine
import candidate as cand
import demo
import matching
import scrapers
from ai_engine import ScoredJob
from candidate import CandidateProfile, Skill
from helpers import PASSWORD, make_job, sign_up, with_csrf
from web import persist
from web import session as sessions
from web.main import app, dom_id

KEY = "AIza-test-key-0000"
EMAIL = "persona@example.com"


@pytest.fixture(autouse=True)
def no_demo_no_ai(monkeypatch):
    monkeypatch.setattr(demo, "enabled", lambda: False)
    monkeypatch.setattr(ai_engine, "check_key", lambda key, model=None: key.startswith("AIza"))
    jobs = [make_job(title="Contadora", company="Estudio Uno"), make_job(title="Analista", company="Estudio Dos")]
    scored = [ScoredJob(job=j, score=90 - i * 5, match_reasons=["Excel"], missing_skills=[], cover_letter=None,
                        summary="") for i, j in enumerate(jobs)]
    monkeypatch.setattr(scrapers, "PORTAL_SCRAPERS", {k: (lambda keywords, max_results=0: list(jobs))
                                                      for k in ("remotive", "themuse", "wwr")})
    monkeypatch.setattr(matching, "match_jobs",
                        lambda js, *a, **k: matching.MatchResult(scored=list(scored), total_found=len(js)))
    sessions.reset()


def profile() -> CandidateProfile:
    return CandidateProfile(summary="Contadora junior", target_roles=["Contadora"], seniority="junior",
                            skills=[Skill("Excel", "Manejo de Excel")], search_terms={"es": ["Contadora"]})


def session_of(client) -> sessions.Session:
    return sessions._store[client.cookies.get(sessions.COOKIE)]


def to_step4(client, monkeypatch):
    monkeypatch.setattr(cand, "extract_profile", lambda *a, **k: profile())
    client.post("/asistente/cv", files={"cv": ("cv.txt", b"Contadora junior", "text/plain")}, data={"origin": "wizard"})
    client.post("/asistente/ia", data={"key": KEY})
    client.post("/asistente/perfil", data={"summary": "Contadora junior", "roles": ["Contadora"]})


def search(client, monkeypatch, **data):
    to_step4(client, monkeypatch)
    r = client.post("/asistente/busqueda", data={"terms": ["Contadora"], "portal": ["remotive"], **data},
                    follow_redirects=False)
    s = session_of(client)
    limit = time.time() + 5
    while s.run is not None and s.run.active and time.time() < limit:
        time.sleep(0.01)
    return r, s


# ─── Muro de ingreso ─────────────────────────────────────────────────────────
def test_without_an_account_the_wizard_asks_to_sign_in():
    client = TestClient(app)
    r = client.get("/asistente/1", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/ingresar?next=/asistente/1"
    hx = client.get("/resultados", headers={"HX-Request": "true"}, follow_redirects=False)
    assert hx.status_code == 204 and hx.headers["HX-Redirect"].startswith("/ingresar")
    assert client.get("/").status_code == 200 and client.get("/crear-cuenta").status_code == 200


def test_landing_invites_to_create_an_account_instead_of_uploading():
    html = TestClient(app).get("/").text
    assert 'href="/crear-cuenta"' in html and 'action="/asistente/cv"' not in html


def test_sign_in_returns_to_where_you_were_going_but_never_off_site():
    sign_up(TestClient(app))
    client = with_csrf(TestClient(app))
    r = client.post("/ingresar", data={"email": EMAIL, "password": PASSWORD, "next": "/historial"}, follow_redirects=False)
    assert r.headers["location"] == "/historial"
    client = with_csrf(TestClient(app))
    r = client.post("/ingresar", data={"email": EMAIL, "password": PASSWORD, "next": "//evil.example"}, follow_redirects=False)
    assert r.headers["location"] == "/asistente"


def test_wrong_password_is_told_without_saying_which_part_failed():
    sign_up(TestClient(app))
    client = with_csrf(TestClient(app))
    r = client.post("/ingresar", data={"email": EMAIL, "password": "otra-clave-9"})
    assert r.status_code == 400 and "El correo o la contraseña no son correctos" in r.text
    assert client.cookies.get("jh_access") is None


def test_sign_up_with_email_confirmation(memory_store):
    memory_store.confirm_signups = True
    client = with_csrf(TestClient(app))
    r = client.post("/crear-cuenta", data={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 200 and "Revisa tu correo" in r.text and EMAIL in r.text
    r = client.post("/ingresar", data={"email": EMAIL, "password": PASSWORD})
    assert "Primero confirma tu correo" in r.text and "/crear-cuenta/reenviar" in r.text
    token = memory_store.sent_links[-1][2]
    r = client.get(f"/auth/confirmar?token_hash={token}&type=email", follow_redirects=False)
    assert r.headers["location"] == "/asistente" and client.cookies.get("jh_access")
    # El enlace sirve una sola vez.
    r = with_csrf(TestClient(app)).get(f"/auth/confirmar?token_hash={token}&type=email")
    assert r.status_code == 400 and "ya no sirve" in r.text


def test_an_existing_email_gets_the_same_answer_as_a_new_one(memory_store):
    """No se puede averiguar si alguien tiene cuenta probando su correo en el alta."""
    memory_store.confirm_signups = True
    sign_up_page = with_csrf(TestClient(app)).post("/crear-cuenta", data={"email": EMAIL, "password": PASSWORD})
    again = with_csrf(TestClient(app)).post("/crear-cuenta", data={"email": EMAIL, "password": "Otra-clave-2"})
    assert again.status_code == sign_up_page.status_code == 200 and "Revisa tu correo" in again.text


def test_password_reset_by_email(memory_store):
    sign_up(TestClient(app))
    client = with_csrf(TestClient(app))
    r = client.post("/recuperar", data={"email": EMAIL})
    assert "te enviamos un enlace" in r.text
    token = next(tok for mail, kind, tok in memory_store.sent_links if kind == "recovery")
    r = client.get(f"/auth/confirmar?token_hash={token}&type=recovery", follow_redirects=False)
    assert r.headers["location"] == "/nueva-clave"
    assert client.post("/nueva-clave", data={"password": "Nueva-clave-7"}, follow_redirects=False).status_code == 303
    fresh = with_csrf(TestClient(app))
    ok = fresh.post("/ingresar", data={"email": EMAIL, "password": "Nueva-clave-7"}, follow_redirects=False)
    assert ok.status_code == 303


def test_sign_out_forgets_the_session():
    client = sign_up(TestClient(app))
    client.get("/asistente/1")
    r = client.post("/salir", follow_redirects=False)
    assert r.headers["location"] == "/"
    assert client.cookies.get("jh_access") is None and client.cookies.get(sessions.COOKIE) is None
    assert client.get("/asistente/1", follow_redirects=False).headers["location"].startswith("/ingresar")


def test_an_invalid_access_cookie_is_cleared_and_explained():
    client = sign_up(TestClient(app))
    client.cookies.set("jh_access", "token-inventado")
    client.cookies.set("jh_refresh", "otro-inventado")
    r = client.get("/asistente/1", follow_redirects=False)
    assert r.headers["location"] == "/ingresar?next=/asistente/1&vencida=1"
    assert "Tu sesión venció" in client.get(r.headers["location"]).text


def test_an_expired_access_token_is_renewed_with_the_refresh_cookie():
    client = sign_up(TestClient(app))
    refresh = client.cookies.get("jh_refresh")
    fresh = with_csrf(TestClient(app))
    fresh.cookies.set("jh_access", "vencido")
    fresh.cookies.set("jh_refresh", refresh)
    r = fresh.get("/asistente/1", follow_redirects=False)
    assert r.status_code == 200
    renewed = [c for c in r.headers.get_list("set-cookie") if c.startswith("jh_access=")]
    assert renewed and "vencido" not in renewed[0] and "HttpOnly" in renewed[0]


def test_when_the_account_service_is_down_nothing_is_reset(memory_store):
    client = sign_up(TestClient(app))
    memory_store.fail = True
    r = client.get("/asistente/1")
    assert r.status_code == 503 and "No pudimos cargar tu cuenta" in r.text
    assert client.cookies.get("jh_access")                   # no se cierra la sesión por una caída
    assert TestClient(app).get("/health/ready").json()["checks"]["database"] is False


# ─── CSRF ────────────────────────────────────────────────────────────────────
def test_every_post_needs_the_csrf_token():
    client = sign_up(TestClient(app))
    token = client.headers.pop("X-CSRF-Token")
    assert client.post("/asistente/manual", data={"notes": "x"}).status_code == 403
    assert client.post("/asistente/manual", data={"notes": "x"}, headers={"X-CSRF-Token": "otro"}).status_code == 403
    # Sin JavaScript, el formulario lo manda en un campo oculto.
    ok = client.post("/asistente/manual", data={"notes": "Electricista", "csrf_token": token}, follow_redirects=False)
    assert ok.status_code == 303


def test_forms_carry_the_csrf_field():
    client = sign_up(TestClient(app))
    html = client.get("/asistente/1").text
    assert f'name="csrf_token" value="{client.cookies.get("jh_csrf")}"' in html


# ─── Lo guardado vuelve ──────────────────────────────────────────────────────
def test_profile_and_preferences_come_back_in_a_new_browser(monkeypatch):
    first = sign_up(TestClient(app))
    to_step4(first, monkeypatch)
    first.post("/asistente/borrador/4", data={"terms": ["Contadora", "Liquidadora"], "portal": ["remotive"],
                                               "min_score": "70", "modality": ["remote"]})
    monkeypatch.setattr(cand, "extract_profile", lambda *a, **k: pytest.fail("no debe volver a analizar el CV"))
    other = with_csrf(TestClient(app))
    other.post("/ingresar", data={"email": EMAIL, "password": PASSWORD})
    # La clave de Gemini no se guarda: se vuelve a pedir, pero el CV y el perfil siguen ahí.
    assert other.get("/asistente", follow_redirects=False).headers["location"] == "/asistente/2"
    s = session_of(other)
    assert s.cv.name == "cv.txt" and s.profile.target_roles == ["Contadora"] and s.profile_confirmed
    assert s.terms == ["Contadora", "Liquidadora"] and s.min_score == 70 and s.modalities == ["remote"]
    other.post("/asistente/ia", data={"key": KEY})
    assert other.get("/asistente/4").status_code == 200


def test_the_gemini_key_is_never_stored(monkeypatch, memory_store):
    client = sign_up(TestClient(app))
    to_step4(client, monkeypatch)
    user = persist.User(session_of(client).user_id, EMAIL)
    assert KEY not in repr(memory_store.export(user))


def test_another_account_in_the_same_browser_starts_clean(monkeypatch):
    client = sign_up(TestClient(app))
    to_step4(client, monkeypatch)
    client.post("/salir")
    sign_up(client, "otra-persona@example.com")
    client.get("/asistente/1")
    s = session_of(client)
    assert s.cv is None and s.profile is None and s.api_key == ""


def test_a_new_cv_replaces_the_stored_one_and_its_profile(monkeypatch, memory_store):
    client = sign_up(TestClient(app))
    to_step4(client, monkeypatch)
    client.post("/asistente/cv", files={"cv": ("otro.txt", b"Otro CV", "text/plain")}, data={"origin": "wizard"})
    user = persist.User(session_of(client).user_id, EMAIL)
    data = memory_store.export(user)
    assert [c["name"] for c in data["cvs"] if c["is_current"]] == ["otro.txt"]
    assert data["profile"] is None
    assert memory_store.cv_bytes(user) == b"Otro CV"


# ─── Plan: topes y cupo mensual ──────────────────────────────────────────────
def test_the_plan_caps_portals_and_evaluated_listings(monkeypatch):
    persist.use(persist.MemoryStore(plan=persist.Plan("free", 10, 2, 30)))
    client = sign_up(TestClient(app))
    to_step4(client, monkeypatch)
    s = session_of(client)
    assert len(s.portals) <= 2 and s.eval_limit <= 30
    r = client.post("/asistente/busqueda", data={"terms": ["x"], "portal": ["remotive", "themuse", "wwr"]})
    assert r.status_code == 400 and "hasta 2 portales" in r.text
    client.post("/asistente/borrador/4", data={"terms": ["x"], "portal": ["remotive"], "eval_limit": "200"})
    assert s.eval_limit == 30
    assert 'max="30"' in client.get("/asistente/4").text


def test_the_monthly_quota_stops_the_next_search(monkeypatch):
    persist.use(persist.MemoryStore(plan=persist.Plan("free", 1, 8, 30)))
    client = sign_up(TestClient(app))
    r, s = search(client, monkeypatch)
    assert r.headers["location"] == "/buscando"
    assert "Te quedan 0 de 1" in client.get("/asistente/4").text
    r = client.post("/asistente/busqueda", data={"terms": ["Contadora"], "portal": ["remotive"]})
    assert r.status_code == 429 and "Ya usaste las 1 búsquedas" in r.text


# ─── Historial y guardadas ───────────────────────────────────────────────────
def test_a_finished_search_lands_in_the_history(monkeypatch, memory_store):
    client = sign_up(TestClient(app))
    _, s = search(client, monkeypatch)
    user = persist.User(s.user_id, EMAIL)
    runs = memory_store.runs(user)
    assert len(runs) == 1 and runs[0]["status"] == "succeeded" and runs[0]["matches_created"] == 2
    stored = memory_store.run(user, runs[0]["id"])["results"]
    assert [d["job"]["title"] for d in stored] == ["Contadora", "Analista"]
    assert all("description" not in d["job"] for d in stored)        # la foto no guarda el aviso entero
    html = client.get("/historial").text
    assert "Completa" in html and f'/historial/{runs[0]["id"]}' in html


def test_an_old_search_opens_in_the_results_screen(monkeypatch):
    client = sign_up(TestClient(app))
    _, s = search(client, monkeypatch)
    run_id = s.run.db_id
    s.run = None                                     # como si fuera otra sesión
    r = client.get(f"/historial/{run_id}", follow_redirects=False)
    assert r.headers["location"] == "/resultados"
    html = client.get("/resultados").text
    assert "Estás viendo tu búsqueda del" in html and "Contadora" in html


def test_the_last_search_is_there_after_signing_in_again(monkeypatch):
    client = sign_up(TestClient(app))
    search(client, monkeypatch)
    other = with_csrf(TestClient(app))
    other.post("/ingresar", data={"email": EMAIL, "password": PASSWORD})
    assert "Estudio Uno" in other.get("/resultados").text


def test_save_and_dismiss_a_listing(monkeypatch):
    client = sign_up(TestClient(app))
    _, s = search(client, monkeypatch)
    first = s.run.result.scored[0]
    did = dom_id(first.job)
    card = client.post(f"/ofertas/{did}/guardar", headers={"HX-Request": "true"}).text
    assert "Guardada ✓" in card and f"/ofertas/{did}/quitar" in card
    assert "Contadora" in client.get("/historial").text.split("Guardadas")[1]
    r = client.post(f"/ofertas/{did}/descartar", headers={"HX-Request": "true"})
    assert "job-gone" in r.text and "Deshacer" in r.text and r.headers["HX-Trigger"] == "jh-jobs"
    counts = client.get("/resultados/lista", headers={"HX-Request": "true"}).text
    assert 'id="chip-dismissed" hx-swap-oob="true"' in counts and "Descartadas (1)" in counts
    assert "Estudio Uno" not in client.get("/resultados").text
    assert "Estudio Uno" in client.get("/resultados?show=dismissed").text
    client.post(f"/ofertas/{did}/quitar")
    assert "Estudio Uno" in client.get("/resultados").text
    assert client.post("/ofertas/nada/guardar").status_code == 204
    assert client.post(f"/ofertas/{did}/borrar-todo").status_code == 404


# ─── Mi cuenta ───────────────────────────────────────────────────────────────
def test_account_page_shows_usage_and_the_cv(monkeypatch):
    persist.use(persist.MemoryStore(plan=persist.Plan("free", 10, 8, 30)))
    client = sign_up(TestClient(app))
    search(client, monkeypatch)
    html = client.get("/cuenta").text
    assert EMAIL in html and "Usaste 1 de 10 búsquedas" in html and "cv.txt" in html


def test_deleting_the_cv_also_deletes_its_profile(monkeypatch, memory_store):
    client = sign_up(TestClient(app))
    to_step4(client, monkeypatch)
    r = client.post("/cuenta/cv/borrar", follow_redirects=False)
    assert r.headers["location"] == "/cuenta?hecho=cv"
    user = persist.User(session_of(client).user_id, EMAIL)
    assert memory_store.cv_bytes(user) is None and memory_store.account(user).profile is None
    assert client.get("/asistente", follow_redirects=False).headers["location"] == "/asistente/1"


def test_export_downloads_the_account_data(monkeypatch):
    client = sign_up(TestClient(app))
    search(client, monkeypatch)
    r = client.get("/cuenta/datos.json")
    assert r.headers["content-disposition"].startswith("attachment") and r.json()["email"] == EMAIL
    assert "files" not in r.json()


def test_deleting_the_account_needs_the_email_and_really_deletes(monkeypatch, memory_store):
    client = sign_up(TestClient(app))
    search(client, monkeypatch)
    wrong = client.post("/cuenta/borrar", data={"confirm": "otro@example.com"})
    assert wrong.status_code == 400 and "No borramos nada" in wrong.text
    r = client.post("/cuenta/borrar", data={"confirm": EMAIL.upper()}, follow_redirects=False)
    assert r.headers["location"] == "/?cuenta=borrada"
    assert memory_store.deletions[-1]["completed_at"] is not None
    assert client.get("/asistente/1", follow_redirects=False).headers["location"].startswith("/ingresar")
    again = with_csrf(TestClient(app)).post("/ingresar", data={"email": EMAIL, "password": PASSWORD})
    assert again.status_code == 400
