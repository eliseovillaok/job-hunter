"""
web/portals.py — Portales de empleo que ofrece el asistente, agrupados por región.

Las claves coinciden con los `use_<portal>` de app.py para que la etapa 3 reuse el mismo pipeline.
Solo entran portales de acceso público: la spec prohíbe atravesar logins, CAPTCHA o límites de acceso
(§21.9 y §34), así que un portal nuevo necesita API, feed o página pública revisada.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Portal:
    key: str
    label: str
    group: str
    default: bool = True


PORTALS: tuple[Portal, ...] = (
    Portal("getonboard", "Get on Board", "latam"),
    Portal("latojobs", "LatoJobs", "latam"),
    Portal("puentetalent", "Puente Talent", "latam"),
    Portal("remotive", "Remotive", "global"),
    Portal("himalayas", "Himalayas", "global"),
    Portal("remoteok", "RemoteOK", "global"),
    Portal("workingnomads", "WorkingNomads", "global"),
    Portal("arbeitnow", "Arbeitnow", "us"),
    Portal("wwr", "WeWorkRemotely", "us"),
    Portal("themuse", "The Muse", "us"),
    Portal("jobspresso", "Jobspresso", "us"),
    Portal("justjoinit", "JustJoin.it", "eu", default=False),
    Portal("authenticjobs", "AuthenticJobs", "other"),
)
GROUPS = ("latam", "global", "us", "eu", "other")
BY_KEY = {p.key: p for p in PORTALS}


def available() -> list[Portal]:
    return list(PORTALS)


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
