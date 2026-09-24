"""
scrapers.py — Fuentes de trabajo con APIs públicas (sin auth requerida)
- Remotive:       API REST pública, enfocada en remoto
- Arbeitnow:      API REST pública, filtro remoto
- We Work Remotely: RSS feeds por categoría
- Himalayas:      API REST pública, 100% remoto
- RemoteOK:       API JSON pública, filtro por tag client-side
- Working Nomads: API REST pública, categorías dev
- The Muse:       API REST paginada, EEUU + global
- Jobspresso:     RSS feed, remoto global
- JustJoin.it:    API REST pública, Europa/global
- Authentic Jobs: RSS feed, EEUU + global
"""

import functools
import requests
import feedparser
import time
import logging
import html
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {"User-Agent": "JobHunterBot/1.0 (personal job search automation)"}


def _strip_html(raw_html: str) -> str:
    """Remove tags and compact whitespace for AI-friendly descriptions."""
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


DESCRIPTION_LIMIT = 3000


def _clean_desc(raw: str) -> str:
    """Limpia HTML ANTES de truncar: si no, el límite se gasta en tags y se pierden requisitos."""
    return _strip_html(raw or "")[:DESCRIPTION_LIMIT]


@functools.lru_cache(maxsize=512)
def _keyword_pattern(keyword: str) -> re.Pattern:
    # Palabra completa: "java" no matchea "javascript", "go" no matchea "google".
    # Lookarounds en vez de \b para soportar keywords como "c++", "c#" o "node.js".
    return re.compile(r"(?<!\w)" + re.escape(keyword.strip().lower()) + r"(?!\w)")


def matches_keywords(keywords: list[str], *parts: str) -> bool:
    """Filtro client-side para fuentes sin búsqueda del lado del servidor."""
    keywords = [k for k in keywords if k and k.strip()]
    if not keywords:
        return True
    haystack = " ".join(p for p in parts if p).lower()
    return any(_keyword_pattern(kw).search(haystack) for kw in keywords)


def _extract_json_ld_objects(page_html: str) -> list[dict]:
    """Parse JSON-LD blocks and flatten arrays into a list of dicts."""
    objects: list[dict] = []
    for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page_html, re.S):
        try:
            parsed = json.loads(html.unescape(raw))
        except Exception:
            continue
        if isinstance(parsed, list):
            objects.extend(item for item in parsed if isinstance(item, dict))
        elif isinstance(parsed, dict):
            objects.append(parsed)
    return objects


def _salary_from_json_ld(job: dict) -> Optional[str]:
    base = job.get("baseSalary")
    if not isinstance(base, dict):
        return None
    currency = base.get("currency", "")
    value = base.get("value", {}) if isinstance(base.get("value"), dict) else {}
    low = value.get("minValue")
    high = value.get("maxValue")
    unit = value.get("unitText", "")
    if low and high:
        return f"{low}-{high} {currency}/{unit}".strip()
    if low:
        return f"{low} {currency}/{unit}".strip()
    return None


def _parse_feed(url: str, timeout: int = 15):
    """Fetch RSS/Atom feed con timeout usando requests, luego parsear con feedparser."""
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return feedparser.parse(resp.content)


@dataclass
class JobPosting:
    id: str
    title: str
    company: str
    description: str
    location: str
    remote: bool
    url: str
    source: str
    published_at: Optional[str] = None
    salary: Optional[str] = None
    tags: list = field(default_factory=list)
    # Completados por normalize.enrich() — "unknown" cuando no se puede determinar.
    language: str = "unknown"    # código ISO: es, en, pt, de, fr
    seniority: str = "unknown"   # intern | junior | mid | senior | lead
    modality: str = "unknown"    # remote | hybrid | onsite


# =============================================================================
# Remotive — https://remotive.com/api/remote-jobs
# =============================================================================
def scrape_remotive(keywords: list[str], max_results: int = 0) -> list[JobPosting]:
    jobs = []
    seen = set()

    for keyword in keywords:
        if max_results > 0 and len(jobs) >= max_results:
            break
        try:
            resp = requests.get(
                "https://remotive.com/api/remote-jobs",
                params={"search": keyword, "limit": 20},
                headers=HEADERS, timeout=15
            )
            resp.raise_for_status()
            data = resp.json().get("jobs", [])
            log.info(f"[Remotive] '{keyword}' → {len(data)} ofertas")

            for item in data:
                if max_results > 0 and len(jobs) >= max_results:
                    break
                jid = f"rem-{item.get('id', '')}"
                if jid in seen:
                    continue
                # La búsqueda de Remotive es difusa (devuelve ofertas que no mencionan el término).
                if not matches_keywords([keyword], item.get("title", ""), _strip_html(item.get("description", "")),
                                        " ".join(item.get("tags", []))):
                    continue
                seen.add(jid)

                jobs.append(JobPosting(
                    id=jid,
                    title=item.get("title", ""),
                    company=item.get("company_name", ""),
                    description=_clean_desc(item.get("description", "")),
                    location=item.get("candidate_required_location", "Worldwide"),
                    remote=True,
                    url=item.get("url", ""),
                    source="Remotive",
                    published_at=item.get("publication_date", ""),
                    salary=item.get("salary", None),
                    tags=item.get("tags", []),
                ))
            time.sleep(1)
        except Exception as e:
            log.error(f"[Remotive] Error '{keyword}': {e}")

    return jobs


# =============================================================================
# Arbeitnow — https://www.arbeitnow.com/api/job-board-api
# =============================================================================
def scrape_arbeitnow(keywords: list[str], max_results: int = 0) -> list[JobPosting]:
    jobs = []
    seen = set()
    MAX_PAGES = 3  # más páginas provocan 403 por rate-limit

    for keyword in keywords:
        if max_results > 0 and len(jobs) >= max_results:
            break
        page = 1
        while page <= MAX_PAGES:
            if max_results > 0 and len(jobs) >= max_results:
                break
            try:
                resp = requests.get(
                    "https://www.arbeitnow.com/api/job-board-api",
                    params={
                        "search": keyword,
                        "page": page,
                    },
                    headers=HEADERS, timeout=15
                )
                if resp.status_code == 403:
                    log.warning(f"[Arbeitnow] 403 rate-limit, deteniendo scraping")
                    return jobs
                resp.raise_for_status()
                data = resp.json().get("data", [])
                if not data:
                    break
                log.info(f"[Arbeitnow] '{keyword}' (página {page}) → {len(data)} ofertas")

                for item in data:
                    if max_results > 0 and len(jobs) >= max_results:
                        break
                    is_remote = item.get("remote", False)

                    jid = f"arb-{item.get('slug', item.get('title', ''))[:40]}"
                    if jid in seen:
                        continue
                    seen.add(jid)

                    jobs.append(JobPosting(
                        id=jid,
                        title=item.get("title", ""),
                        company=item.get("company_name", ""),
                        description=_clean_desc(item.get("description", "")),
                        location=item.get("location", "Remote"),
                        remote=is_remote,
                        url=item.get("url", ""),
                        source="Arbeitnow",
                        published_at=str(item.get("created_at", "")),
                        tags=item.get("tags", []),
                    ))
                page += 1
                time.sleep(1)
            except Exception as e:
                log.error(f"[Arbeitnow] Error '{keyword}' página {page}: {e}")
                break

    return jobs


# =============================================================================
# We Work Remotely — RSS general (todos los empleos remotos)
# =============================================================================
def scrape_weworkremotely(keywords: list[str], max_results: int = 0) -> list[JobPosting]:
    jobs = []
    seen = set()

    try:
        feed = _parse_feed("https://weworkremotely.com/remote-jobs.rss")
        entries = feed.get("entries", [])
        log.info(f"[WeWorkRemotely] {len(entries)} ofertas totales, filtrando por keywords")

        for entry in entries:
            if max_results > 0 and len(jobs) >= max_results:
                break
            title_raw = entry.get("title", "")
            summary   = entry.get("summary", "")
            text      = f"{title_raw} {summary}".lower()
            if not matches_keywords(keywords, text):
                continue

            jid = f"wwr-{entry.get('id', entry.get('link',''))[:50]}"
            if jid in seen:
                continue
            seen.add(jid)

            company, title = "", title_raw
            if ": " in title_raw:
                parts = title_raw.split(": ", 1)
                company, title = parts[0].strip(), parts[1].strip()

            jobs.append(JobPosting(
                id=jid,
                title=title,
                company=company,
                description=_clean_desc(summary),
                location="Remote",
                remote=True,
                url=entry.get("link", ""),
                source="WeWorkRemotely",
                published_at=entry.get("published", ""),
            ))
    except Exception as e:
        log.error(f"[WeWorkRemotely] Error: {e}")

    log.info(f"[WeWorkRemotely] {len(jobs)} ofertas tras filtro")

    return jobs


# =============================================================================
# Himalayas — https://himalayas.app/jobs/api
# =============================================================================
def scrape_himalayas(keywords: list[str], max_results: int = 0) -> list[JobPosting]:
    jobs = []
    seen = set()

    for keyword in keywords:
        if max_results > 0 and len(jobs) >= max_results:
            break
        try:
            resp = requests.get(
                "https://himalayas.app/jobs/api",
                params={"q": keyword, "limit": 15},
                headers=HEADERS, timeout=15
            )
            resp.raise_for_status()
            data = resp.json().get("jobs", [])
            log.info(f"[Himalayas] '{keyword}' → {len(data)} ofertas")

            for item in data:
                if max_results > 0 and len(jobs) >= max_results:
                    break
                jid = f"him-{item.get('slug', item.get('title', ''))[:40]}"
                if jid in seen:
                    continue
                seen.add(jid)

                jobs.append(JobPosting(
                    id=jid,
                    title=item.get("title", ""),
                    company=item.get("companyName", ""),
                    description=_clean_desc((item.get("description", "") or "")),
                    location="Remote",
                    remote=True,
                    url=f"https://himalayas.app/jobs/{item.get('slug', '')}",
                    source="Himalayas",
                    published_at=item.get("publishedAt", ""),
                    salary=item.get("salaryCurrency", ""),
                    tags=item.get("skills", []),
                ))
            time.sleep(1)
        except Exception as e:
            log.error(f"[Himalayas] Error '{keyword}': {e}")

    return jobs


# =============================================================================
# RemoteOK — https://remoteok.com/api
# Devuelve el array completo; filtramos por keywords client-side.
# =============================================================================
def scrape_remoteok(keywords: list[str], max_results: int = 0) -> list[JobPosting]:
    jobs = []
    seen = set()

    try:
        resp = requests.get(
            "https://remoteok.com/api",
            headers={**HEADERS, "Accept": "application/json"},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        # El primer elemento es metadata, el resto son ofertas
        items = [d for d in data if isinstance(d, dict) and d.get("position")]
        log.info(f"[RemoteOK] {len(items)} ofertas totales, filtrando por keywords")

        for item in items:
            if max_results > 0 and len(jobs) >= max_results:
                break
            text = " ".join([
                item.get("position", ""),
                item.get("company", ""),
                " ".join(item.get("tags", [])),
                item.get("description", ""),
            ]).lower()
            if not matches_keywords(keywords, text):
                continue

            jid = f"rok-{item.get('id', item.get('slug', ''))}"
            if jid in seen:
                continue
            seen.add(jid)

            jobs.append(JobPosting(
                id=jid,
                title=item.get("position", ""),
                company=item.get("company", ""),
                description=_clean_desc((item.get("description", "") or "")),
                location=item.get("location", "Remote"),
                remote=True,
                url=item.get("url", f"https://remoteok.com/remote-jobs/{item.get('slug', '')}"),
                source="RemoteOK",
                published_at=item.get("date", ""),
                salary=item.get("salary", None),
                tags=item.get("tags", []),
            ))
    except Exception as e:
        log.error(f"[RemoteOK] Error: {e}")

    log.info(f"[RemoteOK] {len(jobs)} ofertas tras filtro")
    return jobs


# =============================================================================
# NOTA: A partir de 2026 requiere autenticación (401). La API pública fue
# discontinuada. La función se mantiene por si el endpoint vuelve a ser libre,
# pero devuelve [] y loguea un warning en lugar de reintentar 12 veces.
# =============================================================================


def scrape_getonboard(keywords: list[str], max_results: int = 0) -> list[JobPosting]:
    """API pública de Get on Board: una petición por término.

    Antes se recorrían las categorías y se abría cada aviso: cientos de requests y varios minutos.
    """
    jobs: list[JobPosting] = []
    seen: set[str] = set()

    for keyword in keywords:
        if max_results > 0 and len(jobs) >= max_results:
            break
        try:
            resp = requests.get(
                "https://www.getonbrd.com/api/v0/search/jobs",
                params={"query": keyword, "per_page": 50, "expand": '["company"]'},
                headers=HEADERS, timeout=20,
            )
            resp.raise_for_status()
            data = resp.json().get("data", [])
        except Exception as e:
            log.error(f"[GetOnBoard] Error '{keyword}': {e}")
            continue

        log.info(f"[GetOnBoard] '{keyword}' -> {len(data)} ofertas")
        for item in data:
            if max_results > 0 and len(jobs) >= max_results:
                break
            jid = f"gob-{item.get('id', '')}"[:90]
            if not item.get("id") or jid in seen:
                continue
            attrs = item.get("attributes", {}) or {}
            company = ((attrs.get("company") or {}).get("data") or {}).get("attributes", {}).get("name", "")
            countries = [c for c in (attrs.get("countries") or []) if c]
            # location_cities viene como {"data": [...]} y suele estar vacío: la ubicación útil es countries.
            cities = [(c.get("attributes") or {}).get("name", "") for c in
                      ((attrs.get("location_cities") or {}).get("data") or [])]
            location = ", ".join([c for c in cities if c] or countries) or "Not specified"
            description = " ".join(_strip_html(attrs.get(field) or "") for field in
                                   ("description", "functions", "desirable")).strip()
            published = attrs.get("published_at")

            seen.add(jid)
            jobs.append(JobPosting(
                id=jid,
                title=attrs.get("title", ""),
                company=company,
                description=_clean_desc(description),
                location=location,
                remote=bool(attrs.get("remote")),
                url=f"https://www.getonbrd.com/jobs/{item['id']}",
                source="GetOnBoard",
                published_at=datetime.fromtimestamp(published).isoformat() if isinstance(published, (int, float)) else None,
                salary=_gob_salary(attrs),
                tags=[],
            ))

    return jobs


def _gob_salary(attrs: dict) -> Optional[str]:
    low, high = attrs.get("min_salary"), attrs.get("max_salary")
    if low and high:
        return f"USD {low:,.0f} - {high:,.0f}"
    return f"USD {low or high:,.0f}" if (low or high) else None


# =============================================================================
# Puente Talent — JSON-LD estructurado, foco LATAM remoto
# =============================================================================
def scrape_puente(keywords: list[str], max_results: int = 0) -> list[JobPosting]:
    jobs = []
    seen = set()

    try:
        resp = requests.get("https://puentetalent.com/jobs", headers=HEADERS, timeout=20)
        resp.raise_for_status()
        objects = _extract_json_ld_objects(resp.text)
        # mainEntity puede ser un dict con itemListElement, o directamente una lista
        items = []
        for obj in objects:
            if obj.get("@type") != "CollectionPage":
                continue
            main = obj.get("mainEntity", {})
            if isinstance(main, list):
                items = main
            elif isinstance(main, dict):
                items = main.get("itemListElement", [])
            if items:
                break
        if not items:
            # Fallback: buscar ItemList directamente
            for obj in objects:
                if obj.get("@type") in ("ItemList", "JobPosting"):
                    items = obj.get("itemListElement", [obj])
                    break
        if not items:
            return jobs
        log.info(f"[PuenteTalent] {len(items)} vacantes estructuradas")

        for entry in items:
            if max_results > 0 and len(jobs) >= max_results:
                break
            job = entry.get("item", {}) if isinstance(entry, dict) else {}
            if not isinstance(job, dict):
                continue

            title = job.get("title", "")
            description = _strip_html(job.get("description", ""))
            company = job.get("hiringOrganization", {}).get("name", "Puente Talent Partners")
            location = job.get("applicantLocationRequirements", {}).get("name", "LATAM")
            salary = _salary_from_json_ld(job)
            url = job.get("url", entry.get("url", ""))
            jid = f"pnt-{job.get('identifier', {}).get('value', title)[:40]}"

            if jid in seen or not matches_keywords(keywords, title, description, location):
                continue

            remote = job.get("jobLocationType") == "TELECOMMUTE" or "remote" in description.lower()

            seen.add(jid)
            jobs.append(JobPosting(
                id=jid,
                title=title,
                company=company,
                description=_clean_desc(description),
                location=location,
                remote=remote,
                url=url,
                source="PuenteTalent",
                published_at=job.get("datePosted"),
                salary=salary,
                tags=[],
            ))
    except Exception as e:
        log.error(f"[PuenteTalent] Error: {e}")

    return jobs


# =============================================================================
# LatoJobs — SSR + detalle JSON-LD
# =============================================================================
def scrape_latojobs(keywords: list[str], max_results: int = 0) -> list[JobPosting]:
    jobs = []
    seen = set()
    pages_to_fetch = 3

    for page in range(1, pages_to_fetch + 1):
        if max_results > 0 and len(jobs) >= max_results:
            break
        try:
            resp = requests.get(
                "https://www.latojobs.com/jobs",
                params={"page": page},
                headers=HEADERS,
                timeout=20,
            )
            resp.raise_for_status()
            detail_urls = []
            for path in re.findall(r'href="(/jobs/[0-9a-f\-]{36})"', resp.text):
                url = f"https://www.latojobs.com{path}"
                if url not in detail_urls:
                    detail_urls.append(url)
            log.info(f"[LatoJobs] página {page} → {len(detail_urls)} links")

            for url in detail_urls:
                if max_results > 0 and len(jobs) >= max_results:
                    break
                jid = f"lat-{url.rsplit('/', 1)[-1]}"
                if jid in seen:
                    continue

                detail = requests.get(url, headers=HEADERS, timeout=20)
                detail.raise_for_status()
                objects = _extract_json_ld_objects(detail.text)
                job = next((obj for obj in objects if obj.get("@type") == "JobPosting"), None)
                if not job:
                    continue

                title = job.get("title", "")
                company = job.get("hiringOrganization", {}).get("name", "")
                description = _strip_html(job.get("description", ""))
                location = ""
                job_location = job.get("jobLocation")
                if isinstance(job_location, dict):
                    address = job_location.get("address", {})
                    if isinstance(address, dict):
                        location = ", ".join(
                            part for part in [
                                address.get("addressLocality", ""),
                                address.get("addressCountry", ""),
                            ] if part
                        )
                if not location:
                    location = "Remote" if job.get("jobLocationType") == "TELECOMMUTE" else "Not specified"

                if not matches_keywords(keywords, title, company, description, location):
                    continue

                remote = (
                    job.get("jobLocationType") == "TELECOMMUTE"
                    or "remote" in location.lower()
                    or "remote" in description.lower()
                )

                seen.add(jid)
                jobs.append(JobPosting(
                    id=jid,
                    title=title,
                    company=company,
                    description=_clean_desc(description),
                    location=location,
                    remote=remote,
                    url=url,
                    source="LatoJobs",
                    published_at=job.get("datePosted"),
                    salary=_salary_from_json_ld(job),
                    tags=[],
                ))
                time.sleep(0.3)
            time.sleep(0.6)
        except Exception as e:
            log.error(f"[LatoJobs] Error página {page}: {e}")
            break

    return jobs


# =============================================================================
# Working Nomads — https://www.workingnomads.com/api/exposed_jobs/
# Fetches todos los empleos sin categoría; filtra client-side por keywords.
# =============================================================================
def scrape_workingnomads(keywords: list[str], max_results: int = 0) -> list[JobPosting]:
    jobs = []
    seen = set()

    try:
        resp = requests.get(
            "https://www.workingnomads.com/api/exposed_jobs/",
            headers=HEADERS, timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        log.info(f"[WorkingNomads] {len(data)} ofertas totales, filtrando por keywords")

        for item in data:
            if max_results > 0 and len(jobs) >= max_results:
                break
            text = f"{item.get('title', '')} {item.get('description', '')} {item.get('tags', '')}".lower()
            if not matches_keywords(keywords, text):
                continue

            jid = f"wn-{item.get('id', item.get('slug', ''))}"
            if jid in seen:
                continue
            seen.add(jid)

            jobs.append(JobPosting(
                id=jid,
                title=item.get("title", ""),
                company=item.get("company_name", ""),
                description=_clean_desc((item.get("description", "") or "")),
                location=item.get("location", "Remote"),
                remote=True,
                url=item.get("url", ""),
                source="WorkingNomads",
                published_at=item.get("pub_date", ""),
            ))
        log.info(f"[WorkingNomads] {len(jobs)} ofertas tras filtro")
    except Exception as e:
        log.error(f"[WorkingNomads] Error: {e}")

    return jobs




# =============================================================================
# The Muse — https://www.themuse.com/api/public/jobs
# API paginada, ~20 resultados por página. Filtra client-side por keywords.
# =============================================================================
def scrape_themuse(keywords: list[str], max_results: int = 0) -> list[JobPosting]:
    jobs = []
    seen = set()
    pages_to_fetch = 5

    for page in range(1, pages_to_fetch + 1):
        if max_results > 0 and len(jobs) >= max_results:
            break
        try:
            resp = requests.get(
                "https://www.themuse.com/api/public/jobs",
                params={"page": page, "descending": "true"},
                headers=HEADERS, timeout=15,
            )
            resp.raise_for_status()
            data = resp.json().get("results", [])
            if not data:
                break
            log.info(f"[TheMuse] página {page} → {len(data)} ofertas")

            for item in data:
                if max_results > 0 and len(jobs) >= max_results:
                    break
                name = item.get("name", "")
                contents = item.get("contents", "")
                company = item.get("company", {}).get("name", "")
                text = f"{name} {contents} {company}".lower()
                if not matches_keywords(keywords, text):
                    continue

                jid = f"muse-{item.get('id', '')}"
                if jid in seen:
                    continue
                seen.add(jid)

                locs = item.get("locations", [])
                location = locs[0].get("name", "Remote") if locs else "Remote"
                is_remote = any("remote" in (loc.get("name", "")).lower() for loc in locs) or not locs

                jobs.append(JobPosting(
                    id=jid,
                    title=name,
                    company=company,
                    description=_clean_desc(contents),
                    location=location,
                    remote=is_remote,
                    url=item.get("refs", {}).get("landing_page", ""),
                    source="TheMuse",
                    published_at=item.get("publication_date", ""),
                    tags=[l.get("name", "") for l in item.get("levels", [])],
                ))
            time.sleep(1)
        except Exception as e:
            log.error(f"[TheMuse] Error página {page}: {e}")
            break

    return jobs


# =============================================================================
# Jobspresso — RSS feed
# =============================================================================
def scrape_jobspresso(max_results: int = 0) -> list[JobPosting]:
    jobs = []
    seen = set()

    try:
        feed = _parse_feed("https://jobspresso.co/feed/")
        entries = feed.get("entries", [])
        log.info(f"[Jobspresso] {len(entries)} ofertas")

        for entry in entries:
            if max_results > 0 and len(jobs) >= max_results:
                break
            jid = f"jsp-{entry.get('id', entry.get('link', ''))[:60]}"
            if jid in seen:
                continue
            seen.add(jid)

            jobs.append(JobPosting(
                id=jid,
                title=entry.get("title", ""),
                company=entry.get("author", ""),
                description=_clean_desc(entry.get("summary", "")),
                location="Remote",
                remote=True,
                url=entry.get("link", ""),
                source="Jobspresso",
                published_at=entry.get("published", ""),
            ))
    except Exception as e:
        log.error(f"[Jobspresso] Error: {e}")

    return jobs


# =============================================================================
# JustJoin.it — https://api.justjoin.it/jobs
# Lista completa, filtro client-side por keywords. Foco Europa/global.
# =============================================================================
def scrape_justjoinit(keywords: list[str], max_results: int = 0) -> list[JobPosting]:
    jobs = []
    seen = set()

    try:
        resp = requests.get(
            "https://api.justjoin.it/jobs",
            headers=HEADERS, timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        log.info(f"[JustJoin.it] {len(data)} ofertas totales, filtrando por keywords")

        for item in data:
            if max_results > 0 and len(jobs) >= max_results:
                break
            skills = " ".join(s.get("name", "") for s in item.get("skills", []))
            text = f"{item.get('title', '')} {item.get('marker_icon', '')} {skills}".lower()
            if not matches_keywords(keywords, text):
                continue

            jid = f"jji-{item.get('id', '')}"
            if jid in seen:
                continue
            seen.add(jid)

            is_remote = item.get("workplace_type", "") in ("remote", "hybrid")
            jobs.append(JobPosting(
                id=jid,
                title=item.get("title", ""),
                company=item.get("company_name", ""),
                description=_clean_desc(f"{item.get('body', '') or ''}".strip()),
                location=item.get("city", "Remote") or "Remote",
                remote=is_remote,
                url=f"https://justjoin.it/offers/{item.get('id', '')}",
                source="JustJoin.it",
                published_at=item.get("published_at", ""),
                salary=(
                    f"{item['salary_from']}-{item['salary_to']} {item.get('currency', '')}"
                    if item.get("salary_from") else None
                ),
                tags=[s.get("name", "") for s in item.get("skills", [])],
            ))
    except Exception as e:
        log.error(f"[JustJoin.it] Error: {e}")

    log.info(f"[JustJoin.it] {len(jobs)} ofertas tras filtro")
    return jobs


# =============================================================================
# Authentic Jobs — RSS feed
# =============================================================================
def scrape_authenticjobs(max_results: int = 0) -> list[JobPosting]:
    jobs = []
    seen = set()

    try:
        feed = _parse_feed("https://authenticjobs.com/feed/")
        entries = feed.get("entries", [])
        log.info(f"[AuthenticJobs] {len(entries)} ofertas")

        for entry in entries:
            if max_results > 0 and len(jobs) >= max_results:
                break
            jid = f"aj-{entry.get('id', entry.get('link', ''))[:60]}"
            if jid in seen:
                continue
            seen.add(jid)

            jobs.append(JobPosting(
                id=jid,
                title=entry.get("title", ""),
                company=entry.get("author", ""),
                description=_clean_desc(entry.get("summary", "")),
                location="Remote",
                remote=True,
                url=entry.get("link", ""),
                source="AuthenticJobs",
                published_at=entry.get("published", ""),
            ))
    except Exception as e:
        log.error(f"[AuthenticJobs] Error: {e}")

    return jobs


# =============================================================================
# Función principal
# =============================================================================
def get_all_jobs(keywords: list[str], portal_keys: list[str] | None = None, max_per_portal: int = 0) -> list[JobPosting]:
    """Lee los portales pedidos (por defecto, todos) y devuelve las ofertas sin duplicados.

    La usa el CLI. La app web tiene su propia corrida (web/run.py), que lee los portales en paralelo
    y reporta el progreso; las dos parten del mismo registro PORTAL_SCRAPERS.
    """
    keys = [k for k in (portal_keys or PORTAL_SCRAPERS) if k in PORTAL_SCRAPERS]
    jobs: list[JobPosting] = []
    seen: set[str] = set()

    for key in keys:
        log.info(f"--- {key} ---")
        try:
            found = PORTAL_SCRAPERS[key](keywords, max_per_portal)
        except Exception as e:
            log.error(f"Error en {key}: {e}")
            continue
        for job in found:
            fingerprint = f"{job.title.lower()[:40]}|{job.company.lower()[:30]}"
            if fingerprint not in seen:
                seen.add(fingerprint)
                jobs.append(job)

    log.info(f"=== Total de ofertas únicas: {len(jobs)} ===")
    return jobs


# =============================================================================
# Registro de portales
# =============================================================================
# La clave es la misma que usa web/portals.py: la interfaz elige por clave y nadie tiene que
# mantener una cadena de if/elif por portal. Firma única: (palabras, tope) -> ofertas.

def _fixed_list(fn: Callable[..., list[JobPosting]]) -> Callable[[list[str], int], list[JobPosting]]:
    """Dos portales publican una lista fija: reciben las palabras y las ignoran."""
    def scrape(keywords: list[str], max_results: int = 0) -> list[JobPosting]:
        return fn(max_results=max_results)
    return scrape


# Retirados el 24/09/2026: Jobicy (su API redirige a un artículo del blog y responde 403) y
# Remote.co (su feed agota el tiempo de espera en todas las corridas).
PORTAL_SCRAPERS: dict[str, Callable[[list[str], int], list[JobPosting]]] = {
    "getonboard": scrape_getonboard,
    "latojobs": scrape_latojobs,
    "puentetalent": scrape_puente,
    "remotive": scrape_remotive,
    "himalayas": scrape_himalayas,
    "remoteok": scrape_remoteok,
    "workingnomads": scrape_workingnomads,
    "arbeitnow": scrape_arbeitnow,
    "wwr": scrape_weworkremotely,
    "themuse": scrape_themuse,
    "jobspresso": _fixed_list(scrape_jobspresso),
    "justjoinit": scrape_justjoinit,
    "authenticjobs": _fixed_list(scrape_authenticjobs),
}
