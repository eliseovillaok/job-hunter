"""
web/portals.py — Portales de empleo que ofrece el asistente, agrupados por región.

Las claves coinciden con los `use_<portal>` de app.py para que la etapa 3 reuse el mismo pipeline.
Los portales con inicio de sesión necesitan Playwright y un perfil guardado: solo se ofrecen en local.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Portal:
    key: str
    label: str
    group: str
    default: bool = True
    login: bool = False


PORTALS: tuple[Portal, ...] = (
    Portal("getonboard", "Get on Board", "latam"),
    Portal("latojobs", "LatoJobs", "latam"),
    Portal("puentetalent", "Puente Talent", "latam"),
    Portal("remotive", "Remotive", "global"),
    Portal("himalayas", "Himalayas", "global"),
    Portal("remoteok", "RemoteOK", "global"),
    Portal("jobicy", "Jobicy", "global"),
    Portal("workingnomads", "WorkingNomads", "global"),
    Portal("arbeitnow", "Arbeitnow", "us"),
    Portal("wwr", "WeWorkRemotely", "us"),
    Portal("themuse", "The Muse", "us"),
    Portal("jobspresso", "Jobspresso", "us"),
    Portal("remoteco", "Remote.co", "us"),
    Portal("justjoinit", "JustJoin.it", "eu", default=False),
    Portal("authenticjobs", "AuthenticJobs", "other"),
    Portal("linkedin_browser", "LinkedIn", "login", default=False, login=True),
    Portal("bumeran_browser", "Bumeran", "login", default=False, login=True),
    Portal("computrabajo_browser", "Computrabajo", "login", default=False, login=True),
    Portal("indeed_browser", "Indeed", "login", default=False, login=True),
)
GROUPS = ("latam", "global", "us", "eu", "other", "login")
BY_KEY = {p.key: p for p in PORTALS}


def login_available() -> bool:
    """Los portales con login requieren Playwright (solo en local)."""
    try:
        import playwright.sync_api  # noqa: F401
        return True
    except ImportError:
        return False


def available() -> list[Portal]:
    can_login = login_available()
    return [p for p in PORTALS if can_login or not p.login]


def default_selection() -> list[str]:
    return [p.key for p in PORTALS if p.default]


def grouped(selected: list[str]) -> list[dict]:
    """Grupos para la plantilla, con cuántos portales están elegidos en cada uno."""
    avail = available()
    out = []
    for g in GROUPS:
        items = [p for p in avail if p.group == g]
        if items:
            out.append({"key": g, "items": items, "n_on": sum(p.key in selected for p in items)})
    return out
