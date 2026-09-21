"""
ai_engine.py — Motor de IA usando google-genai

Toda la configuración sensible (API key, perfil, modelo) se recibe por parámetro:
en Streamlit Cloud el proceso es compartido entre usuarios, así que nada por
sesión puede vivir en variables de módulo.
"""

from google import genai
import json
import re
import logging
import time
from dataclasses import dataclass
from typing import Optional
from scrapers import JobPosting

log = logging.getLogger(__name__)

DEFAULT_MODEL = "models/gemini-3.1-flash-lite"

# Free tier: 15 req/min → esperar 4s entre requests para no pasarse
REQUEST_DELAY = 4.0
MAX_RETRIES = 3

# Idioma en el que la IA escribe motivos, faltantes y resumen (el de la UI).
OUTPUT_LANGUAGES = {"es": "Spanish", "en": "English"}


@dataclass
class ScoredJob:
    job: JobPosting
    score: int
    match_reasons: list[str]
    missing_skills: list[str]
    cover_letter: Optional[str]
    summary: str
    # False si la IA no pudo evaluar la oferta (error, respuesta inválida o cuota).
    # Una oferta no evaluada no es un "match débil": no se rankea ni se recomienda.
    evaluated: bool = True


def _generate(prompt: str, *, api_key: str, model: str) -> tuple[str, bool]:
    """Llama a Gemini con retry automático ante 429.
    Retorna (response_text, quota_exceeded_bool).
    """
    client = genai.Client(api_key=api_key)
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.models.generate_content(model=model, contents=prompt)
            return (resp.text or "").strip(), False
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


def _failed(quota_exceeded: bool = False, auth_error: bool = False) -> dict:
    return {"score": 0, "match_reasons": [], "missing_skills": [], "summary": "",
            "apply_recommended": False, "quota_exceeded": quota_exceeded,
            "auth_error": auth_error, "error": True}


def _is_auth_error(e: Exception) -> bool:
    msg = str(e)
    return any(s in msg for s in ("API_KEY_INVALID", "API key not valid", "PERMISSION_DENIED", "UNAUTHENTICATED"))


# =============================================================================
# STEP 1 — Scoring
# =============================================================================
def score_job(job: JobPosting, profile: str, *, api_key: str, model: str, lang: str = "es") -> dict:
    """Evalúa una oferta contra el perfil.

    Devuelve un dict con `error=True` si la oferta no pudo evaluarse; en ese caso
    `score` no significa nada y no debe mostrarse como puntaje.
    """
    out_lang = OUTPUT_LANGUAGES.get(lang, "Spanish")
    prompt = f"""Score how well this job offer matches the candidate profile below.

STRICT RULES — read before scoring:
- Use ONLY information explicitly stated in the candidate profile. Do not infer, upgrade, or assume anything.
- SENIORITY IS CRITICAL: if the job requires Senior / Lead / Staff / Principal and the profile does NOT explicitly state that level, that is a major mismatch — penalize heavily (≥20 points off). Knowing a technology does NOT imply senior expertise.
- If the profile says the candidate "collaborated on", "supported", "learned", or "assisted with" something, that is junior/mid-level involvement — do not treat it as ownership or deep expertise.
- Score the ACTUAL candidate described, not an idealized version of someone with those technologies.
- A high score (80+) means the job's requirements closely match what the profile explicitly describes — including seniority level, years of experience, and responsibilities.

CANDIDATE PROFILE:
{profile}

JOB OFFER:
Title: {job.title}
Company: {job.company} | Remote: {"Yes" if job.remote else "No"}
Description: {job.description[:1500]}

OUTPUT LANGUAGE: write "match_reasons", "missing_skills" and "summary" in {out_lang}, regardless of the language of the job offer or the profile.

Return ONLY a raw JSON object, no markdown, no explanation:
{{"score": <integer 0-100>, "match_reasons": ["reason1", "reason2"], "missing_skills": ["skill1"], "summary": "one line summary", "apply_recommended": <true or false>}}

Scoring bands: 80-100 strong match (seniority + skills align) | 60-79 solid match (minor gaps) | 40-59 partial match (seniority mismatch or missing key skills) | 0-39 weak match"""

    try:
        raw, quota_exceeded = _generate(prompt, api_key=api_key, model=model)
        if quota_exceeded:
            return _failed(quota_exceeded=True)
        result = _parse_json(raw) if raw else {}
        try:
            score = int(result.get("score"))
        except (TypeError, ValueError):
            log.warning(f"Respuesta sin score válido para '{job.title}'")
            return _failed()
        result["score"] = max(0, min(100, score))
        result["quota_exceeded"] = False
        result["error"] = False
        return result
    except Exception as e:
        log.error(f"Error scoring '{job.title}': {e}")
        return _failed(auth_error=_is_auth_error(e))


# =============================================================================
# STEP 2 — Cover Letter (solo a pedido del usuario)
# =============================================================================
def generate_cover_letter(job: JobPosting, match_reasons: list[str], profile: str, *, api_key: str, model: str) -> str:
    """Genera la carta en el idioma de la oferta. Lanza excepción si falla."""
    prompt = f"""Write a professional cover letter for the job posting below.

LANGUAGE RULE: Detect the language of the job posting (title + description) and write the entire letter in that exact language. English job → English letter. Spanish job → Spanish letter. No mixing.

CANDIDATE PROFILE (single source of truth — use only facts explicitly stated here):
{profile}

JOB POSTING:
Title: {job.title}
Company: {job.company}
Why it matches: {", ".join(match_reasons)}
Description: {job.description[:2000]}

STRUCTURE (3–4 paragraphs):
1. Brief introduction: who the candidate is and the role they are applying for.
2. Skills & experience: connect only the candidate's actual skills and experience from the profile to this specific role. Zero invented metrics, zero invented achievements. If the profile says "colaboró en" or "supported", do not write "led" or "built". Mirror the profile's language.
3. Why this company: write a specific paragraph about why the candidate wants to work at {job.company}. Base it on concrete details visible in the job description — product, mission, tech stack, culture, market, or problem they solve. Avoid generic praise like "innovative company" unless supported by specific facts from the description.
4. Call to action: short, direct closing.

First line of output must be: [SUBJECT: suggested email subject in the same language as the letter]
Output only the cover letter, nothing else."""

    raw, quota_exceeded = _generate(prompt, api_key=api_key, model=model)
    if quota_exceeded:
        raise RuntimeError("quota_exceeded")
    if not raw:
        raise RuntimeError("empty_response")
    return raw


# =============================================================================
# PIPELINE (CLI)
# =============================================================================
def process_jobs(jobs: list[JobPosting], profile: str, *, api_key: str, model: str = DEFAULT_MODEL,
                 min_score: int = 65, lang: str = "es", with_letters: bool = False) -> list[ScoredJob]:
    scored_jobs: list[ScoredJob] = []
    dist = {"80-100": 0, "60-79": 0, "40-59": 0, "0-39": 0, "no evaluadas": 0}

    log.info(f"Evaluando {len(jobs)} ofertas con {model}...")
    log.info(f"Tiempo estimado: ~{len(jobs) * REQUEST_DELAY / 60:.1f} minutos")

    for i, job in enumerate(jobs, 1):
        data = score_job(job, profile, api_key=api_key, model=model, lang=lang)
        evaluated = not data.get("error", False)
        score = data.get("score", 0)

        if not evaluated:  dist["no evaluadas"] += 1
        elif score >= 80:  dist["80-100"] += 1
        elif score >= 60:  dist["60-79"] += 1
        elif score >= 40:  dist["40-59"] += 1
        else:              dist["0-39"] += 1

        shown = f"{score:3d}/100" if evaluated else "  —/100"
        log.info(f"[{i:2d}/{len(jobs)}] {shown} — {job.title[:40]:<40} @ {job.company[:20]}")

        scored_jobs.append(ScoredJob(
            job=job,
            score=score,
            match_reasons=data.get("match_reasons", []),
            missing_skills=data.get("missing_skills", []),
            cover_letter=None,
            summary=data.get("summary", ""),
            evaluated=evaluated,
        ))
        if data.get("quota_exceeded") or data.get("auth_error"):
            log.error("Cuota agotada o API key inválida: se detiene la evaluación.")
            break
        time.sleep(REQUEST_DELAY)

    scored_jobs.sort(key=rank_key)

    log.info("--- Distribución de scores ---")
    for rng, count in dist.items():
        log.info(f"  {rng}: {count} ofertas")

    top = recommended(scored_jobs, min_score)
    log.info(f"→ {len(top)} ofertas superaron umbral de {min_score}")

    if with_letters:
        for i, sj in enumerate(top, 1):
            log.info(f"[{i}/{len(top)}] Cover letter: {sj.job.title} (score: {sj.score})")
            try:
                sj.cover_letter = generate_cover_letter(sj.job, sj.match_reasons, profile, api_key=api_key, model=model)
            except Exception as e:
                log.error(f"Error cover letter '{sj.job.title}': {e}")
            time.sleep(REQUEST_DELAY)

    return scored_jobs


def rank_key(sj: ScoredJob):
    """Evaluadas primero (por score desc), no evaluadas al final."""
    return (not sj.evaluated, -sj.score if sj.evaluated else 0)


def recommended(scored_jobs: list[ScoredJob], min_score: int) -> list[ScoredJob]:
    return [sj for sj in scored_jobs if sj.evaluated and sj.score >= min_score]
