import pytest

import scrapers
from scrapers import _clean_desc, matches_keywords


@pytest.mark.parametrize("keywords,text,expected", [
    (["java"], "Senior JavaScript developer", False),
    (["java"], "Java developer", True),
    (["go"], "Google Ads manager", False),
    (["c++"], "Embedded C++ role", True),
    (["node.js"], "node.js backend", True),
    (["contador"], "Contador público", True),
    (["enfermería"], "Licenciada en Enfermería", True),
    (["react native"], "React Native dev", True),
    ([], "anything", True),
    (["  "], "anything", True),
])
def test_matches_keywords_whole_word(keywords, text, expected):
    assert matches_keywords(keywords, text) is expected


def test_clean_desc_strips_html_before_truncating():
    html = "<p>Hola <b>mundo</b> &amp; más</p>" + "<div>x</div>" * 5000
    out = _clean_desc(html)
    assert out.startswith("Hola mundo & más")
    assert "<" not in out and len(out) <= 3000


# ─── Get on Board por su API ─────────────────────────────────────────────────
def _gob_response(**over):
    attrs = {"title": "Desarrollador Python", "remote": True, "countries": ["Chile"],
             "location_cities": {"data": []}, "description": "<p>Trabajo con <b>Django</b></p>",
             "functions": "", "desirable": "", "published_at": 1790000000,
             "min_salary": 3000, "max_salary": 4000,
             "company": {"data": {"attributes": {"name": "Empresa Ficticia"}}}}
    attrs.update(over)
    return {"data": [{"id": "dev-python-empresa", "attributes": attrs}]}


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_getonboard_reads_the_api_once_per_keyword(monkeypatch):
    """Antes abría cada aviso: cientos de peticiones. Ahora, una por término."""
    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append((url, params["query"]))
        return _FakeResp(_gob_response())

    monkeypatch.setattr(scrapers.requests, "get", fake_get)
    jobs = scrapers.scrape_getonboard(["python", "django"])
    assert [c[1] for c in calls] == ["python", "django"]
    assert all("api/v0/search/jobs" in c[0] for c in calls)
    job = jobs[0]
    assert job.title == "Desarrollador Python" and job.company == "Empresa Ficticia"
    assert job.location == "Chile" and job.remote is True
    assert job.url == "https://www.getonbrd.com/jobs/dev-python-empresa"
    assert "Django" in job.description and "<b>" not in job.description
    assert job.salary == "USD 3,000 - 4,000"
    assert len(jobs) == 1                      # el mismo aviso en dos términos no se duplica


def test_getonboard_survives_a_broken_answer(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("500")

    monkeypatch.setattr(scrapers.requests, "get", boom)
    assert scrapers.scrape_getonboard(["python"]) == []


def test_get_all_jobs_uses_the_registry_and_dedupes(monkeypatch):
    from helpers import make_job
    monkeypatch.setattr(scrapers, "PORTAL_SCRAPERS", {
        "a": lambda kw, mx=0: [make_job(title="Analista", company="ACME")],
        "b": lambda kw, mx=0: [make_job(title="Analista", company="ACME"), make_job(title="Otro", company="ACME")],
        "c": lambda kw, mx=0: (_ for _ in ()).throw(RuntimeError("caído")),
    })
    jobs = scrapers.get_all_jobs(["analista"])
    assert [j.title for j in jobs] == ["Analista", "Otro"]      # el portal caído no rompe nada
