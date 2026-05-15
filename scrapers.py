"""
scrapers.py — Fuentes de trabajo con APIs públicas (sin auth requerida)
- Remotive:       API REST pública, enfocada en remoto
- Arbeitnow:      API REST pública, filtro remoto
- We Work Remotely: RSS feeds por categoría
- Himalayas:      API REST pública, 100% remoto
"""

import requests
import feedparser
import time
import logging
from dataclasses import dataclass, field
from typing import Optional
from config import SEARCH_KEYWORDS, ONLY_REMOTE

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {"User-Agent": "JobHunterBot/1.0 (personal job search automation)"}


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

    for keyword in keywords:
        if max_results > 0 and len(jobs) >= max_results:
            break
        page = 1
        while True:
            if max_results > 0 and len(jobs) >= max_results:
                log.info(f"[Arbeitnow] Alcanzado límite de {max_results} ofertas")
                break
            try:
                resp = requests.get(
                    "https://www.arbeitnow.com/api/job-board-api",
                    params={
                        "search": keyword,
                        "remote": "true" if ONLY_REMOTE else "",
                        "page": page,
                    },
                    headers=HEADERS, timeout=15
                )
                resp.raise_for_status()
                data = resp.json().get("data", [])
                if not data:
                    break
                log.info(f"[Arbeitnow] '{keyword}' (página {page}) → {len(data)} ofertas")

                for item in data:
                    if max_results > 0 and len(jobs) >= max_results:
                        break
                    is_remote = item.get("remote", False)
                    if ONLY_REMOTE and not is_remote:
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
# We Work Remotely — RSS por categorías
# =============================================================================
def scrape_weworkremotely(max_results: int = 0) -> list[JobPosting]:
    jobs = []
    seen = set()

    feeds = [
        ("https://weworkremotely.com/categories/remote-programming-jobs.rss", "Programming"),
        ("https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss", "DevOps"),
    ]

    for feed_url, category in feeds:
        if max_results > 0 and len(jobs) >= max_results:
            break
        try:
            feed = feedparser.parse(feed_url)
            entries = feed.get("entries", [])
            log.info(f"[WeWorkRemotely] {category} → {len(entries)} ofertas")

            for entry in entries:
                if max_results > 0 and len(jobs) >= max_results:
                    break
                jid = f"wwr-{entry.get('id', entry.get('link',''))[:50]}"
                if jid in seen:
                    continue
                seen.add(jid)

                title = entry.get("title", "")
                company = ""
                # Formato WWR: "Company: Title"
                if ": " in title:
                    parts = title.split(": ", 1)
                    company, title = parts[0].strip(), parts[1].strip()

                jobs.append(JobPosting(
                    id=jid,
                    title=title,
                    company=company,
                    description=entry.get("summary", "")[:3000],
                    location="Remote",
                    remote=True,
                    url=entry.get("link", ""),
                    source="WeWorkRemotely",
                    published_at=entry.get("published", ""),
                    tags=[category],
                ))
            time.sleep(1)
        except Exception as e:
            log.error(f"[WeWorkRemotely] Error feed {category}: {e}")

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
        jobs = scrape_weworkremotely()
        for job in jobs:
            key = f"{job.title.lower()[:40]}|{job.company.lower()[:30]}"
            if key not in seen_global:
                seen_global.add(key)
                all_jobs.append(job)
    except Exception as e:
        log.error(f"Error en WeWorkRemotely: {e}")

    log.info(f"=== Total de ofertas únicas: {len(all_jobs)} ===")
    return all_jobs
