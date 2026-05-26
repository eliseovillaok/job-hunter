"""
scrapers.py — Fuentes de trabajo con APIs públicas (sin auth requerida)
- Remotive:       API REST pública, enfocada en remoto
- Arbeitnow:      API REST pública, filtro remoto
- We Work Remotely: RSS feeds por categoría
- Himalayas:      API REST pública, 100% remoto
- RemoteOK:       API JSON pública, filtro por tag client-side
- Jobicy:         API REST pública, remoto global
- Working Nomads: API REST pública, categorías dev
- The Muse:       API REST paginada, EEUU + global
- Remote.co:      RSS feed, remoto global
- Jobspresso:     RSS feed, remoto global
- JustJoin.it:    API REST pública, Europa/global
- Authentic Jobs: RSS feed, EEUU + global
"""

import requests
import feedparser
import time
import logging
import html
import json
import re
from dataclasses import dataclass, field
from typing import Optional
import config
from config import SEARCH_KEYWORDS

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


def _matches_keywords(keywords: list[str], *parts: str) -> bool:
    """Client-side keyword filter for sources without server-side search."""
    if not keywords:
        return True
    haystack = " ".join(p for p in parts if p).lower()
    return any(kw.lower() in haystack for kw in keywords)


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
                seen.add(jid)

                jobs.append(JobPosting(
                    id=jid,
                    title=item.get("title", ""),
                    company=item.get("company_name", ""),
                    description=item.get("description", "")[:3000],
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
                        "remote": "true" if config.ONLY_REMOTE else "",
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
                    if config.ONLY_REMOTE and not is_remote:
                        continue

                    jid = f"arb-{item.get('slug', item.get('title', ''))[:40]}"
                    if jid in seen:
                        continue
                    seen.add(jid)

                    jobs.append(JobPosting(
                        id=jid,
                        title=item.get("title", ""),
                        company=item.get("company_name", ""),
                        description=item.get("description", "")[:3000],
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
    kw_lower = [k.lower() for k in keywords]

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
            if keywords and not any(kw in text for kw in kw_lower):
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
                description=summary[:3000],
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
                    description=(item.get("description", "") or "")[:3000],
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
    kw_lower = [k.lower() for k in keywords]

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
            if not any(kw in text for kw in kw_lower):
                continue

            jid = f"rok-{item.get('id', item.get('slug', ''))}"
            if jid in seen:
                continue
            seen.add(jid)

            jobs.append(JobPosting(
                id=jid,
                title=item.get("position", ""),
                company=item.get("company", ""),
                description=(item.get("description", "") or "")[:3000],
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
# Jobicy — https://jobicy.com/api/v0/remote-jobs
# NOTA: A partir de 2026 requiere autenticación (401). La API pública fue
# discontinuada. La función se mantiene por si el endpoint vuelve a ser libre,
# pero devuelve [] y loguea un warning en lugar de reintentar 12 veces.
# =============================================================================
def scrape_jobicy(keywords: list[str], max_results: int = 0) -> list[JobPosting]:
    jobs = []
    seen = set()

    for keyword in keywords:
        if max_results > 0 and len(jobs) >= max_results:
            break
        try:
            resp = requests.get(
                "https://jobicy.com/api/v0/remote-jobs",
                params={"count": 50, "tag": keyword},
                headers=HEADERS, timeout=15,
            )
            if resp.status_code == 401:
                log.warning("[Jobicy] API requiere autenticación (401) — fuente deshabilitada.")
                return []
            resp.raise_for_status()
            data = resp.json().get("jobs", [])
            log.info(f"[Jobicy] '{keyword}' → {len(data)} ofertas")

            for item in data:
                if max_results > 0 and len(jobs) >= max_results:
                    break
                jid = f"jcy-{item.get('id', item.get('jobSlug', ''))}"
                if jid in seen:
                    continue
                seen.add(jid)

                jobs.append(JobPosting(
                    id=jid,
                    title=item.get("jobTitle", ""),
                    company=item.get("companyName", ""),
                    description=(item.get("jobDescription", "") or "")[:3000],
                    location=item.get("jobGeo", "Remote"),
                    remote=True,
                    url=item.get("url", ""),
                    source="Jobicy",
                    published_at=item.get("pubDate", ""),
                    salary=item.get("annualSalaryMin", None),
                    tags=item.get("jobIndustry", []) if isinstance(item.get("jobIndustry"), list) else [],
                ))
            time.sleep(1)
        except Exception as e:
            log.error(f"[Jobicy] Error '{keyword}': {e}")

    return jobs


# =============================================================================
# Get on Board — HTML público + detalle SSR
# =============================================================================
def scrape_getonboard(keywords: list[str], max_results: int = 0) -> list[JobPosting]:
    jobs = []
    seen = set()
    categories = [
        "programming",
        "data-science-analytics",
        "sysadmin-devops-qa",
        "machine-learning-ai",
        # "product-innovation-agile",  # 404 desde 2026, categoría eliminada
        "design-ux",
        "customer-support",
        "digital-marketing",
    ]

    for category in categories:
        if max_results > 0 and len(jobs) >= max_results:
            break
        try:
            resp = requests.get(
                f"https://www.getonbrd.com/jobs/{category}",
                headers=HEADERS,
                timeout=20,
            )
            resp.raise_for_status()
            listing_html = resp.text
            urls = []
            for match in re.findall(r'href="(https://www\.getonbrd\.com/jobs/[^"?#]+)', listing_html):
                url = html.unescape(match)
                if url not in urls:
                    urls.append(url)
            log.info(f"[GetOnBoard] categoría '{category}' → {len(urls)} links")

            for url in urls:
                if max_results > 0 and len(jobs) >= max_results:
                    break
                jid = f"gob-{url.rsplit('/', 1)[-1][:80]}"
                if jid in seen:
                    continue

                detail = requests.get(url, headers=HEADERS, timeout=20)
                detail.raise_for_status()
                page_html = detail.text

                title_match = re.search(r'<h1[^>]*>.*?<span itemprop="title">\s*(.*?)\s*</span>', page_html, re.S)
                company_match = re.search(r'<h1[^>]*>.*?<span class="fake-hidden[^"]*">\s*in\s*(.*?)\s*</span>', page_html, re.S)
                location_match = re.search(r'<span class="location">\s*(.*?)\s*</span>', page_html, re.S)
                desc_match = re.search(r'<meta content="([^"]+)" name="description"', page_html)
                published_match = re.search(r'<meta content="([^"]+)" property="og:updated_time"', page_html)

                title = _strip_html(title_match.group(1)) if title_match else ""
                company = _strip_html(company_match.group(1)) if company_match else ""
                location = _strip_html(location_match.group(1)) if location_match else "Not specified"
                description = html.unescape(desc_match.group(1)) if desc_match else ""

                if not _matches_keywords(keywords, title, company, location, description, category):
                    continue

                remote = "remote" in location.lower() or "work from home" in page_html.lower()
                if config.ONLY_REMOTE and not remote:
                    continue

                seen.add(jid)
                jobs.append(JobPosting(
                    id=jid,
                    title=title,
                    company=company,
                    description=description[:3000],
                    location=location,
                    remote=remote,
                    url=url,
                    source="GetOnBoard",
                    published_at=published_match.group(1) if published_match else None,
                    tags=[],
                ))
                time.sleep(0.35)
            time.sleep(0.7)
        except Exception as e:
            log.error(f"[GetOnBoard] Error categoría '{category}': {e}")

    return jobs


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

            if jid in seen or not _matches_keywords(keywords, title, description, location):
                continue

            remote = job.get("jobLocationType") == "TELECOMMUTE" or "remote" in description.lower()
            if config.ONLY_REMOTE and not remote:
                continue

            seen.add(jid)
            jobs.append(JobPosting(
                id=jid,
                title=title,
                company=company,
                description=description[:3000],
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

                if not _matches_keywords(keywords, title, company, description, location):
                    continue

                remote = (
                    job.get("jobLocationType") == "TELECOMMUTE"
                    or "remote" in location.lower()
                    or "remote" in description.lower()
                )
                if config.ONLY_REMOTE and not remote:
                    continue

                seen.add(jid)
                jobs.append(JobPosting(
                    id=jid,
                    title=title,
                    company=company,
                    description=description[:3000],
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
    kw_lower = [k.lower() for k in keywords]

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
            if keywords and not any(kw in text for kw in kw_lower):
                continue

            jid = f"wn-{item.get('id', item.get('slug', ''))}"
            if jid in seen:
                continue
            seen.add(jid)

            jobs.append(JobPosting(
                id=jid,
                title=item.get("title", ""),
                company=item.get("company_name", ""),
                description=(item.get("description", "") or "")[:3000],
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
    kw_lower = [k.lower() for k in keywords]
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
                if keywords and not any(kw in text for kw in kw_lower):
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
                    description=contents[:3000],
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
# Remote.co — RSS feed
# =============================================================================
def scrape_remoteco(keywords: list[str], max_results: int = 0) -> list[JobPosting]:
    jobs = []
    seen = set()
    kw_lower = [k.lower() for k in keywords]

    try:
        feed = _parse_feed("https://remote.co/feed/")
        entries = feed.get("entries", [])
        log.info(f"[Remote.co] {len(entries)} ofertas totales, filtrando por keywords")

        for entry in entries:
            if max_results > 0 and len(jobs) >= max_results:
                break
            title_raw = entry.get("title", "")
            summary   = entry.get("summary", "")
            text      = f"{title_raw} {summary}".lower()
            if keywords and not any(kw in text for kw in kw_lower):
                continue

            jid = f"rco-{entry.get('id', entry.get('link', ''))[:60]}"
            if jid in seen:
                continue
            seen.add(jid)

            title, company = title_raw, ""
            if " at " in title_raw:
                parts = title_raw.rsplit(" at ", 1)
                title, company = parts[0].strip(), parts[1].strip()

            jobs.append(JobPosting(
                id=jid,
                title=title,
                company=company,
                description=summary[:3000],
                location="Remote",
                remote=True,
                url=entry.get("link", ""),
                source="Remote.co",
                published_at=entry.get("published", ""),
            ))
    except Exception as e:
        log.error(f"[Remote.co] Error: {e}")

    log.info(f"[Remote.co] {len(jobs)} ofertas tras filtro")
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
                description=entry.get("summary", "")[:3000],
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
    kw_lower = [k.lower() for k in keywords]

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
            if keywords and not any(kw in text for kw in kw_lower):
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
                description=f"{item.get('body', '') or ''}".strip()[:3000],
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
                description=entry.get("summary", "")[:3000],
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
def get_all_jobs() -> list[JobPosting]:
    all_jobs: list[JobPosting] = []
    seen_global: set[str] = set()

    log.info("=== Iniciando scraping de plataformas ===")

    # Fuentes con keywords
    keyword_sources = [
        ("Remotive",   scrape_remotive),
        ("Arbeitnow",  scrape_arbeitnow),
        ("Himalayas",  scrape_himalayas),
        ("Jobicy",     scrape_jobicy),
        ("GetOnBoard", scrape_getonboard),
        ("PuenteTalent", scrape_puente),
        ("LatoJobs",   scrape_latojobs),
    ]
    for name, fn in keyword_sources:
        log.info(f"--- {name} ---")
        try:
            jobs = fn(SEARCH_KEYWORDS)
            for job in jobs:
                key = f"{job.title.lower()[:40]}|{job.company.lower()[:30]}"
                if key not in seen_global:
                    seen_global.add(key)
                    all_jobs.append(job)
        except Exception as e:
            log.error(f"Error en {name}: {e}")

    # WeWorkRemotely (sin keywords, categorías fijas)
    log.info("--- WeWorkRemotely ---")
    try:
        jobs = scrape_weworkremotely(SEARCH_KEYWORDS)
        for job in jobs:
            key = f"{job.title.lower()[:40]}|{job.company.lower()[:30]}"
            if key not in seen_global:
                seen_global.add(key)
                all_jobs.append(job)
    except Exception as e:
        log.error(f"Error en WeWorkRemotely: {e}")

    log.info(f"=== Total de ofertas únicas: {len(all_jobs)} ===")
    return all_jobs
