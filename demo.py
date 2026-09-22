"""
demo.py — Datos ficticios para revisar la interfaz sin gastar cuota de Gemini.

Solo desarrollo: se activa con la variable de entorno JOB_HUNTER_DEMO=1
(PowerShell: `$env:JOB_HUNTER_DEMO="1"; streamlit run app.py`). Nunca se define en producción.
Los perfiles y ofertas salen de eval/dataset.json (100% ficticios); los scores son inventados.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import matching
import normalize
from ai_engine import FactorScore, ScoredJob
from candidate import CandidateProfile
from scrapers import JobPosting

DATASET = Path(__file__).resolve().parent / "eval" / "dataset.json"


def enabled() -> bool:
    return os.environ.get("JOB_HUNTER_DEMO") == "1"


def _factors(skills, seniority, role, language, location, ej, ecv) -> dict[str, FactorScore]:
    vals = dict(skills=skills, seniority=seniority, role=role, language=language, location=location)
    return {k: FactorScore(v, ej if k in ("skills", "role") else "", ecv if k in ("skills", "role") else "")
            for k, v in vals.items()}


def load() -> tuple[CandidateProfile, list[ScoredJob]]:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    profile = CandidateProfile.from_dict(next(p for p in data["profiles"] if p["id"] == "p_accountant")["profile"])
    profile.search_terms = {"es": ["Contador", "Analista contable", "Liquidación de impuestos"],
                            "en": ["Accountant", "Junior accountant"]}

    jobs = {j["id"]: j for j in data["jobs"]}
    plan = [  # (job_id, factores, motivos, faltantes)
        ("j_ac_1", (95, 100, 100, 100, 100), ["Liquidación de IVA e Ingresos Brutos", "Conciliaciones bancarias"], []),
        ("j_ac_4", (80, 100, 90, 60, 100), ["Conciliaciones bancarias", "Experiencia junior"], ["QuickBooks", "Inglés fluido"]),
        ("j_ac_2", (75, 60, 90, 100, 100), ["Liquidación de impuestos", "Conciliaciones"], ["Cierres mensuales", "ERP"]),
        ("j_da_4", (55, 100, 50, 100, 60), ["Excel"], ["Power BI", "SQL"]),
        ("j_ac_3", (50, 20, 90, 100, 60), ["Liquidación de impuestos"], ["Balances y auditoría", "7+ años"]),
        ("j_re_1", (10, 100, 0, 100, 60), [], ["Reclutamiento"]),
    ]
    scored = []
    for jid, f, reasons, missing in plan:
        j = jobs[jid]
        job = normalize.enrich(JobPosting(id=jid, title=j["title"], company=j["company"], description=j["description"],
                                          location=j["location"], remote=j["remote"], url="https://example.com/oferta",
                                          source="Demo"))
        factors = _factors(*f, ej=j["description"][:90], ecv="Asistente contable junior: liquidación de IVA")
        scored.append(ScoredJob(job=job, score=matching.compute_score(factors), match_reasons=reasons,
                                missing_skills=missing, cover_letter=None,
                                summary=f"Afinidad estimada con {j['title']}.", evaluated=True, factors=factors))
    scored.sort(key=lambda s: -s.score)
    return profile, scored
