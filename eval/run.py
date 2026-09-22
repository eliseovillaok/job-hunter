"""
eval/run.py — Mide si el matching es bueno y parejo entre profesiones.

Uso (desde la raíz del repo, con GEMINI_API_KEY en .env o en el entorno):
    python -m eval.run                         # los 12 perfiles contra las 48 ofertas
    python -m eval.run --profiles p_nurse,p_chef
    python -m eval.run --pre-rank --top-n 12   # incluye el pre-ranking con embeddings
    python -m eval.run --repeat-check          # re-evalúa un perfil para medir estabilidad

Relevancia esperada (reglas, no etiquetas a mano):
    2 = misma profesión y mismo nivel de seniority
    1 = misma profesión a otro nivel, o profesión vecina a ≤1 nivel
    0 = el resto
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import ai_engine  # noqa: E402
import matching  # noqa: E402
import normalize  # noqa: E402
from candidate import CandidateProfile  # noqa: E402
from scrapers import JobPosting  # noqa: E402

DATASET = Path(__file__).resolve().parent / "dataset.json"
REPORTS = Path(__file__).resolve().parent / "reports"
K = 5
# Umbrales para marcar una profesión como problemática.
MIN_NDCG = 0.80
MIN_SEPARATION = 30
MIN_RELEVANT_MEAN = 60


def load_env() -> None:
    """Carga KEY=VALUE de .env sin imprimir nada. No pisa variables ya definidas."""
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def relevance(profile: dict, job: dict, levels: dict, adjacent: set) -> int:
    dist = abs(levels[profile["level"]] - levels[job["level"]])
    if profile["profession"] == job["profession"]:
        return 2 if dist == 0 else 1
    if frozenset((profile["profession"], job["profession"])) in adjacent and dist <= 1:
        return 1
    return 0


def ndcg_at_k(ranked_rels: list[int], k: int) -> float:
    def dcg(rels):
        return sum((2 ** r - 1) / math.log2(i + 2) for i, r in enumerate(rels[:k]))
    ideal = dcg(sorted(ranked_rels, reverse=True))
    return dcg(ranked_rels) / ideal if ideal else 0.0


def _mean(xs):
    return statistics.mean(xs) if xs else float("nan")


def to_job(d: dict) -> JobPosting:
    job = JobPosting(id=d["id"], title=d["title"], company=d["company"], description=d["description"],
                     location=d["location"], remote=d["remote"], url="", source="Eval")
    return normalize.enrich(job)


def throttled(fn, delay: float):
    def wrapper(*a, **k):
        time.sleep(delay)
        return fn(*a, **k)
    return wrapper


def evaluate_profile(p: dict, jobs: list[JobPosting], args, api_key: str, generate):
    profile = CandidateProfile.from_dict(p["profile"])
    candidates = jobs
    if args.pre_rank:
        candidates, failed = matching.pre_rank(jobs, profile, api_key=api_key, top_n=args.top_n)
        if failed:
            print("  ! embeddings no disponibles: sin pre-ranking")
    if args.mode == "hybrid":
        scored, stop = matching.evaluate_hybrid(candidates, profile, api_key=api_key, model=args.model,
                                                lang=args.lang, generate=generate)
    else:
        scored, stop = matching.evaluate(candidates, profile, api_key=api_key, model=args.model, lang=args.lang,
                                         batch_size=1 if args.mode == "single" else matching.SCREEN_BATCH,
                                         generate=generate)
    return scored, stop, candidates


def main() -> int:
    ap = argparse.ArgumentParser(description="Eval del matching con perfiles y ofertas ficticios")
    ap.add_argument("--profiles", help="IDs separados por coma (default: todos)")
    ap.add_argument("--model", default=ai_engine.DEFAULT_MODEL)
    ap.add_argument("--lang", default="es")
    ap.add_argument("--pre-rank", action="store_true", help="Pasar primero por el pre-ranking con embeddings")
    ap.add_argument("--top-n", type=int, default=12)
    ap.add_argument("--delay", type=float, default=2.0, help="Segundos entre llamadas (rate limit)")
    ap.add_argument("--repeat-check", action="store_true", help="Re-evalúa el primer perfil y mide la variación")
    ap.add_argument("--mode", choices=["hybrid", "single", "batch"], default="hybrid",
                    help="hybrid (producción), single (todo de a una) o batch (todo en lotes)")
    args = ap.parse_args()

    load_env()
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("Falta GEMINI_API_KEY (en .env o en el entorno).")
        return 1

    data = json.loads(DATASET.read_text(encoding="utf-8"))
    levels = data["levels"]
    adjacent = {frozenset(pair) for pair in data["adjacent"]}
    profiles = data["profiles"]
    if args.profiles:
        wanted = set(args.profiles.split(","))
        profiles = [p for p in profiles if p["id"] in wanted]
    jobs = [to_job(j) for j in data["jobs"]]
    job_meta = {j["id"]: j for j in data["jobs"]}
    generate = throttled(ai_engine.generate_json, args.delay)

    rows, details = [], []
    started = time.monotonic()
    for p in profiles:
        print(f"→ {p['id']} ({p['profession']}, {p['level']})")
        scored, stop, candidates = evaluate_profile(p, jobs, args, api_key, generate)
        if stop:
            print(f"  ✗ evaluación interrumpida: {stop}")
            return 2
        rel = {j.id: relevance(p, job_meta[j.id], levels, adjacent) for j in jobs}
        evaluated = [s for s in scored if s.evaluated]
        ranked = sorted(evaluated, key=lambda s: -s.score)
        # Las relevantes que el pre-ranking dejó afuera cuentan como no encontradas.
        ranked_rels = [rel[s.job.id] for s in ranked] + [r for jid, r in rel.items()
                                                         if jid not in {c.id for c in candidates}]
        by_rel = {r: [s.score for s in evaluated if rel[s.job.id] == r] for r in (0, 1, 2)}
        row = {
            "id": p["id"], "profession": p["profession"], "level": p["level"],
            "ndcg": ndcg_at_k(ranked_rels, K),
            "p_at_k": sum(1 for s in ranked[:K] if rel[s.job.id] == 2) / K,
            "mean2": _mean(by_rel[2]), "mean1": _mean(by_rel[1]), "mean0": _mean(by_rel[0]),
            "unevaluated": len(scored) - len(evaluated),
        }
        if args.pre_rank:
            total_rel2 = sum(1 for r in rel.values() if r == 2)
            row["recall_pre"] = sum(1 for c in candidates if rel[c.id] == 2) / total_rel2 if total_rel2 else float("nan")
        row["separation"] = row["mean2"] - row["mean0"]
        row["flags"] = [f for f, bad in (
            ("ndcg", row["ndcg"] < MIN_NDCG),
            ("separation", not row["separation"] >= MIN_SEPARATION),
            ("relevant_low", not row["mean2"] >= MIN_RELEVANT_MEAN),
            ("unevaluated", row["unevaluated"] > 0),
        ) if bad]
        rows.append(row)
        details.append((p, ranked[:K], rel))
        print(f"  NDCG@{K}={row['ndcg']:.2f}  P@{K}={row['p_at_k']:.2f}  "
              f"rel2={row['mean2']:.0f} rel1={row['mean1']:.0f} rel0={row['mean0']:.0f}  {' '.join(row['flags'])}")

    repeat = None
    if args.repeat_check and profiles:
        p = profiles[0]
        first = {s.job.id: s.score for s in evaluate_profile(p, jobs, args, api_key, generate)[0] if s.evaluated}
        second = {s.job.id: s.score for s in evaluate_profile(p, jobs, args, api_key, generate)[0] if s.evaluated}
        common = first.keys() & second.keys()
        diffs = [abs(first[k] - second[k]) for k in common]
        repeat = {"profile": p["id"], "mean_abs_diff": _mean(diffs), "max_abs_diff": max(diffs) if diffs else 0}
        print(f"Estabilidad ({p['id']}): diferencia media {repeat['mean_abs_diff']:.1f}, máxima {repeat['max_abs_diff']}")

    report = write_report(rows, details, repeat, args, time.monotonic() - started)
    print(f"\nReporte: {report.relative_to(ROOT)}")
    return 0


def write_report(rows, details, repeat, args, elapsed: float) -> Path:
    REPORTS.mkdir(exist_ok=True)
    path = REPORTS / f"eval_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    ndcgs = [r["ndcg"] for r in rows]
    means2 = [r["mean2"] for r in rows if not math.isnan(r["mean2"])]
    lines = [
        f"# Eval del matching — {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"Modelo `{args.model}` · modo `{args.mode}` · idioma `{args.lang}` · pre-ranking {'sí (top ' + str(args.top_n) + ')' if args.pre_rank else 'no'} · {elapsed/60:.1f} min",
        "",
        "## Resumen",
        f"- NDCG@{K} medio: **{_mean(ndcgs):.2f}** (mínimo {min(ndcgs):.2f})",
        f"- Brecha entre profesiones en NDCG@{K}: **{max(ndcgs) - min(ndcgs):.2f}**",
        f"- Score medio de ofertas relevantes: {_mean(means2):.0f} (rango {min(means2):.0f}–{max(means2):.0f} entre profesiones)",
        f"- Profesiones marcadas: {sum(1 for r in rows if r['flags'])} de {len(rows)}",
    ]
    if repeat:
        lines.append(f"- Estabilidad ({repeat['profile']}): diferencia media {repeat['mean_abs_diff']:.1f} puntos, máxima {repeat['max_abs_diff']}")
    lines += [
        "",
        f"Umbrales: NDCG@{K} ≥ {MIN_NDCG} · separación (relevantes − irrelevantes) ≥ {MIN_SEPARATION} · score medio de relevantes ≥ {MIN_RELEVANT_MEAN}",
        "",
        "## Por profesión",
        "",
        f"| Perfil | Profesión | Nivel | NDCG@{K} | P@{K} | Relevantes | Parciales | Irrelevantes | Separación |"
        + (" Recall pre-rank |" if args.pre_rank else "") + " Marcas |",
        "|---|---|---|---|---|---|---|---|---|" + ("---|" if args.pre_rank else "") + "---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['id']} | {r['profession']} | {r['level']} | {r['ndcg']:.2f} | {r['p_at_k']:.2f} | "
            f"{r['mean2']:.0f} | {r['mean1']:.0f} | {r['mean0']:.0f} | {r['separation']:.0f} |"
            + (f" {r['recall_pre']:.2f} |" if args.pre_rank else "")
            + f" {', '.join(r['flags']) or '—'} |"
        )
    lines += ["", f"## Top {K} por perfil", ""]
    for p, top, rel in details:
        lines.append(f"**{p['id']}**: " + " · ".join(f"{s.job.title} ({s.score}, rel {rel[s.job.id]})" for s in top))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


if __name__ == "__main__":
    raise SystemExit(main())
