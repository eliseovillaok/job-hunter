"""
build_logo.py — Genera el logotipo oficial de JobHunter en trazos vectoriales (docs/brand/logo/).

Uso (herramienta de desarrollo, ver BRAND.md §3):
    python scripts/build_logo.py ruta/a/BricolageGrotesque.ttf

La fuente (Bricolage Grotesque, licencia OFL) no se versiona: se descarga de
https://github.com/google/fonts/tree/main/ofl/bricolagegrotesque
Requiere fonttools (requirements-dev.txt) y Playwright/Chromium para los PNG.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "brand" / "logo"
TOKENS = json.loads((ROOT / "docs" / "brand" / "tokens.json").read_text(encoding="utf-8"))
L, D = TOKENS["light"], TOKENS["dark"]

FOREST = L["text"]          # #13261E · fondo del ícono
MINT = L["secondary"]       # #7FC8A9 · J sobre oscuro
WHITE = "#FFFFFF"
EMERALD = L["primary"]      # #1F6F54 · J sobre claro / "Hunter"
TEXT_DARK_UI = D["text"]    # #E8F2EC · "Job" sobre oscuro
PRIMARY_DARK = D["primary"] # #5FCB9F · "Hunter" sobre oscuro


class Font:
    def __init__(self, path: str):
        vf = TTFont(path)
        # Mismo estilo que en la web: peso 800; tamaño óptico de display.
        self.font = instantiateVariableFont(vf, {"wght": 800, "opsz": 72, "wdth": 100})
        self.upm = self.font["head"].unitsPerEm
        self.cmap = self.font.getBestCmap()
        self.glyphs = self.font.getGlyphSet()
        self.hmtx = self.font["hmtx"]

    def run(self, text: str, size: float, tracking_em: float = 0.0):
        """Devuelve [(char, path_d, x_offset)] y el bbox total, con baseline en y=0."""
        scale = size / self.upm
        x, out = 0.0, []
        xmin = ymin = float("inf")
        xmax = ymax = float("-inf")
        for ch in text:
            gname = self.cmap[ord(ch)]
            pen = SVGPathPen(self.glyphs)
            # y invertida (SVG crece hacia abajo)
            self.glyphs[gname].draw(TransformPen(pen, (scale, 0, 0, -scale, x, 0)))
            bp = BoundsPen(self.glyphs)
            self.glyphs[gname].draw(TransformPen(bp, (scale, 0, 0, -scale, x, 0)))
            if bp.bounds:
                a, b, c, d = bp.bounds
                xmin, ymin, xmax, ymax = min(xmin, a), min(ymin, b), max(xmax, c), max(ymax, d)
            out.append((ch, pen.getCommands()))
            x += self.hmtx[gname][0] * scale + tracking_em * size
        return out, (xmin, ymin, xmax, ymax)


def group(parts, colors, dx, dy) -> str:
    paths = "".join(f'<path fill="{colors[i]}" d="{d}"/>' for i, (_, d) in enumerate(parts))
    return f'<g transform="translate({dx:.2f} {dy:.2f})">{paths}</g>'


def svg(w, h, body, bg: str | None = None, rx: float = 0) -> str:
    rect = f'<rect width="{w}" height="{h}" rx="{rx}" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
            f'{rect}{body}</svg>\n')


ICON_CAP = 0.40   # altura de la H respecto del ícono (y de los lockups, con o sin recuadro)


def monogram(font: Font, box: float, cap_ratio: float, colors) -> str:
    """JH centrada ópticamente en un cuadrado de lado `box`."""
    # Tamaño tal que la altura de la H ocupe `cap_ratio` del cuadrado.
    _, (x0, y0, x1, y1) = font.run("H", 100)
    size = 100 * (box * cap_ratio) / (y1 - y0)
    parts, (x0, y0, x1, y1) = font.run("JH", size, tracking_em=-0.035)
    dx = (box - (x1 - x0)) / 2 - x0
    dy = (box - (y1 - y0)) / 2 - y0
    return group(parts, colors, dx, dy)


def wordmark(font: Font, size: float, job_color: str, hunter_color: str):
    parts, bbox = font.run("JobHunter", size, tracking_em=-0.025)
    colors = [job_color] * 3 + [hunter_color] * 6
    return parts, bbox, colors


def lockup(font: Font, height: float, icon_body: str | None, glyph_colors, job, hunter) -> str:
    """Ícono (o JH sin recuadro) + nombre, alineados al centro vertical."""
    gap = height * 0.28
    parts, (x0, y0, x1, y1), colors = wordmark(font, height * 0.62, job, hunter)
    word_w = x1 - x0
    if icon_body:
        mark = f'<svg x="0" y="0" width="{height}" height="{height}" viewBox="0 0 100 100">{icon_body}</svg>'
        mark_w = height
    else:
        # Misma JH y misma posición que dentro del recuadro (ICON_CAP): al cambiar de tema solo
        # desaparece el fondo; las letras no cambian de tamaño ni el nombre se desplaza.
        mark = f'<svg x="0" y="0" width="{height}" height="{height}" viewBox="0 0 100 100">{monogram(font, 100, ICON_CAP, glyph_colors)}</svg>'
        mark_w = height
    dx = mark_w + gap - x0
    dy = height / 2 - (y0 + y1) / 2
    w = mark_w + gap + word_w + 2
    return svg(round(w, 1), height, mark + group(parts, colors, dx, dy))


def write(name: str, content: str) -> None:
    (OUT / name).write_text(content, encoding="utf-8", newline="\n")


def render_pngs(sizes: dict[str, tuple[str, int]]) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for png, (svg_name, px) in sizes.items():
            page = browser.new_page(viewport={"width": px, "height": px}, device_scale_factor=1)
            markup = (OUT / svg_name).read_text(encoding="utf-8")
            page.set_content(f'<html><body style="margin:0">{markup.replace("<svg ", f"<svg style=\"width:{px}px;height:{px}px;display:block\" ", 1)}</body></html>')
            page.screenshot(path=str(OUT / png), omit_background=True)
            page.close()
        browser.close()


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    font = Font(sys.argv[1])
    OUT.mkdir(parents=True, exist_ok=True)

    on_dark = [MINT, WHITE]
    on_light = [EMERALD, FOREST]
    icon_body = monogram(font, 100, ICON_CAP, on_dark)
    icon_rounded = f'<rect width="100" height="100" rx="22.5" fill="{FOREST}"/>{icon_body}'

    # Ícono de app: cuadrado sin redondear (las tiendas aplican su máscara) y versión web redondeada.
    write("icon.svg", svg(100, 100, icon_body, bg=FOREST))
    write("icon-rounded.svg", svg(100, 100, icon_rounded))
    # JH sin recuadro (fondo transparente)
    write("glyph-on-dark.svg", svg(100, 100, monogram(font, 100, 0.62, on_dark)))
    write("glyph-on-light.svg", svg(100, 100, monogram(font, 100, 0.62, on_light)))
    write("glyph-on-emerald.svg", svg(100, 100, monogram(font, 100, 0.62, [L["surface-2"], WHITE])))
    write("glyph-mono.svg", svg(100, 100, monogram(font, 100, 0.62, ["currentColor", "currentColor"])))
    # Lockups: ícono + nombre (claro) y JH sin recuadro + nombre (oscuro)
    write("lockup-light.svg", lockup(font, 100, icon_rounded, None, FOREST, EMERALD))
    write("lockup-dark.svg", lockup(font, 100, None, on_dark, TEXT_DARK_UI, PRIMARY_DARK))
    write("lockup-light-glyph.svg", lockup(font, 100, None, on_light, FOREST, EMERALD))

    render_pngs({
        "icon-1024.png": ("icon.svg", 1024),       # App Store / Play Store
        "icon-512.png": ("icon.svg", 512),
        "apple-touch-icon.png": ("icon.svg", 180),
        "favicon-32.png": ("icon-rounded.svg", 32),
        "favicon-16.png": ("icon-rounded.svg", 16),
    })
    print("Logo generado en", OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
