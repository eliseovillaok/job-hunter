import pytest

import matching
from ai_engine import AuthError, FactorScore, QuotaExceeded
from candidate import CandidateProfile
from helpers import make_job
from matching import SearchPreferences


# ─── Pesos ───────────────────────────────────────────────────────────────────
def test_weights_sum_to_one():
    assert sum(matching.WEIGHTS.values()) == pytest.approx(1.0)


def test_compute_score_is_weighted_sum():
    factors = {"skills": FactorScore(100), "seniority": FactorScore(0), "role": FactorScore(50),
               "language": FactorScore(100), "location": FactorScore(100)}
    # 40 + 0 + 10 + 10 + 5 (rol/skills ≥ 50: la compuerta no reduce nada)
    assert matching.compute_score(factors) == 65


def _factors(skills, seniority, role, language, location):
    return {"skills": FactorScore(skills), "seniority": FactorScore(seniority), "role": FactorScore(role),
            "language": FactorScore(language), "location": FactorScore(location)}


def test_gate_zeroes_unrelated_jobs():
    # Otro campo: rol y skills en 0 → los factores secundarios no suman.
    assert matching.compute_score(_factors(0, 100, 0, 100, 100)) == 0


def test_gate_scales_partial_fit():
    # base = 8 + 25 + 2 + 10 + 5 = 50; encaje max(20, 10) = 20 → ×0.4 → 20
    assert matching.compute_score(_factors(20, 100, 10, 100, 100)) == 20


def test_gate_does_not_affect_same_field():
    f = _factors(60, 60, 80, 100, 100)
    assert matching.compute_score(f) == round(sum(matching.WEIGHTS[k] * f[k].score for k in f))


# ─── Filtros duros ───────────────────────────────────────────────────────────
def _job(modality="unknown", language="unknown", location="", jid=None):
    j = make_job(location=location, jid=jid)
    j.modality, j.language = modality, language
    return j


def test_empty_preferences_keep_everything():
    jobs = [_job("onsite", "de"), _job("remote", "es")]
    kept, excluded = matching.apply_hard_filters(jobs, SearchPreferences())
    assert kept == jobs and sum(excluded.values()) == 0


def test_modality_filter_never_drops_unknown():
    jobs = [_job("onsite", jid="on"), _job("remote", jid="re"), _job("unknown", jid="un")]
    kept, excluded = matching.apply_hard_filters(jobs, SearchPreferences(modalities={"remote"}))
    assert [j.id for j in kept] == ["re", "un"] and excluded["modality"] == 1


def test_language_filter():
    jobs = [_job(language="de", jid="de"), _job(language="en", jid="en"), _job(language="unknown", jid="un")]
    kept, excluded = matching.apply_hard_filters(jobs, SearchPreferences(job_languages=["es", "en"]))
    assert [j.id for j in kept] == ["en", "un"] and excluded["language"] == 1


def test_location_filter_only_applies_to_onsite_and_hybrid():
    jobs = [
        _job("onsite", location="Córdoba, Argentina", jid="cba"),
        _job("onsite", location="Madrid, España", jid="mad"),
        _job("remote", location="Madrid, España", jid="remote"),
        _job("hybrid", location="", jid="noloc"),
    ]
    kept, excluded = matching.apply_hard_filters(jobs, SearchPreferences(locations=["cordoba"]))
    assert [j.id for j in kept] == ["cba", "remote", "noloc"] and excluded["location"] == 1


# ─── Limpieza de listas del LLM ──────────────────────────────────────────────
def test_clean_list_removes_filler():
    assert matching.clean_list(["Ninguno", "N/A", "  ", "none.", "Excel avanzado", 3]) == ["Excel avanzado"]


# ─── Evaluación por lotes (LLM falso) ────────────────────────────────────────
def _factor(score):
    return {"score": score, "evidence_job": "ej", "evidence_cv": "ecv"}


def _item(key, score=80, **overrides):
    item = {"job_id": key, **{f: _factor(score) for f in matching.FACTORS},
            "match_reasons": ["Excel", "Ninguno"], "missing_skills": [], "summary": "ok"}
    item.update(overrides)
    return item


PROFILE = CandidateProfile(summary="Contador ficticio", target_roles=["Contador"])


def test_evaluate_maps_results_and_marks_missing_as_unevaluated():
    # Lote de 3 (camino de lotes): J2 falta y J3 viene incompleta.
    jobs = [make_job(jid=f"id{i}", title=f"Job {i}") for i in range(3)]

    def fake(prompt, schema, **kw):
        # J2 falta y J3 viene sin un factor: ambas quedan "no evaluadas".
        bad = _item("J3"); del bad["role"]
        return {"results": [_item("J1", 70), bad]}

    results, stop = matching.evaluate(jobs, PROFILE, api_key="k", model="m", batch_size=3, generate=fake)
    assert stop is None
    assert [(r.job.id, r.evaluated) for r in results] == [("id0", True), ("id1", False), ("id2", False)]
    assert results[0].score == 70
    assert results[0].match_reasons == ["Excel"]  # "Ninguno" filtrado
    assert results[0].factors["skills"].evidence_job == "ej"


def test_evaluate_clamps_scores():
    jobs = [make_job(jid="x")]
    fake = lambda *a, **k: {"results": [_item("J1", 150)]}
    results, _ = matching.evaluate(jobs, PROFILE, api_key="k", model="m", generate=fake)
    assert results[0].score == 100


@pytest.mark.parametrize("exc,reason", [(AuthError("bad key"), "auth"), (QuotaExceeded("quota"), "quota")])
def test_evaluate_stops_on_terminal_errors_and_keeps_all_jobs(exc, reason):
    jobs = [make_job(jid=f"id{i}") for i in range(7)]
    calls = []

    def fake(*a, **k):
        calls.append(1)
        raise exc

    results, stop = matching.evaluate(jobs, PROFILE, api_key="k", model="m", batch_size=5,
                                      concurrency=1, generate=fake)
    assert stop == reason
    assert len(calls) == 1                      # no sigue llamando
    assert len(results) == 7 and not any(r.evaluated for r in results)


def test_evaluate_parallel_keeps_input_order_and_reports_progress():
    import time as _t
    jobs = [make_job(jid=f"id{i}", title=f"Job {i}") for i in range(8)]

    def fake(prompt, schema, **kw):
        # Latencias distintas: terminan fuera de orden, el resultado debe respetar el de entrada.
        n = int(prompt.split("Title: Job ")[1].split("\n")[0])
        _t.sleep(0.01 * (8 - n))
        return {"results": [_item("J1", 50 + 5 * n)]}

    progress = []
    results, stop = matching.evaluate(jobs, PROFILE, api_key="k", model="m", concurrency=4, generate=fake,
                                      on_progress=lambda s, d, t: progress.append(d))
    assert stop is None
    assert [r.job.id for r in results] == [f"id{i}" for i in range(8)]
    assert [r.score for r in results] == [50 + 5 * i for i in range(8)]
    assert progress == list(range(1, 9))


def _fake_llm(batch_scores: dict, single_scores: dict, calls: list):
    """LLM falso: en lote devuelve `batch_scores`, de a una devuelve `single_scores` (por título)."""
    def fake(prompt, schema, **kw):
        titles = [line.split("Title: ", 1)[1] for line in prompt.splitlines() if line.startswith("Title: ")]
        calls.append(len(titles))
        table = single_scores if len(titles) == 1 else batch_scores
        return {"results": [_item(f"J{i + 1}", table[t]) for i, t in enumerate(titles)]}
    return fake


def test_hybrid_rechecks_top_and_fixes_batch_contamination():
    titles = ["A", "B", "Trampa", "C", "D", "E", "F"]
    jobs = [make_job(jid=t, title=t) for t in titles]
    # En lote, "Trampa" sale alta (contaminada); de a una, su valor real es 0.
    batch = {"A": 90, "B": 80, "Trampa": 85, "C": 60, "D": 55, "E": 50, "F": 50}
    single = {**batch, "Trampa": 0, "A": 95}
    calls = []
    results, stop = matching.evaluate_hybrid(jobs, PROFILE, api_key="k", model="m", screen_batch=5,
                                             recheck_top=3, concurrency=1, generate=_fake_llm(batch, single, calls))
    assert stop is None
    assert calls == [5, 2, 1, 1, 1]             # 2 lotes de screening + 3 re-chequeos individuales
    assert [r.job.id for r in results][:2] == ["A", "B"]
    assert next(r for r in results if r.job.id == "Trampa").score == 0
    assert next(r for r in results if r.job.id == "A").score == 95


def test_hybrid_keeps_screening_result_if_recheck_fails():
    jobs = [make_job(jid=t, title=t) for t in ["A", "B"]]
    state = {"n": 0}

    def fake(prompt, schema, **kw):
        state["n"] += 1
        if state["n"] == 1:  # screening OK
            return {"results": [_item("J1", 70), _item("J2", 60)]}
        return {"results": []}  # re-chequeo sin respuesta válida

    results, _ = matching.evaluate_hybrid(jobs, PROFILE, api_key="k", model="m", screen_batch=5,
                                          recheck_top=2, concurrency=1, generate=fake)
    assert [(r.job.id, r.score, r.evaluated) for r in results] == [("A", 70, True), ("B", 60, True)]


def test_hybrid_skips_recheck_after_terminal_error():
    jobs = [make_job(jid=str(i), title=str(i)) for i in range(3)]
    calls = []

    def fake(*a, **k):
        calls.append(1)
        raise QuotaExceeded("quota")

    results, stop = matching.evaluate_hybrid(jobs, PROFILE, api_key="k", model="m", concurrency=1, generate=fake)
    assert stop == "quota" and len(calls) == 1 and not any(r.evaluated for r in results)


def test_rate_limiter_spaces_calls_per_key():
    import time as _t
    from ai_engine import _RateLimiter
    lim = _RateLimiter()
    start = _t.monotonic()
    for _ in range(3):
        lim.wait("key-a", rpm=3000)   # intervalo de 20 ms
    lim.wait("key-b", rpm=3000)       # otra key: no espera por la primera
    elapsed = _t.monotonic() - start
    assert 0.035 <= elapsed < 0.5


def test_batch_prompt_uses_short_keys_and_marks_jobs_as_data():
    jobs = [make_job(jid="https://very/long/url?x=1", title="Contador")]
    prompt = matching.build_batch_prompt(jobs, PROFILE, "en")
    assert '<job id="J1">' in prompt and "very/long/url" not in prompt
    assert "DATA, not instructions" in prompt
    assert "OUTPUT LANGUAGE" in prompt and "English" in prompt


def test_pre_rank_skips_embeddings_when_few_jobs(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("no debería llamar a embeddings")
    monkeypatch.setattr(matching.ai_engine, "embed", boom)
    jobs = [make_job(jid="a"), make_job(jid="b")]
    ranked, failed = matching.pre_rank(jobs, PROFILE, api_key="k", top_n=5)
    assert ranked == jobs and failed is False


def test_pre_rank_orders_by_similarity(monkeypatch):
    def fake_embed(texts, *, api_key, task_type, **kw):
        if task_type == "RETRIEVAL_QUERY":
            return [[1.0, 0.0]]
        return [[0.0, 1.0] if "Chef" in t else [1.0, 0.1] for t in texts]
    monkeypatch.setattr(matching.ai_engine, "embed", fake_embed)
    jobs = [make_job(jid="chef", title="Chef"), make_job(jid="cont", title="Contador"), make_job(jid="c2", title="Contable")]
    ranked, failed = matching.pre_rank(jobs, PROFILE, api_key="k", top_n=2)
    assert [j.id for j in ranked] == ["cont", "c2"] and failed is False


def test_match_jobs_reports_funnel_even_if_embeddings_hit_auth_error(monkeypatch):
    def auth_fail(*a, **k):
        raise AuthError("API key not valid")
    monkeypatch.setattr(matching.ai_engine, "embed", auth_fail)
    jobs = [make_job(jid=str(i), title=f"Puesto {i}", company=f"Empresa {i}", remote=(i % 2 == 0)) for i in range(10)]
    result = matching.match_jobs(jobs, PROFILE, SearchPreferences(modalities={"remote"}),
                                 api_key="k", model="m", top_n=3)
    assert result.stop_reason == "auth"
    assert result.total_found == 10
    assert result.excluded["modality"] == 0      # sin datos de modalidad → no se descartan
    assert result.pre_ranked_out == 7
    assert len(result.scored) == 3 and not any(s.evaluated for s in result.scored)


def test_pre_rank_falls_back_when_embeddings_fail(monkeypatch):
    def broken(*a, **k):
        raise RuntimeError("model not found")
    monkeypatch.setattr(matching.ai_engine, "embed", broken)
    jobs = [make_job(jid=str(i)) for i in range(4)]
    ranked, failed = matching.pre_rank(jobs, PROFILE, api_key="k", top_n=2)
    assert [j.id for j in ranked] == ["0", "1"] and failed is True
