"""
browser_scrapers.py — Fuentes con login/sesión persistente vía Playwright.

Objetivo:
- Reutilizar una sesión real guardada por el usuario.
- Leer vacantes visibles en portales con login o JS pesado.
- No automatizar postulaciones.

Estado:
- Beta. Extracción best-effort orientada a listados.
- Si Playwright no está instalado o no hay sesión guardada, devuelve [].
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import quote_plus

from scrapers import JobPosting

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class BrowserPortal:
    key: str
    label: str
    home_url: str
    href_patterns: tuple[str, ...]
    search_runner: Callable


def _playwright_import():
    try:
        from playwright.sync_api import sync_playwright

        return sync_playwright, None
    except Exception as e:
        return None, str(e)


def playwright_ready() -> tuple[bool, str]:
    sync_playwright, err = _playwright_import()
    if sync_playwright is None:
        return False, f"Playwright no disponible: {err}"
    return True, ""


def default_profile_dir() -> str:
    return str(Path(".browser_profiles").resolve())


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def _matches_keywords(keywords: list[str], *parts: str) -> bool:
    if not keywords:
        return True
    haystack = " ".join(_normalize_text(p) for p in parts if p).lower()
    return any(kw.lower() in haystack for kw in keywords)


def _is_location_like(text: str) -> bool:
    lowered = text.lower()
    return any(
        token in lowered
        for token in (
            "remote",
            "remoto",
            "hybrid",
            "hibrido",
            "argentina",
            "mexico",
            "colombia",
            "chile",
            "peru",
            "uruguay",
            "panama",
            "bogota",
            "buenos aires",
            "santiago",
            "lima",
            "cdmx",
            "monterrey",
        )
    )


def _extract_card_candidates(page, href_patterns: tuple[str, ...]) -> list[dict]:
    script = """
    (patterns) => {
      const anchors = Array.from(document.querySelectorAll("a[href]"));
      return anchors.map((a) => {
        const href = a.href || "";
        const text = (a.textContent || "").replace(/\\s+/g, " ").trim();
        const card = a.closest("li, article, section, div");
        const lines = (card?.innerText || "")
          .split("\\n")
          .map((line) => line.replace(/\\s+/g, " ").trim())
          .filter(Boolean)
          .slice(0, 10);
        return { href, text, lines };
      }).filter((item) => patterns.some((pattern) => item.href.includes(pattern)));
    }
    """
    raw_items = page.evaluate(script, list(href_patterns))
    candidates = []
    seen = set()
    for item in raw_items:
        href = item.get("href", "")
        title = _normalize_text(item.get("text", ""))
        lines = [_normalize_text(line) for line in item.get("lines", []) if _normalize_text(line)]
        if not href or not title or len(title) < 4:
            continue
        key = (href, title)
        if key in seen:
            continue
        seen.add(key)
        candidates.append({"href": href, "title": title, "lines": lines})
    return candidates


def _job_from_candidate(candidate: dict, source: str) -> JobPosting:
    lines = candidate.get("lines", [])
    title = candidate.get("title", "") or (lines[0] if lines else "")
    company = ""
    location = ""

    for line in lines:
        if not company and line != title and not _is_location_like(line) and len(line) <= 80:
            company = line
            continue
        if not location and _is_location_like(line):
            location = line
        if company and location:
            break

    description = " | ".join(lines[:8])[:3000]
    remote = "remote" in description.lower() or "remoto" in description.lower()
    jid_seed = re.sub(r"[^a-zA-Z0-9]+", "-", candidate.get("href", ""))[-100:]

    return JobPosting(
        id=f"brw-{source.lower()}-{jid_seed}",
        title=title[:180],
        company=company[:120],
        description=description,
        location=location or "No especificada",
        remote=remote,
        url=candidate.get("href", ""),
        source=source,
        published_at=None,
        salary=None,
        tags=["browser", "login-beta"],
    )


def _run_linkedin_search(page, keyword: str):
    url = f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(keyword)}"
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3500)


def _run_bumeran_search(page, keyword: str):
    page.goto("https://www.bumeran.com.ar/", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2000)
    inputs = page.locator("input")
    if inputs.count() > 0:
        inputs.nth(0).fill(keyword)
    buttons = page.locator("button")
    for idx in range(min(buttons.count(), 20)):
        try:
            text = _normalize_text(buttons.nth(idx).inner_text())
        except Exception:
            continue
        if "buscar" in text.lower():
            buttons.nth(idx).click()
            break
    page.wait_for_timeout(3500)


def _run_computrabajo_search(page, keyword: str):
    page.goto("https://www.computrabajo.com/", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2000)
    inputs = page.locator("input")
    if inputs.count() > 0:
        inputs.nth(0).fill(keyword)
    buttons = page.locator("button, input[type='submit']")
    for idx in range(min(buttons.count(), 20)):
        try:
            text = _normalize_text(buttons.nth(idx).inner_text())
        except Exception:
            try:
                text = _normalize_text(buttons.nth(idx).get_attribute("value") or "")
            except Exception:
                text = ""
        if "buscar" in text.lower():
            buttons.nth(idx).click()
            break
    page.wait_for_timeout(3500)


def _run_indeed_search(page, keyword: str):
    url = f"https://www.indeed.com/jobs?q={quote_plus(keyword)}&remotejob=032b3046-06a3-4876-8dfd-474eb5e7ed11"
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3500)


PORTALS: dict[str, BrowserPortal] = {
    "LinkedInBrowser": BrowserPortal(
        key="linkedin",
        label="LinkedIn",
        home_url="https://www.linkedin.com/jobs",
        href_patterns=("/jobs/view/",),
        search_runner=_run_linkedin_search,
    ),
    "BumeranBrowser": BrowserPortal(
        key="bumeran",
        label="Bumeran",
        home_url="https://www.bumeran.com.ar/",
        href_patterns=("/empleos/",),
        search_runner=_run_bumeran_search,
    ),
    "ComputrabajoBrowser": BrowserPortal(
        key="computrabajo",
        label="Computrabajo",
        home_url="https://www.computrabajo.com/",
        href_patterns=("/ofertas-de-trabajo/", "/trabajo-de-"),
        search_runner=_run_computrabajo_search,
    ),
    "IndeedBrowser": BrowserPortal(
        key="indeed",
        label="Indeed",
        home_url="https://www.indeed.com/jobs",
        href_patterns=("/viewjob?", "/rc/clk?"),
        search_runner=_run_indeed_search,
    ),
}


def scrape_browser_portal(
    portal_name: str,
    keywords: list[str],
    profile_dir: str,
    max_results: int = 0,
) -> list[JobPosting]:
    portal = PORTALS.get(portal_name)
    if portal is None:
        log.warning(f"[Browser] Portal desconocido: {portal_name}")
        return []

    sync_playwright, err = _playwright_import()
    if sync_playwright is None:
        log.warning(f"[{portal.label}] Playwright no disponible: {err}")
        return []

    profile_dir = profile_dir or default_profile_dir()
    os.makedirs(profile_dir, exist_ok=True)

    jobs = []
    seen = set()

    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        try:
            for keyword in keywords:
                if max_results > 0 and len(jobs) >= max_results:
                    break
                try:
                    portal.search_runner(page, keyword)
                    candidates = _extract_card_candidates(page, portal.href_patterns)
                    log.info(f"[{portal.label}] '{keyword}' → {len(candidates)} candidatos")
                    for candidate in candidates:
                        if max_results > 0 and len(jobs) >= max_results:
                            break
                        job = _job_from_candidate(candidate, portal_name)
                        if job.id in seen:
                            continue
                        if not _matches_keywords(keywords, job.title, job.company, job.description, job.location):
                            continue
                        seen.add(job.id)
                        jobs.append(job)
                except Exception as e:
                    log.error(f"[{portal.label}] Error keyword '{keyword}': {e}")
        finally:
            context.close()

    return jobs
