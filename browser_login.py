"""
browser_login.py — Abre una sesión persistente para portales con login.

Uso:
    python browser_login.py linkedin
    python browser_login.py bumeran --profile-dir .browser_profiles
"""

from __future__ import annotations

import argparse
import sys

from browser_scrapers import PORTALS, default_profile_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Guardar sesión de navegador para portales con login.")
    parser.add_argument("portal", choices=sorted(p.key for p in PORTALS.values()))
    parser.add_argument("--profile-dir", default=default_profile_dir())
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print(f"Playwright no está disponible: {e}")
        print("Instalá dependencias con: pip install -r requirements.txt")
        print("Y luego instalá Chromium con: python -m playwright install chromium")
        return 1

    portal = next(p for p in PORTALS.values() if p.key == args.portal)
    print(f"Abriré {portal.label} con perfil persistente en: {args.profile_dir}")
    print("Iniciá sesión manualmente en la ventana del navegador.")
    print("Cuando termines, volvé a la terminal y presioná Enter para guardar la sesión.")

    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            user_data_dir=args.profile_dir,
            headless=False,
        )
        page = context.new_page()
        page.goto(portal.home_url, wait_until="domcontentloaded", timeout=60000)
        try:
            input()
        finally:
            context.close()

    print("Sesión guardada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
