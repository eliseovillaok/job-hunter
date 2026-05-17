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
# Working Nomads — https://www.workingnomads.com/api/exposed_jobs/
# Sin búsqueda por keyword; filtra client-side.
# =============================================================================
def scrape_workingnomads(keywords: list[str], max_results: int = 0) -> list[JobPosting]:
    jobs = []
    seen = set()
    kw_lower = [k.lower() for k in keywords]

    categories = ["development-programming", "devops-sysadmin", "back-end-programming",
                  "front-end-programming", "full-stack-programming"]

    for cat in categories:
        if max_results > 0 and len(jobs) >= max_results:
            break
        try:
            resp = requests.get(
                "https://www.workingnomads.com/api/exposed_jobs/",
                params={"category": cat},
                headers=HEADERS, timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            log.info(f"[WorkingNomads] '{cat}' → {len(data)} ofertas")

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
                    tags=[cat],
                ))
            time.sleep(1)
        except Exception as e:
            log.error(f"[WorkingNomads] Error '{cat}': {e}")

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
                params={"page": page, "descending": "true", "category": "Software Engineer"},
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
def scrape_remoteco(max_results: int = 0) -> list[JobPosting]:
    jobs = []
    seen = set()

    feeds = [
        "https://remote.co/job-categories/software-dev/feed/",
        "https://remote.co/job-categories/web-design/feed/",
    ]

    for feed_url in feeds:
        if max_results > 0 and len(jobs) >= max_results:
            break
        try:
            feed = feedparser.parse(feed_url)
            entries = feed.get("entries", [])
            log.info(f"[Remote.co] {feed_url.split('/')[-3]} → {len(entries)} ofertas")

            for entry in entries:
                if max_results > 0 and len(jobs) >= max_results:
                    break
                jid = f"rco-{entry.get('id', entry.get('link', ''))[:60]}"
                if jid in seen:
                    continue
                seen.add(jid)

                title = entry.get("title", "")
                company = ""
                if " at " in title:
                    parts = title.rsplit(" at ", 1)
                    title, company = parts[0].strip(), parts[1].strip()

                jobs.append(JobPosting(
                    id=jid,
                    title=title,
                    company=company,
                    description=entry.get("summary", "")[:3000],
                    location="Remote",
                    remote=True,
                    url=entry.get("link", ""),
                    source="Remote.co",
                    published_at=entry.get("published", ""),
                ))
            time.sleep(1)
        except Exception as e:
            log.error(f"[Remote.co] Error {feed_url}: {e}")

    return jobs


# =============================================================================
# Jobspresso — RSS feed
# =============================================================================
def scrape_jobspresso(max_results: int = 0) -> list[JobPosting]:
    jobs = []
    seen = set()

    try:
        feed = feedparser.parse("https://jobspresso.co/feed/")
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
        feed = feedparser.parse("https://authenticjobs.com/feed/")
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
