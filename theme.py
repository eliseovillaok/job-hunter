"""
theme.py — CSS de la marca JobHunter, generado desde docs/brand/tokens.json.

Reglas (docs/brand/BRAND.md): colores solo de los tokens, Bricolage Grotesque para
títulos e Inter para texto, radios 22/28 px en bloques y píldora en botones y chips.
Los selectores de widgets usan los data-testid públicos de Streamlit.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

BRAND = Path(__file__).resolve().parent / "docs" / "brand"


@lru_cache(maxsize=1)
def tokens() -> dict:
    return json.loads((BRAND / "tokens.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def logo_svg(name: str) -> str:
    """SVG oficial del logo (docs/brand/logo/<name>.svg) para incrustar en HTML."""
    return (BRAND / "logo" / f"{name}.svg").read_text(encoding="utf-8").strip()


def _css_string(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def uploader_css(button: str, hint: str) -> str:
    """Traduce los textos fijos del file_uploader de Streamlit ("Upload", "200MB per file…")."""
    return f"""<style>
[data-testid="stFileUploaderDropzone"] button {{ background:var(--primary) !important; border-color:var(--primary) !important; color:var(--on-primary) !important; }}
[data-testid="stFileUploaderDropzone"] button [data-testid="stMarkdownContainer"] p {{ font-size:0 !important; }}
[data-testid="stFileUploaderDropzone"] button [data-testid="stMarkdownContainer"] p::after {{ content:{_css_string(button)}; font-size:14px; }}
[data-testid="stFileUploaderDropzoneInstructions"] span {{ font-size:0 !important; }}
[data-testid="stFileUploaderDropzoneInstructions"] span::after {{ content:{_css_string(hint)}; font-size:14px; color:var(--text-2); }}
</style>"""


def _vars(t: dict) -> str:
    return (
        f"--bg:{t['bg']};--surface:{t['surface']};--surface-2:{t['surface-subtle']};--tint:{t['surface-2']};"
        f"--border:{t['border-subtle']};--border-2:{t['border']};"
        f"--text:{t['text']};--text-2:{t['text-2']};--muted:{t['text-muted']};"
        f"--primary:{t['primary']};--primary-h:{t['primary-hover']};--on-primary:{t['on-primary']};"
        f"--mint:{t['secondary']};--coral:{t['accent']};--coral-s:{t['accent-strong']};"
        f"--ok:{t['success']};--warn:{t['warning']};--danger:{t['danger']};--info:{t['info']};"
        f"--score-mid:{t['score-mid']};"
    )


@lru_cache(maxsize=1)
def css() -> str:
    tk = tokens()
    light, dark = tk["light"], tk["dark"]
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&family=Inter:wght@400;500;600;700&display=swap');

:root {{ {_vars(light)} --forest:{light['text']};
  --display:'Bricolage Grotesque','Inter',sans-serif; --body:'Inter',system-ui,-apple-system,sans-serif; }}
html[data-theme="dark"] {{ {_vars(dark)} --forest:#16241E; color-scheme: dark; }}

/* ── Base ─────────────────────────────────────────────────────────────── */
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
  background: var(--bg) !important; color: var(--text); font-family: var(--body);
}}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu {{ display: none !important; }}
.block-container, [data-testid="stMainBlockContainer"] {{ max-width: 1180px; padding: 12px 28px 64px; }}
h1, h2, h3, h4 {{ font-family: var(--display); color: var(--text); letter-spacing: -.02em; }}
p, li, label, span, div {{ font-family: var(--body); }}
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li {{ color: var(--text-2); }}
[data-testid="stWidgetLabel"] p {{ color: var(--text); font-weight: 600; font-size: 14px; }}
[data-testid="stCaptionContainer"], .stCaption {{ color: var(--muted) !important; }}
a {{ color: var(--primary); }}

/* ── Botones (píldora) ────────────────────────────────────────────────── */
.stButton > button, .stDownloadButton > button, .stLinkButton > a, .stFormSubmitButton > button {{
  border-radius: 999px !important; font-weight: 700 !important; font-family: var(--body) !important;
  padding: 10px 20px !important; min-height: 44px; transition: background .15s ease, border-color .15s ease;
}}
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {{
  background: var(--primary) !important; border: 1px solid var(--primary) !important; color: var(--on-primary) !important;
}}
[data-testid="stBaseButton-primary"]:hover {{ background: var(--primary-h) !important; border-color: var(--primary-h) !important; }}
[data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondaryFormSubmit"], .stLinkButton > a {{
  background: var(--surface) !important; border: 1.5px solid var(--primary) !important; color: var(--primary) !important;
}}
[data-testid="stBaseButton-secondary"]:hover, .stLinkButton > a:hover {{ background: var(--tint) !important; }}
[data-testid="stBaseButton-tertiary"] {{ color: var(--text-2) !important; }}
[data-testid="stBaseButton-tertiary"]:hover {{ color: var(--primary) !important; }}
button p, .stLinkButton > a p {{ color: inherit !important; font-weight: 700; }}

/* ── Chips (st.pills / st.segmented_control) ─────────────────────────── */
button[data-variant="pills"], button[data-variant="segmented_control"] {{
  border-radius: 999px !important; border: 1px solid var(--border-2) !important; background: var(--surface) !important;
  color: var(--text-2) !important; font-weight: 600 !important;
}}
button[data-variant="pills"][aria-pressed="true"], button[data-variant="segmented_control"][aria-checked="true"] {{
  border-radius: 999px !important; background: var(--tint) !important; border: 1px solid var(--tint) !important;
  color: var(--primary) !important; font-weight: 700 !important;
}}

/* ── Campos ───────────────────────────────────────────────────────────── */
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div, [data-testid="stNumberInput"] [data-baseweb="input"] {{
  border-radius: 14px !important; background: var(--surface) !important; border-color: var(--border-2) !important;
}}
[data-baseweb="input"] input, [data-baseweb="textarea"] textarea, [data-baseweb="select"] * {{ color: var(--text) !important; }}
[data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within {{ border-color: var(--primary) !important; }}
[data-baseweb="tag"] {{ background: var(--tint) !important; border-radius: 999px !important; }}
[data-baseweb="tag"] span {{ color: var(--primary) !important; font-weight: 600; }}
[data-baseweb="popover"] ul {{ background: var(--surface) !important; }}

/* Zona de carga del CV */
[data-testid="stFileUploaderDropzone"] {{
  background: var(--surface) !important; border: 1.5px dashed var(--border-2) !important; border-radius: 22px !important;
  padding: 18px 20px !important;
}}
[data-testid="stFileUploaderDropzone"]:hover {{ border-color: var(--primary) !important; }}
[data-testid="stFileUploaderDropzoneInstructions"] span, [data-testid="stFileUploaderDropzoneInstructions"] small {{ color: var(--text-2) !important; }}

/* ── Contenedores ─────────────────────────────────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {{ border-radius: 22px; }}
[data-testid="stVerticalBlockBorderWrapper"][data-test-scroll-behavior], div[data-testid="stVerticalBlockBorderWrapper"] {{ border-color: var(--border) !important; }}
[data-testid="stExpander"] details {{ border-radius: 16px !important; border: 1px solid var(--border) !important; background: var(--surface); }}
[data-testid="stExpander"] summary p {{ color: var(--text) !important; font-weight: 600; }}
[data-testid="stAlert"] {{ border-radius: 16px; }}
[data-testid="stProgress"] > div > div > div > div {{ background: var(--primary) !important; }}
hr {{ border-color: var(--border) !important; }}

/* ── Componentes de marca ─────────────────────────────────────────────── */
.jh-nav {{ display:flex; align-items:center; gap:28px; min-height:48px; }}
.jh-logo svg {{ height:40px; width:auto; display:block; }}
.jh-links {{ display:flex; gap:24px; font-size:14px; font-weight:500; }}
.jh-links a {{ color:var(--text-2); text-decoration:none; }} .jh-links a:hover {{ color:var(--primary); }}

.jh-eyebrow {{ display:inline-flex; gap:8px; align-items:center; background:var(--tint); color:var(--primary);
  font:700 12.5px var(--body); padding:7px 14px; border-radius:999px; }}
.jh-h1 {{ font:800 clamp(38px,5.4vw,66px)/.98 var(--display) !important; letter-spacing:-.03em; text-transform:uppercase;
  color:var(--text); margin:18px 0 16px; }}
.jh-h1 em {{ font-style:normal; color:var(--primary); }}
.jh-sub {{ font-size:17px; line-height:1.55; color:var(--text-2); max-width:520px; margin:0 0 22px; }}
.jh-proof {{ display:flex; align-items:center; gap:14px; margin-top:10px; }}
.jh-proof p {{ margin:0; font-size:13.5px; line-height:1.35; color:var(--text-2); }} .jh-proof b {{ color:var(--text); }}
.jh-dots {{ display:flex; }} .jh-dots i {{ width:34px; height:34px; border-radius:50%; border:3px solid var(--bg);
  margin-left:-8px; display:grid; place-items:center; font-style:normal; font-size:15px; background:var(--tint); }}
.jh-dots i:first-child {{ margin-left:0; }}

.jh-mosaic {{ display:grid; grid-template-columns:1fr 1fr; grid-auto-rows:190px; border-radius:28px; overflow:hidden; }}
.jh-tile {{ position:relative; display:grid; place-items:center; }}
.jh-tile .lbl {{ position:absolute; left:14px; bottom:12px; font:700 12px var(--body); padding:6px 12px; border-radius:999px;
  background:rgba(255,255,255,.92); color:#13261E; }}

.jh-band {{ background:var(--forest); color:#E8F2EC; border-radius:28px; padding:30px 36px; display:grid;
  grid-template-columns:1.2fr repeat(4,1fr); gap:24px; align-items:center; margin:36px 0 8px; }}
.jh-band .n {{ font:800 38px var(--display); letter-spacing:-.02em; color:#FFFFFF; }}
.jh-band .l {{ font-size:13px; color:#A9C2B6; margin-top:4px; line-height:1.35; }}
.jh-band .intro {{ font-size:15px; line-height:1.5; color:#E8F2EC; }}
.jh-shapes {{ display:flex; gap:6px; margin-bottom:12px; }} .jh-shapes span {{ width:16px; height:16px; border-radius:5px; }}

.jh-label {{ display:block; font:600 12px var(--body); letter-spacing:.08em; text-transform:uppercase; color:var(--muted); margin:40px 0 12px; }}
.jh-steps {{ display:grid; grid-template-columns:repeat(3,1fr); gap:18px; }}
.jh-step {{ background:var(--surface); border:1px solid var(--border); border-radius:22px; padding:24px; }}
.jh-step .num {{ width:38px; height:38px; border-radius:12px; display:grid; place-items:center; font:800 17px var(--display);
  color:#FFFFFF; margin-bottom:14px; }}
.jh-step h3 {{ font:800 19px var(--display) !important; margin:0 0 6px; }} .jh-step p {{ margin:0; color:var(--text-2); font-size:14px; line-height:1.55; }}

.jh-title {{ font:800 clamp(26px,3.4vw,34px) var(--display) !important; letter-spacing:-.02em; margin:0; color:var(--text); }}
.jh-meta {{ color:var(--text-2); font-size:14px; margin:6px 0 0; }}
.jh-funnel {{ font-size:12.5px; color:var(--muted); background:var(--surface); border:1px solid var(--border);
  border-radius:14px; padding:10px 14px; }}
.jh-filters-h {{ font:700 12px var(--body); letter-spacing:.08em; text-transform:uppercase; color:var(--muted); margin:6px 0 2px; }}

/* La tarjeta es un contenedor nativo (key "job_N") para que los botones queden adentro. */
[class*="st-key-job_"] {{ background:var(--surface) !important; border:1px solid var(--border) !important; border-radius:22px !important;
  padding:20px 22px 12px !important; margin-bottom:6px; }}
[class*="st-key-job_"]:hover {{ border-color:var(--border-2) !important; box-shadow:0 10px 30px rgba(19,38,30,.07); }}
.jh-job {{ display:grid; grid-template-columns:52px 1fr 96px; gap:18px; }}
.jh-avatar {{ width:52px; height:52px; border-radius:14px; display:grid; place-items:center; font:800 20px var(--display); color:#FFFFFF; }}
.jh-job h3 {{ font:700 19px var(--body) !important; margin:0 0 4px; letter-spacing:-.01em; color:var(--text); }}
.jh-job .meta {{ font-size:13.5px; color:var(--text-2); margin-bottom:10px; }}
.jh-chips span {{ display:inline-block; font-size:12px; font-weight:600; padding:4px 10px; border-radius:999px;
  background:var(--surface-2); color:var(--text-2); margin:0 6px 6px 0; }}
.jh-chips .new {{ background:var(--coral-s); color:#FFFFFF; }}
.jh-why {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:6px; font-size:13.5px; line-height:1.5; }}
.jh-why .ok {{ color:var(--ok); }} .jh-why .no {{ color:var(--warn); }} .jh-why .na {{ color:var(--muted); }}
.jh-job p.jh-summary {{ font-size:13.5px; line-height:1.5; color:var(--text-2); margin:8px 0 0; }}
.jh-score {{ text-align:center; }}
.jh-ring {{ width:84px; height:84px; border-radius:50%; margin:0 auto 6px; display:grid; place-items:center; }}
.jh-ring div {{ width:66px; height:66px; border-radius:50%; background:var(--surface); display:grid; place-items:center;
  font:800 23px var(--display); color:var(--text); }}
.jh-score small {{ display:block; font-size:12px; font-weight:700; }}

.jh-footer {{ margin-top:56px; padding-top:18px; border-top:1px solid var(--border); font-size:12.5px; color:var(--muted);
  display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap; }}

/* Asistente (pasos) */
.jh-stepper {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin:10px 0 18px; }}
.jh-stepper .s {{ display:flex; gap:10px; align-items:center; padding:12px 14px; border-radius:16px; background:var(--surface);
  border:1px solid var(--border); }}
.jh-stepper .s b {{ width:28px; height:28px; border-radius:9px; display:grid; place-items:center; font:800 14px var(--display);
  background:var(--surface-2); color:var(--muted); flex:none; }}
.jh-stepper .s span {{ font-size:13px; font-weight:600; color:var(--muted); }}
.jh-stepper .on {{ border-color:var(--primary); }} .jh-stepper .on b {{ background:var(--primary); color:var(--on-primary); }}
.jh-stepper .on span {{ color:var(--text); }}
.jh-stepper .done b {{ background:var(--tint); color:var(--primary); }} .jh-stepper .done span {{ color:var(--text-2); }}

@media (max-width: 900px) {{
  .jh-links {{ display:none; }}
  .jh-band {{ grid-template-columns:1fr 1fr; padding:24px; }}
  .jh-steps {{ grid-template-columns:1fr; }}
  .jh-job {{ grid-template-columns:44px 1fr; }} .jh-score {{ grid-column:1/-1; display:flex; gap:12px; align-items:center; }}
  .jh-ring {{ margin:0; }} .jh-why {{ grid-template-columns:1fr; }}
  .jh-stepper {{ grid-template-columns:1fr 1fr; }}
  .jh-mosaic {{ grid-auto-rows:130px; }}
}}
</style>
"""
