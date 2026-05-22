"""
ai_engine.py — Motor de IA usando google-genai
Modelo: gemini-1.5-flash (FREE TIER: 15 req/min, 1500 req/día)
"""

from google import genai
from google.genai import errors as genai_errors
import json
import re
import logging
import time
from dataclasses import dataclass
from typing import Optional
import config
from scrapers import JobPosting

log = logging.getLogger(__name__)

MODEL = "gemini-1.5-flash"   # ← free tier disponible (2.0-flash NO tiene free tier)

# Free tier: 15 req/min → esperar 4s entre requests para no pasarse
REQUEST_DELAY = 4.0
MAX_RETRIES = 3


@dataclass
class ScoredJob:
    job: JobPosting
    score: int
    match_reasons: list[str]
    missing_skills: list[str]
    cover_letter: Optional[str]
    summary: str


def _generate(prompt: str) -> tuple[str, bool]:
    """Llama a Gemini con retry automático ante 429.
    Retorna (response_text, quota_exceeded_bool).
    """
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.models.generate_content(model=MODEL, contents=prompt)
            return resp.text.strip(), False
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                if "limit: 0" in err_str:
                    log.error("CUOTA DIARIA AGOTADA — No hay más tokens disponibles hoy")
                    return "", True
                # Extraer retryDelay del mensaje si está disponible
                wait = 60  # default
                match = re.search(r"retryDelay.*?(\d+)s", err_str)
                if match:
                    wait = int(match.group(1)) + 2
                if attempt < MAX_RETRIES - 1:
                    log.warning(f"Rate limit (429). Esperando {wait}s antes de reintentar... (intento {attempt+1}/{MAX_RETRIES})")
                    time.sleep(wait)
                else:
                    log.error(f"Rate limit agotado tras {MAX_RETRIES} intentos.")
                    raise
            else:
                raise
    return "", False


def _parse_json(raw: str) -> dict:
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    log.warning(f"No se pudo parsear JSON. Raw:\n{raw[:200]}")
    return {}


# =============================================================================
# STEP 1 — Scoring
# =============================================================================
def score_job(job: JobPosting) -> dict:
    prompt = f"""Score how well this job offer matches the candidate profile below. Base the evaluation exclusively on the information provided — do not add assumptions, infer seniority, or apply external criteria.

CANDIDATE PROFILE:
{config.CANDIDATE_PROFILE}

JOB OFFER:
Title: {job.title}
Company: {job.company} | Remote: {"Yes" if job.remote else "No"}
Description: {job.description[:1500]}

Return ONLY a raw JSON object, no markdown, no explanation:
{{"score": <integer 0-100>, "match_reasons": ["reason1", "reason2"], "missing_skills": ["skill"], "summary": "one line summary", "apply_recommended": <true or false>}}

Scoring bands (for calibration): 80-100 strong overlap | 60-79 solid match | 40-59 partial match | 0-39 weak match"""

    try:
        raw, quota_exceeded = _generate(prompt)
        if quota_exceeded:
            return {"score": 0, "match_reasons": [], "missing_skills": [], "summary": "", "apply_recommended": False, "quota_exceeded": True}
        if not raw:
            return {"score": 0, "match_reasons": [], "missing_skills": [], "summary": "", "apply_recommended": False, "quota_exceeded": False}
        result = _parse_json(raw)
        if not result or "score" not in result:
            return {"score": 0, "match_reasons": [], "missing_skills": [], "summary": "", "apply_recommended": False, "quota_exceeded": False}
        result["quota_exceeded"] = False
        return result
    except Exception as e:
        log.error(f"Error scoring '{job.title}': {e}")
        return {"score": 0, "match_reasons": [], "missing_skills": [], "summary": "", "apply_recommended": False, "quota_exceeded": False}


# =============================================================================
# STEP 2 — Cover Letter
# =============================================================================
def generate_cover_letter(job: JobPosting, score_data: dict) -> str:
    prompt = f"""Write a professional cover letter for the job posting below.

LANGUAGE RULE: Detect the language of the job posting (title + description) and write the entire letter in that exact language. English job → English letter. Spanish job → Spanish letter. No mixing.

CANDIDATE PROFILE (single source of truth — use only facts explicitly stated here):
{config.CANDIDATE_PROFILE}

JOB POSTING:
Title: {job.title}
Company: {job.company}
Why it matches: {", ".join(score_data.get("match_reasons", []))}
Description: {job.description[:2000]}

STRUCTURE (3–4 paragraphs):
1. Brief introduction: who the candidate is and the role they are applying for.
2. Skills & experience: connect only the candidate's actual skills and experience from the profile to this specific role. Zero invented metrics, zero invented achievements. If the profile says "colaboró en" or "supported", do not write "led" or "built". Mirror the profile's language.
3. Why this company: write a specific paragraph about why the candidate wants to work at {job.company}. Base it on concrete details visible in the job description — product, mission, tech stack, culture, market, or problem they solve. Avoid generic praise like "innovative company" unless supported by specific facts from the description.
4. Call to action: short, direct closing.

First line of output must be: [SUBJECT: suggested email subject in the same language as the letter]
Output only the cover letter, nothing else."""

    try:
        raw, _ = _generate(prompt)
        return raw
    except Exception as e:
        log.error(f"Error cover letter '{job.title}': {e}")
        return "Error generando cover letter."


# =============================================================================
# PIPELINE
# =============================================================================
def process_jobs(jobs: list[JobPosting]) -> list[ScoredJob]:
    scored_jobs: list[ScoredJob] = []
    dist = {"80-100": 0, "60-79": 0, "40-59": 0, "0-39": 0}

    log.info(f"Evaluando {len(jobs)} ofertas con {MODEL} (free tier: 15 req/min)...")
    log.info(f"Tiempo estimado: ~{len(jobs) * REQUEST_DELAY / 60:.1f} minutos")

    for i, job in enumerate(jobs, 1):
        data = score_job(job)
        score = data.get("score", 0)

        if score >= 80:   dist["80-100"] += 1
        elif score >= 60: dist["60-79"] += 1
        elif score >= 40: dist["40-59"] += 1
        else:             dist["0-39"] += 1

        log.info(f"[{i:2d}/{len(jobs)}] {score:3d}/100 — {job.title[:40]:<40} @ {job.company[:20]}")

        scored_jobs.append(ScoredJob(
            job=job,
            score=score,
            match_reasons=data.get("match_reasons", []),
            missing_skills=data.get("missing_skills", []),
            cover_letter=None,
            summary=data.get("summary", ""),
        ))
        time.sleep(REQUEST_DELAY)

    scored_jobs.sort(key=lambda x: x.score, reverse=True)

    log.info("--- Distribución de scores ---")
    for rng, count in dist.items():
        log.info(f"  {rng}: {count} ofertas")

    top = [j for j in scored_jobs if j.score >= config.MIN_MATCH_SCORE]
    log.info(f"→ {len(top)} ofertas superaron umbral de {config.MIN_MATCH_SCORE}")

    if not top:
        log.info("Top 5 scores:")
        for sj in scored_jobs[:5]:
            log.info(f"  {sj.score}/100 — {sj.job.title} @ {sj.job.company}")

    for i, sj in enumerate(top, 1):
        log.info(f"[{i}/{len(top)}] Cover letter: {sj.job.title} (score: {sj.score})")
        sj.cover_letter = generate_cover_letter(sj.job, {"match_reasons": sj.match_reasons})
        time.sleep(REQUEST_DELAY)

    return scored_jobs
