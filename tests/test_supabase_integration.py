"""SupabaseStore contra un Supabase real (el local de `supabase start`): RLS, Storage, cupo y borrado.

No corre en CI ni por defecto. Para correrlo, con el stack local arriba:
    . .\\scripts\\dev-env.ps1; $env:JH_SUPABASE_TESTS="1"; pytest tests/test_supabase_integration.py -q
Crea usuarios ficticios y los borra al terminar.
"""

import os
import uuid

import pytest
import requests

from web import persist
from web.persist import AuthError, Plan
from web.supa import SupabaseStore

URL = os.environ.get("SUPABASE_URL", "")
PUB = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")
SECRET = os.environ.get("SUPABASE_SECRET_KEY", "")

pytestmark = pytest.mark.skipif(not (os.environ.get("JH_SUPABASE_TESTS") and URL and PUB and SECRET),
                                reason="integración con Supabase: JH_SUPABASE_TESTS=1 y las variables SUPABASE_*")
PASSWORD = "clave-ficticia-1"


def admin_headers() -> dict:
    h = {"apikey": SECRET}
    if SECRET.startswith("eyJ"):
        h["Authorization"] = f"Bearer {SECRET}"
    return h


@pytest.fixture
def store():
    return SupabaseStore(URL, PUB, SECRET)


@pytest.fixture
def users(store):
    """Dos cuentas confirmadas (creadas por la API de administración, sin correo)."""
    made = []

    def make() -> persist.User:
        email = f"prueba-{uuid.uuid4().hex[:10]}@example.com"
        r = requests.post(f"{URL}/auth/v1/admin/users", headers=admin_headers(), timeout=10,
                          json={"email": email, "password": PASSWORD, "email_confirm": True})
        assert r.status_code in (200, 201), r.text
        made.append(r.json()["id"])
        return store.sign_in(email, PASSWORD).user

    yield make
    for uid in made:
        requests.delete(f"{URL}/auth/v1/admin/users/{uid}", headers=admin_headers(), timeout=10)


def rest(user: persist.User, table: str, method="GET", **kw):
    return requests.request(method, f"{URL}/rest/v1/{table}", timeout=10,
                            headers={"apikey": PUB, "Authorization": f"Bearer {user.access_token}"}, **kw)


def test_sign_in_errors_are_stable_codes(store, users):
    user = users()
    with pytest.raises(AuthError) as e:
        store.sign_in(user.email, "otra-clave-9")
    assert e.value.code == "invalid_credentials"
    assert store.user_for_token(user.access_token).id == user.id
    assert store.user_for_token("no-es-un-token") is None


def test_new_accounts_get_a_profile_and_the_free_plan(store, users):
    acc = store.account(users())
    assert acc.plan == Plan("free", 10, 8, 30)
    assert acc.cv is None and acc.profile is None and acc.preferences is None


def test_cv_profile_and_preferences_round_trip(store, users):
    user = users()
    cv_id = store.save_cv(user, name="cv.pdf", mime="application/pdf", data=b"%PDF-1.4 ficticio", sha="a" * 64)
    assert store.cv_bytes(user) == b"%PDF-1.4 ficticio"
    store.mark_cv_parsed(user, cv_id, {"summary": "x"}, "models/test")
    store.save_profile(user, {"summary": "Contadora", "target_roles": ["Contadora"], "skills": [{"name": "Excel"}],
                              "languages": [{"language": "Español", "level": "nativo"}], "location": "unknown"},
                       confirmed=True, source="cv", cv_id=cv_id)
    store.save_preferences(user, {"terms": ["Contadora"], "modalities": ["remote"], "locations": "Mendoza, Chile",
                                  "job_languages": ["es"], "portals": ["remotive"], "min_score": 70, "eval_limit": 30})
    acc = store.account(user)
    assert acc.cv["id"] == cv_id and acc.cv["parsed"] and acc.cv["size"] == len(b"%PDF-1.4 ficticio")
    assert acc.profile["summary"] == "Contadora" and acc.profile_confirmed
    assert acc.preferences["locations"] == "Mendoza, Chile" and acc.preferences["min_score"] == 70
    # Otro CV reemplaza al anterior: su archivo y el perfil que salió de él se van.
    store.save_cv(user, name="otro.txt", mime="text/plain", data=b"otro", sha="b" * 64)
    acc = store.account(user)
    assert acc.cv["name"] == "otro.txt" and acc.profile is None
    store.delete_cv(user)
    assert store.cv_bytes(user) is None and store.account(user).cv is None


def test_rls_keeps_each_account_to_itself(store, users):
    a, b = users(), users()
    store.save_cv(a, name="cv.txt", mime="text/plain", data=b"privado", sha="c" * 64)
    store.set_job_state(a, "f" * 32, "saved", {"job": {"title": "x"}}, None)
    assert rest(b, "cv_documents", params={"select": "id"}).json() == []
    assert rest(b, "saved_jobs", params={"select": "job_key"}).json() == []
    path = rest(a, "cv_documents", params={"select": "storage_path"}).json()[0]["storage_path"]
    other = requests.get(f"{URL}/storage/v1/object/cv-documents/{path}", timeout=10,
                         headers={"apikey": PUB, "Authorization": f"Bearer {b.access_token}"})
    assert other.status_code >= 400
    # Lo que decide el cupo lo escribe solo el servidor.
    assert rest(a, "search_runs", "POST", json={"user_id": a.id, "status": "succeeded"}).status_code in (401, 403)
    assert rest(a, "usage_events", "POST", json={"user_id": a.id, "event_type": "search_run"}).status_code in (401, 403)
    assert rest(a, "plans", "PATCH", params={"id": "eq.free"}, json={"monthly_search_limit": 999}).status_code in (401, 403, 404) \
        or store.plan(a).monthly_search_limit == 10


def test_the_monthly_quota_is_atomic_on_the_server(store, users):
    user = users()
    plan = Plan("free", 1, 8, 30)
    run_id = store.start_run(user.id, plan, {"sources_requested": 1, "query": {"terms": ["x"]}, "lang": "es"})
    assert run_id and store.start_run(user.id, plan, {"query": {}}) is None
    assert store.searches_used(user) == 1
    store.finish_run(user.id, run_id, {"status": "succeeded", "results": [{"job": {"title": "x"}, "score": 80}],
                                       "funnel": {"found": 1}, "matches_created": 1})
    assert store.runs(user)[0]["status"] == "succeeded"
    assert store.latest_run_with_results(user)["results"][0]["score"] == 80
    assert store.run(user, "no-es-uuid") is None


def test_deleting_the_account_removes_everything(store, users):
    user = users()
    store.save_cv(user, name="cv.txt", mime="text/plain", data=b"privado", sha="d" * 64)
    store.set_job_state(user, "e" * 32, "saved", {"job": {"title": "x"}}, None)
    store.delete_account(user)
    assert store.user_for_token(user.access_token) is None
    listed = requests.post(f"{URL}/storage/v1/object/list/cv-documents", headers=admin_headers(), timeout=10,
                           json={"prefix": user.id, "limit": 10}).json()
    assert listed == []
    left = requests.get(f"{URL}/rest/v1/account_deletions", headers=admin_headers(), timeout=10,
                        params={"select": "user_id,completed_at", "order": "requested_at.desc", "limit": "1"}).json()
    assert left[0]["user_id"] is None and left[0]["completed_at"]
