"""
normalize.py — Normalización de ofertas sin IA.

Detecta idioma, seniority y modalidad con reglas explícitas y deduplica ofertas
publicadas en más de un portal. Cuando un dato no se puede determinar con
confianza queda en "unknown": nunca se adivina.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from scrapers import JobPosting

UNKNOWN = "unknown"
SENIORITY_ORDER = ["intern", "junior", "mid", "senior", "lead"]


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", strip_accents((text or "").lower())).strip()


# ─── Idioma ──────────────────────────────────────────────────────────────────
# Palabras frecuentes que no se comparten entre idiomas (sin tildes: "años" → "anos").
_STOPWORDS = {
    "es": {"el", "los", "las", "del", "y", "con", "una", "por", "como", "buscamos", "anos", "hasta", "mas", "sin",
           "modalidad", "manejo", "conocimientos", "recibido", "experiencia", "nuestro", "nuestra", "deseable"},
    "en": {"the", "and", "with", "for", "you", "our", "will", "are", "your", "of", "to", "years", "experience",
           "team", "we", "required", "plus", "is", "building"},
    "pt": {"voce", "uma", "nao", "sao", "trabalho", "vaga", "nossa", "nosso", "obrigatorio", "atendimento", "e", "fluente", "ano"},
    "de": {"und", "der", "die", "das", "mit", "fur", "wir", "sie", "ihre", "erfahrung", "unternehmen", "suchen"},
    "fr": {"les", "des", "pour", "avec", "vous", "nous", "est", "entreprise", "poste", "et", "annees"},
}
_MIN_HITS = 2


def detect_language(text: str) -> str:
    tokens = re.findall(r"[a-z]+", _norm(text)[:4000])
    if not tokens:
        return UNKNOWN
    counts = {lang: sum(1 for t in tokens if t in words) for lang, words in _STOPWORDS.items()}
    best = max(counts, key=counts.get)
    ordered = sorted(counts.values(), reverse=True)
    # Exigimos mínimo de coincidencias y un margen claro sobre el segundo idioma.
    if ordered[0] < _MIN_HITS or ordered[0] < ordered[1] * 1.5:
        return UNKNOWN
    return best


# ─── Seniority ───────────────────────────────────────────────────────────────
# Orden importa: "semi senior" antes que "senior", "lead" antes que "senior".
# Se excluyen a propósito palabras que en muchas profesiones son parte del ROL y no
# del nivel: "manager" (Account/Community Manager), "staff" (Staff Nurse),
# "principal", "mid" suelto (Mid-Market). Ante la duda, "unknown".
_SENIORITY_TITLE = [
    ("intern", r"\b(intern|internship|pasante|pasantia|becario|becaria|trainee|practicante|estagio|estagiario)\b"),
    ("mid", r"\b(semi[\s-]?senior|ssr|mid[\s-]level|mid level|intermediate|pleno)\b"),
    ("lead", r"\b(team lead|tech lead|lead(?!\s+gen)|leader|lider|head of|director|directora|jefe|jefa)\b"),
    ("senior", r"\b(senior|sr)\b"),
    ("junior", r"\b(junior|jr|entry[\s-]?level|graduate|sin experiencia)\b"),
]
# En la descripción solo cuentan declaraciones explícitas del nivel buscado.
_SENIORITY_DESC = r"\b(?:seniority|nivel|level)\s*[:\-]\s*(semi[\s-]?senior|senior|junior|mid|trainee|lead)\b"


def detect_seniority(title: str, description: str = "") -> str:
    t = _norm(title)
    for level, pattern in _SENIORITY_TITLE:
        if re.search(pattern, t):
            return level
    m = re.search(_SENIORITY_DESC, _norm(description))
    if m:
        found = m.group(1)
        if found.startswith("semi"):
            return "mid"
        return {"trainee": "intern"}.get(found, found)
    return UNKNOWN


# ─── Modalidad ───────────────────────────────────────────────────────────────
_HYBRID = r"\b(hybrid|hibrido|hibrida|semipresencial)\b"
_REMOTE = r"\b(remote|remoto|remota|teletrabajo|home office|work from home|anywhere)\b"
_ONSITE = r"\b(on[\s-]?site|in[\s-]?office|presencial|en oficina)\b"
# En la descripción "remote" aparece en beneficios o menciones sueltas: se exige una frase explícita.
_REMOTE_DESC = r"\b(100% remot[eoa]|fully remote|remote[\s-]first|trabajo remoto|full remote)\b"


def detect_modality(job: JobPosting) -> str:
    head = _norm(f"{job.title} {job.location}")
    if re.search(_HYBRID, head):
        return "hybrid"
    if job.remote or re.search(_REMOTE, head):
        return "remote"
    if re.search(_ONSITE, head):
        return "onsite"
    desc = _norm(job.description)
    if re.search(_HYBRID, desc):
        return "hybrid"
    if re.search(_REMOTE_DESC, desc):
        return "remote"
    if re.search(_ONSITE, desc):
        return "onsite"
    return UNKNOWN


def enrich(job: JobPosting) -> JobPosting:
    job.language = detect_language(f"{job.title} {job.description}")
    job.seniority = detect_seniority(job.title, job.description)
    job.modality = detect_modality(job)
    return job


# ─── Deduplicación ───────────────────────────────────────────────────────────
_LEGAL_SUFFIX = r"\b(inc|llc|ltd|limited|gmbh|s\.?a\.?|s\.?r\.?l\.?|s\.?a\.?s\.?|corp|corporation|co|plc|bv|ag)\b\.?"
_TITLE_NOISE = r"\((?:m/w/d|w/m/d|m/f/d|f/m/d|h/f|remote|remoto|hybrid)\)"
TITLE_SIMILARITY = 0.9


def _company_key(company: str) -> str:
    c = re.sub(_LEGAL_SUFFIX, " ", _norm(company))
    return re.sub(r"[^a-z0-9]+", " ", c).strip()


def _title_key(title: str) -> str:
    t = re.sub(_TITLE_NOISE, " ", _norm(title))
    return re.sub(r"[^a-z0-9+#]+", " ", t).strip()


def dedupe(jobs: list[JobPosting]) -> list[JobPosting]:
    """Elimina la misma oferta publicada en varios portales (misma empresa, título casi igual).

    Se conserva la versión con la descripción más completa, en la posición de la primera.
    """
    kept: list[JobPosting] = []
    by_company: dict[str, list[int]] = {}
    for job in jobs:
        ckey = _company_key(job.company)
        tkey = _title_key(job.title)
        dup_idx = None
        if ckey:
            for idx in by_company.get(ckey, []):
                if SequenceMatcher(None, tkey, _title_key(kept[idx].title)).ratio() >= TITLE_SIMILARITY:
                    dup_idx = idx
                    break
        if dup_idx is None:
            by_company.setdefault(ckey, []).append(len(kept))
            kept.append(job)
        elif len(job.description) > len(kept[dup_idx].description):
            kept[dup_idx] = job
    return kept
