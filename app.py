"""
app.py — Job Hunter UI con Streamlit
"""

import streamlit as st
import streamlit.components.v1 as components
import json
import time
import os
from datetime import datetime
from pathlib import Path

# ─── Detección de entorno ─────────────────────────────────────────────────────
# Streamlit Cloud setea la variable STREAMLIT_SHARING_MODE o bien corre dentro
# de un contenedor sin Playwright instalado. Detectamos ambas condiciones.
def _is_cloud() -> bool:
    """True cuando corre en Streamlit Cloud (o cualquier entorno sin Playwright)."""
    if os.environ.get("STREAMLIT_SHARING_MODE") or os.environ.get("IS_STREAMLIT_CLOUD"):
        return True
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return False  # Playwright disponible → entorno local
    except ImportError:
        return True

IS_CLOUD = _is_cloud()

# ─── Página ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Job Hunter AI",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
/* ═══════════════════════════════════════════════════════════════════════════
   JOB HUNTER AI — Design System v3.0
   Premium SaaS Interface · Inter + Plus Jakarta Sans · Light Mode
   ═══════════════════════════════════════════════════════════════════════════ */

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@700;800&display=swap');

/* ── 1. TOKENS ─────────────────────────────────────────────────────────── */
:root {
  color-scheme: light only;
  forced-color-adjust: none;

  /* Brand palette */
  --blue-50:#eff6ff; --blue-100:#dbeafe; --blue-200:#bfdbfe;
  --blue-500:#3b82f6; --blue-600:#2563eb; --blue-700:#1d4ed8; --blue-900:#1e3a8a;
  --violet-50:#f5f3ff; --violet-100:#ede9fe;
  --violet-500:#8b5cf6; --violet-600:#7c3aed;
  --emerald-50:#ecfdf5; --emerald-100:#d1fae5;
  --emerald-600:#059669; --emerald-700:#047857; --emerald-900:#064e3b;
  --amber-50:#fffbeb; --amber-100:#fef3c7;
  --amber-600:#d97706; --amber-900:#78350f;
  --red-50:#fef2f2; --red-100:#fee2e2;
  --red-600:#dc2626; --red-900:#7f1d1d;
  --slate-50:#f8fafc; --slate-100:#f1f5f9; --slate-200:#e2e8f0;
  --slate-300:#cbd5e1; --slate-400:#94a3b8; --slate-500:#64748b;
  --slate-600:#475569; --slate-700:#334155; --slate-800:#1e293b; --slate-900:#0f172a;

  /* Semantic — surfaces */
  --bg:        #f8fafc;
  --surface:   #ffffff;
  --surface-2: #f1f5f9;
  --surface-3: #e2e8f0;

  /* Semantic — text */
  --t1: #0f172a;   /* primary text   */
  --t2: #475569;   /* secondary text */
  --t3: #94a3b8;   /* muted text     */
  --ti: #ffffff;   /* inverse text   */

  /* Semantic — borders */
  --b1: #e2e8f0;
  --b2: #cbd5e1;

  /* Semantic — brand */
  --p:   #2563eb;  --ph:  #1d4ed8;
  --ps:  #eff6ff;  --pm:  #dbeafe;
  --a:   #7c3aed;  --as:  #f5f3ff;
  --ok:  #059669;  --oks: #ecfdf5; --okm: #d1fae5; --okt: #064e3b;
  --wn:  #d97706;  --wns: #fffbeb; --wnt: #78350f;
  --er:  #dc2626;  --ers: #fef2f2; --ert: #7f1d1d;

  /* Typography */
  --font:    'Inter', system-ui, -apple-system, sans-serif;
  --font-d:  'Plus Jakarta Sans', 'Inter', sans-serif;

  /* Radius */
  --r1:4px; --r2:6px; --r3:10px; --r4:14px; --r5:20px; --r6:28px; --rf:9999px;

  /* Shadows */
  --s0: 0 1px 2px rgba(15,23,42,.05);
  --s1: 0 1px 3px rgba(15,23,42,.08),0 1px 2px rgba(15,23,42,.04);
  --s2: 0 4px 8px rgba(15,23,42,.07),0 2px 4px rgba(15,23,42,.04);
  --s3: 0 12px 24px rgba(15,23,42,.09),0 4px 8px rgba(15,23,42,.04);
  --s4: 0 24px 48px rgba(15,23,42,.11),0 8px 16px rgba(15,23,42,.05);
  --sp: 0 8px 24px rgba(37,99,235,.28);
  --sr: 0 0 0 3px rgba(37,99,235,.15);
  --se: 0 0 0 3px rgba(220,38,38,.14);

  /* Motion */
  --ease: cubic-bezier(.16,1,.3,1);
  --eio:  cubic-bezier(.4,0,.2,1);
  --spr:  cubic-bezier(.34,1.56,.64,1);
  --t1d: 120ms; --t2d: 200ms; --t3d: 300ms;
}

/* ── 2. RESET & BASE ────────────────────────────────────────────────── */
html {
  color-scheme: light only !important;
  forced-color-adjust: none !important;
  background: var(--bg) !important;
}
html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
  background: var(--bg) !important;
  color: var(--t1) !important;
  font-family: var(--font) !important;
  -webkit-font-smoothing: antialiased;
}

/* ── 3. LAYOUT ──────────────────────────────────────────────────────── */
div.block-container,
div[data-testid="stMainBlockContainer"] {
  max-width: 1080px !important;
  padding: 2rem 2.5rem 4rem !important;
  margin: 0 auto !important;
}
section[data-testid="stSidebar"],
button[data-testid="collapsedControl"] { display: none !important; }

/* ── 4. TYPOGRAPHY ──────────────────────────────────────────────────── */
h1,h2,h3,h4,h5,h6 {
  font-family: var(--font-d) !important;
  color: var(--t1) !important;
  letter-spacing: -.025em;
  line-height: 1.2;
}
p,li,label,span { font-family: var(--font); }
hr { border:none !important; border-top:1px solid var(--b1) !important; margin:.25rem 0 !important; }

/* ── 5. BUTTONS ─────────────────────────────────────────────────────── */
button[data-testid^="baseButton"],button[kind] {
  border-radius: var(--r3) !important;
  font-family: var(--font) !important;
  font-weight: 600 !important;
  font-size: 14px !important;
  letter-spacing: -.01em;
  transition:
    transform var(--t1d) var(--ease),
    box-shadow var(--t2d) var(--ease),
    background-color var(--t1d) var(--eio),
    border-color var(--t1d) var(--eio),
    color var(--t1d) var(--eio) !important;
}
button[data-testid="baseButton-primary"],button[kind="primary"] {
  background: var(--p) !important;
  color: var(--ti) !important;
  border: 1px solid transparent !important;
  box-shadow: var(--sp) !important;
  padding: .6rem 1.25rem !important;
}
button[data-testid="baseButton-primary"]:hover,button[kind="primary"]:hover {
  background: var(--ph) !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 12px 28px rgba(37,99,235,.34) !important;
}
button[data-testid="baseButton-primary"]:active,button[kind="primary"]:active {
  transform: translateY(0) !important;
  box-shadow: var(--sp) !important;
}
button[data-testid="baseButton-secondary"],button[kind="secondary"] {
  background: var(--surface) !important;
  color: var(--t1) !important;
  border: 1px solid var(--b1) !important;
  box-shadow: var(--s0) !important;
}
button[data-testid="baseButton-secondary"]:hover,button[kind="secondary"]:hover {
  background: var(--surface-2) !important;
  border-color: var(--b2) !important;
  transform: translateY(-1px) !important;
  box-shadow: var(--s1) !important;
}
button[data-testid^="baseButton"]:focus-visible,button[kind]:focus-visible {
  outline: none !important;
  box-shadow: var(--sr) !important;
}
a[data-testid="stLinkButton"] {
  border-radius: var(--r3) !important;
  font-weight: 600 !important;
  font-size: 14px !important;
  transition: all var(--t2d) var(--ease) !important;
}

/* ── 6. INPUTS ──────────────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
  background: var(--surface) !important;
  border: 1px solid var(--b1) !important;
  border-radius: var(--r3) !important;
  color: var(--t1) !important;
  font-family: var(--font) !important;
  font-size: 14px !important;
  box-shadow: var(--s0) !important;
  transition: border-color var(--t1d) var(--eio), box-shadow var(--t2d) var(--ease) !important;
}
[data-testid="stTextInput"] input:hover,
[data-testid="stTextArea"] textarea:hover { border-color: var(--b2) !important; }
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
  border-color: var(--p) !important;
  box-shadow: var(--sr) !important;
  outline: none !important;
}
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder { color: var(--t3) !important; }
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
  background: var(--surface) !important;
  border: 1px solid var(--b1) !important;
  border-radius: var(--r3) !important;
  box-shadow: var(--s0) !important;
  min-height: 42px !important;
  transition: border-color var(--t1d) var(--eio), box-shadow var(--t2d) var(--ease) !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div:focus-within {
  border-color: var(--p) !important;
  box-shadow: var(--sr) !important;
}
[data-baseweb="select"] * { color: var(--t1) !important; }
[data-testid="stCheckbox"] input[type="checkbox"] { accent-color: var(--p) !important; }
[data-testid="stCheckbox"] label { font-size: 14px !important; color: var(--t1) !important; }

/* ── 7. CONTAINERS ──────────────────────────────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] {
  border: 1px solid var(--b1) !important;
  border-radius: var(--r5) !important;
  background: var(--surface) !important;
  box-shadow: var(--s1) !important;
  overflow: hidden !important;
  transition: box-shadow var(--t2d) var(--ease), border-color var(--t2d) var(--ease) !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
  box-shadow: var(--s2) !important;
  border-color: var(--b2) !important;
}

/* ── 8. EXPANDERS ───────────────────────────────────────────────────── */
div[data-testid="stExpander"] {
  border: 1px solid var(--b1) !important;
  border-radius: var(--r4) !important;
  background: var(--surface) !important;
  box-shadow: var(--s0) !important;
  overflow: hidden !important;
  transition: box-shadow var(--t2d) var(--ease) !important;
}
div[data-testid="stExpander"]:hover { box-shadow: var(--s1) !important; }
div[data-testid="stExpander"] summary {
  font-weight: 600 !important;
  font-size: 14px !important;
  color: var(--t1) !important;
}

/* ── 9. TABS ────────────────────────────────────────────────────────── */
div[data-testid="stTabs"] [role="tablist"] {
  gap: 4px !important;
  border-bottom: 1px solid var(--b1) !important;
}
div[data-testid="stTabs"] button[role="tab"] {
  border-radius: var(--r3) var(--r3) 0 0 !important;
  border: 1px solid transparent !important;
  background: transparent !important;
  color: var(--t2) !important;
  font-weight: 500 !important;
  font-size: 14px !important;
  padding: .6rem 1rem !important;
  transition: all var(--t1d) var(--eio) !important;
  margin-bottom: -1px;
}
div[data-testid="stTabs"] button[role="tab"]:hover {
  color: var(--t1) !important;
  background: var(--surface-2) !important;
}
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
  background: var(--surface) !important;
  color: var(--p) !important;
  border-color: var(--b1) !important;
  border-bottom-color: var(--surface) !important;
  font-weight: 700 !important;
}

/* ── 10. PROGRESS ───────────────────────────────────────────────────── */
[data-testid="stProgress"] {
  border-radius: var(--rf) !important;
  background: var(--surface-2) !important;
  height: 6px !important;
  overflow: hidden !important;
}
[data-testid="stProgress"] > div {
  background: linear-gradient(90deg, var(--p), var(--a)) !important;
  border-radius: var(--rf) !important;
  transition: width .4s var(--ease) !important;
}

/* ── 11. METRICS ────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
  background: var(--surface) !important;
  border: 1px solid var(--b1) !important;
  border-radius: var(--r5) !important;
  padding: 1.25rem !important;
  box-shadow: var(--s1) !important;
}
[data-testid="stMetricValue"] {
  font-family: var(--font-d) !important;
  font-size: 2rem !important;
  font-weight: 800 !important;
  letter-spacing: -.04em !important;
  color: var(--t1) !important;
}
[data-testid="stMetricLabel"] {
  font-size: 11px !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: .06em !important;
  color: var(--t3) !important;
}

/* ── 12. MISC ───────────────────────────────────────────────────────── */
[data-testid="stFileUploaderDropzone"] {
  border: 2px dashed var(--b2) !important;
  border-radius: var(--r5) !important;
  background: var(--surface-2) !important;
  transition: border-color var(--t1d) var(--eio), background var(--t1d) var(--eio) !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
  border-color: var(--p) !important;
  background: var(--ps) !important;
}
div[data-testid="stForm"] { border:none !important; padding:0 !important; background:transparent !important; }
[data-testid="stAlert"] { border-radius:var(--r4) !important; font-size:14px !important; }
[data-testid="stCaptionContainer"] p { font-size:13px !important; color:var(--t3) !important; }

/* ── Form submit buttons (kind differs from baseButton) ── */
button[data-testid="stFormSubmitButton"] > button,
[data-testid="stFormSubmitButton"] button,
button[kind="secondaryFormSubmit"],
button[kind="primaryFormSubmit"] {
  border-radius: var(--r3) !important;
  font-family: var(--font) !important;
  font-weight: 600 !important;
  font-size: 14px !important;
  background: var(--surface) !important;
  color: var(--t1) !important;
  border: 1px solid var(--b1) !important;
  box-shadow: var(--s0) !important;
  transition: all var(--t1d) var(--eio) !important;
}
button[data-testid="stFormSubmitButton"] > button:hover,
[data-testid="stFormSubmitButton"] button:hover {
  background: var(--surface-2) !important;
  border-color: var(--b2) !important;
  transform: translateY(-1px) !important;
}

/* ── Checkboxes — force light styling ── */
[data-testid="stCheckbox"] { color: var(--t1) !important; }
[data-testid="stCheckbox"] input[type="checkbox"] {
  accent-color: #2563eb !important;
  width: 16px !important;
  height: 16px !important;
  cursor: pointer !important;
  background: #ffffff !important;
  border: 1.5px solid #cbd5e1 !important;
}
[data-testid="stCheckbox"] label,
[data-testid="stCheckbox"] p {
  color: var(--t1) !important;
  font-size: 14px !important;
}

/* ── Slider — force primary color ── */
[data-testid="stSlider"] [role="slider"] {
  background: #2563eb !important;
  border-color: #2563eb !important;
  box-shadow: 0 0 0 3px rgba(37,99,235,.18) !important;
}
[data-testid="stSlider"] [data-baseweb="slider"] div[data-testid*="StyledThumb"] {
  background: #2563eb !important;
}

/* ── Streamlit header — force light ── */
header[data-testid="stHeader"] {
  background: var(--surface) !important;
  border-bottom: 1px solid var(--b1) !important;
  box-shadow: none !important;
}
header[data-testid="stHeader"] * { color: var(--t2) !important; }

/* ── Toolbar buttons ── */
[data-testid="stToolbar"] button,
[data-testid="stAppDeployButton"] button {
  color: var(--t2) !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}
[data-testid="stToolbar"] button:hover {
  background: var(--surface-2) !important;
  transform: none !important;
}

/* ── 13. KEYFRAMES ──────────────────────────────────────────────────── */
@keyframes fadeUp {
  from { opacity:0; transform:translateY(10px); }
  to   { opacity:1; transform:translateY(0); }
}
@keyframes fadeIn {
  from { opacity:0; }
  to   { opacity:1; }
}
@keyframes slideRight {
  from { opacity:0; transform:translateX(-8px); }
  to   { opacity:1; transform:translateX(0); }
}
@keyframes shimmer {
  0%   { background-position:-200% 0; }
  100% { background-position:200% 0; }
}

/* ── 14. CUSTOM COMPONENTS ──────────────────────────────────────────── */

/* Hero */
.jh-hero {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 1.75rem;
  padding: 2.25rem 2.5rem;
  border: 1px solid var(--b1);
  border-radius: var(--r6);
  background: linear-gradient(135deg,rgba(37,99,235,.05) 0%,rgba(124,58,237,.04) 100%), var(--surface);
  box-shadow: var(--s2);
  animation: fadeUp var(--t3d) var(--ease) both;
  position: relative;
  overflow: hidden;
}
.jh-hero::before {
  content:'';
  position:absolute;
  width:400px; height:400px;
  top:-150px; right:-100px;
  background:radial-gradient(circle,rgba(37,99,235,.06),transparent 65%);
  pointer-events:none;
}
.jh-hero-copy {
  display:flex; flex-direction:column;
  justify-content:center; gap:.9rem;
  position:relative; z-index:1;
}
.jh-eyebrow {
  display:inline-flex; align-items:center;
  width:fit-content;
  height:24px; padding:0 12px;
  border-radius:var(--rf);
  background:var(--ps); border:1px solid var(--pm);
  color:var(--p); font-size:11px; font-weight:700;
  letter-spacing:.1em; text-transform:uppercase;
}
.jh-hero-title {
  font-family:var(--font-d);
  font-size:clamp(1.9rem,3.8vw,3rem);
  font-weight:800; line-height:1.05;
  letter-spacing:-.04em; color:var(--t1);
  background:linear-gradient(135deg,var(--slate-900) 0%,var(--blue-700) 55%,var(--violet-600) 100%);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}
.jh-hero-sub {
  font-size:15px; line-height:1.7; color:var(--t2); max-width:500px;
}
.jh-tags { display:flex; flex-wrap:wrap; gap:7px; }
.jh-tag {
  display:inline-flex; align-items:center;
  height:26px; padding:0 10px;
  border-radius:var(--rf); border:1px solid;
  font-size:12px; font-weight:600; white-space:nowrap;
}
.jh-tag-blue   { color:var(--p);  background:var(--ps);  border-color:var(--pm); }
.jh-tag-violet { color:var(--a);  background:var(--as);  border-color:var(--violet-100); }
.jh-tag-green  { color:var(--ok); background:var(--oks); border-color:var(--okm); }
.jh-tag-gray   { color:var(--t2); background:var(--surface-2); border-color:var(--b1); }
.jh-tag-amber  { color:var(--wn); background:var(--wns); border-color:var(--amber-100); }

/* Hero panel */
.jh-panel {
  display:flex; flex-direction:column; gap:10px;
  padding:1.25rem;
  border:1px solid var(--b1); border-radius:var(--r5);
  background:var(--surface); box-shadow:var(--s1);
  position:relative; z-index:1;
}
.jh-stat-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
.jh-stat {
  padding:12px;
  border-radius:var(--r4); border:1px solid var(--b1);
  background:var(--surface-2);
}
.jh-stat strong {
  display:block; font-family:var(--font-d);
  font-size:1.1rem; font-weight:800;
  color:var(--t1); letter-spacing:-.03em; margin-bottom:2px;
}
.jh-stat span { font-size:11px; color:var(--t3); line-height:1.4; }
.jh-panel-note {
  padding:10px 12px; border-radius:var(--r3);
  background:var(--ps); border:1px solid var(--pm);
  font-size:12px; color:var(--blue-700); line-height:1.55;
}

/* Section header */
.jh-section { display:flex; flex-direction:column; gap:5px; animation:fadeIn var(--t3d) var(--ease) both; }
.jh-label {
  display:inline-flex; align-items:center;
  width:fit-content; height:22px; padding:0 9px;
  border-radius:var(--rf); background:var(--surface-2);
  border:1px solid var(--b1);
  font-size:10.5px; font-weight:700;
  letter-spacing:.08em; text-transform:uppercase; color:var(--t3);
}
.jh-title {
  font-family:var(--font-d);
  font-size:clamp(1.2rem,2vw,1.65rem);
  font-weight:800; letter-spacing:-.03em;
  color:var(--t1); line-height:1.15;
}
.jh-copy { font-size:14px; color:var(--t2); line-height:1.65; max-width:580px; }

/* Feature grid (empty state) */
.jh-features {
  display:grid; grid-template-columns:repeat(4,1fr);
  gap:12px; margin-top:14px;
}
.jh-feature {
  display:flex; flex-direction:column; gap:10px;
  padding:18px 16px;
  border:1px solid var(--b1); border-radius:var(--r5);
  background:var(--surface); box-shadow:var(--s0);
  transition:transform var(--t2d) var(--ease),
             box-shadow var(--t2d) var(--ease),
             border-color var(--t2d) var(--ease);
  animation:fadeUp var(--t3d) var(--ease) both;
}
.jh-feature:nth-child(1){animation-delay:0ms}
.jh-feature:nth-child(2){animation-delay:60ms}
.jh-feature:nth-child(3){animation-delay:120ms}
.jh-feature:nth-child(4){animation-delay:180ms}
.jh-feature:hover {
  transform:translateY(-2px);
  box-shadow:var(--s2);
  border-color:var(--b2);
}
.jh-f-icon {
  display:flex; align-items:center; justify-content:center;
  width:36px; height:36px; border-radius:var(--r4);
  background:linear-gradient(135deg,var(--p),var(--a));
  color:#fff; font-size:14px; font-weight:800;
  font-family:var(--font-d); flex-shrink:0;
  box-shadow:0 4px 10px rgba(37,99,235,.22);
}
.jh-f-title { font-weight:700; font-size:14px; color:var(--t1); letter-spacing:-.01em; }
.jh-f-desc  { font-size:13px; color:var(--t2); line-height:1.55; }

/* Wizard stepper */
.jh-stepper {
  display:grid; grid-template-columns:repeat(4,1fr);
  gap:10px; margin:1.25rem 0;
}
.jh-step {
  display:flex; flex-direction:column; gap:7px;
  padding:13px 15px;
  border:1px solid var(--b1); border-radius:var(--r4);
  background:var(--surface);
  transition:all var(--t2d) var(--ease);
}
.jh-step--active {
  border-color:rgba(37,99,235,.35);
  background:linear-gradient(135deg,rgba(37,99,235,.04),rgba(124,58,237,.03));
  box-shadow:0 0 0 3px rgba(37,99,235,.08),var(--s1);
}
.jh-step--done {
  border-color:rgba(5,150,105,.25);
  background:linear-gradient(135deg,rgba(5,150,105,.04),rgba(5,150,105,.02));
}
.jh-step-num {
  display:inline-flex; align-items:center; justify-content:center;
  width:28px; height:28px; border-radius:var(--rf);
  font-size:12px; font-weight:800; font-family:var(--font-d);
  flex-shrink:0; transition:all var(--t2d) var(--ease);
}
.jh-step--pending .jh-step-num {
  background:var(--surface-2); border:1px solid var(--b1); color:var(--t3);
}
.jh-step--active .jh-step-num {
  background:linear-gradient(135deg,var(--p),var(--a));
  color:#fff; box-shadow:0 4px 12px rgba(37,99,235,.3);
}
.jh-step--done .jh-step-num {
  background:var(--oks); border:1px solid var(--okm); color:var(--ok);
}
.jh-step-lbl { font-size:13px; font-weight:700; color:var(--t1); line-height:1.2; }
.jh-step-desc { font-size:11.5px; color:var(--t3); line-height:1.4; }

/* Score & source badges */
.jh-score {
  display:inline-flex; align-items:center;
  height:24px; padding:0 9px;
  border-radius:var(--rf); border:1px solid;
  font-size:11.5px; font-weight:700; letter-spacing:-.01em;
}
.jh-score-hi { color:var(--okt); background:var(--oks); border-color:var(--okm); }
.jh-score-md { color:var(--wnt); background:var(--wns); border-color:var(--amber-100); }
.jh-score-lo { color:var(--t2); background:var(--surface-2); border-color:var(--b1); }

.jh-src {
  display:inline-flex; align-items:center;
  height:20px; padding:0 8px;
  border-radius:var(--rf);
  font-size:11px; font-weight:600; color:#fff;
}
.src-Remotive        {background:linear-gradient(135deg,#2563eb,#7c3aed)}
.src-Arbeitnow       {background:linear-gradient(135deg,#0ea5e9,#0284c7)}
.src-WeWorkRemotely  {background:linear-gradient(135deg,#059669,#047857)}
.src-Himalayas       {background:linear-gradient(135deg,#f59e0b,#d97706)}
.src-RemoteOK        {background:linear-gradient(135deg,#7c3aed,#6d28d9)}
.src-Jobicy          {background:linear-gradient(135deg,#14b8a6,#0d9488)}
.src-GetOnBoard      {background:linear-gradient(135deg,#10b981,#059669)}
.src-LatoJobs        {background:linear-gradient(135deg,#3b82f6,#2563eb)}
.src-PuenteTalent    {background:linear-gradient(135deg,#f59e0b,#d97706)}
.src-WorkingNomads   {background:linear-gradient(135deg,#6366f1,#4f46e5)}
.src-TheMuse         {background:linear-gradient(135deg,#ec4899,#db2777)}
.src-Remote-co       {background:linear-gradient(135deg,#059669,#047857)}
.src-Jobspresso      {background:linear-gradient(135deg,#ef4444,#dc2626)}
.src-JustJoin-it     {background:linear-gradient(135deg,#f97316,#ea580c)}
.src-AuthenticJobs   {background:linear-gradient(135deg,#8b5cf6,#7c3aed)}
.src-LinkedInBrowser {background:linear-gradient(135deg,#0a66c2,#004182)}
.src-BumeranBrowser  {background:linear-gradient(135deg,#f97316,#ea580c)}
.src-ComputrabajoBrowser{background:linear-gradient(135deg,#ef4444,#dc2626)}
.src-IndeedBrowser   {background:linear-gradient(135deg,#2557a7,#1d4ed8)}

/* Job card */
.jh-job {
  padding:18px 20px;
  border:1px solid var(--b1); border-radius:var(--r5);
  background:var(--surface); box-shadow:var(--s0);
  transition:box-shadow var(--t2d) var(--ease), border-color var(--t2d) var(--ease);
  animation:fadeUp var(--t2d) var(--ease) both;
}
.jh-job:hover { box-shadow:var(--s2); border-color:var(--b2); }
.jh-job-badges { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:10px; }
.jh-job-title {
  font-family:var(--font-d);
  font-size:16px; font-weight:700;
  color:var(--t1); letter-spacing:-.02em; line-height:1.3;
  margin-bottom:3px;
}
.jh-job-co { font-size:13.5px; color:var(--t2); }
.jh-job-summary {
  font-size:13.5px; color:var(--t2); line-height:1.65;
  margin-top:10px; padding-top:10px;
  border-top:1px solid var(--b1);
}
.jh-col-lbl {
  font-size:10.5px; font-weight:700; letter-spacing:.07em;
  text-transform:uppercase; color:var(--t3); margin-bottom:8px;
}
.jh-reason {
  display:flex; align-items:flex-start; gap:6px;
  font-size:13px; color:var(--t2); line-height:1.5; margin-bottom:5px;
}
.jh-reason::before { content:'✓'; color:var(--ok); font-weight:800; font-size:11px; margin-top:1px; flex-shrink:0; }
.jh-skill { color:var(--t2); }
.jh-skill::before { content:'→'; color:var(--wn); font-weight:700; font-size:11px; margin-top:1px; flex-shrink:0; }

/* Cover letter */
.jh-letter {
  background:var(--surface-2); border:1px solid var(--b1);
  border-radius:var(--r4);
  padding:18px 20px;
  font-family:Georgia,'Times New Roman',serif;
  font-size:14px; line-height:1.75;
  color:var(--t1); white-space:pre-wrap;
  max-height:360px; overflow-y:auto;
}
.jh-letter::-webkit-scrollbar{width:5px}
.jh-letter::-webkit-scrollbar-track{background:transparent}
.jh-letter::-webkit-scrollbar-thumb{background:var(--b2);border-radius:var(--rf)}

/* Metrics row */
.jh-metrics {
  display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:1.5rem;
}
.jh-metric {
  padding:18px 20px;
  border:1px solid var(--b1); border-radius:var(--r5);
  background:var(--surface); box-shadow:var(--s1);
}
.jh-metric-val {
  font-family:var(--font-d); font-size:2.1rem; font-weight:800;
  letter-spacing:-.04em; color:var(--t1); line-height:1;
}
.jh-metric-lbl {
  font-size:11px; font-weight:700; text-transform:uppercase;
  letter-spacing:.07em; color:var(--t3); margin-top:6px;
}

/* Cancel button (wizard close) */
div[data-testid="stMarkdownContainer"] .cancel-marker { display:none; }
[data-testid="stMarkdownContainer"]:has(.cancel-marker) ~ [data-testid="stButton"] > button {
  background:var(--ers) !important; color:var(--er) !important;
  border:1px solid var(--red-100) !important; box-shadow:none !important;
}
[data-testid="stMarkdownContainer"]:has(.cancel-marker) ~ [data-testid="stButton"] > button:hover {
  background:var(--red-100) !important; border-color:var(--er) !important; transform:none !important;
}

/* Stop buttons durante búsqueda */
div[data-testid="stMarkdownContainer"] .stop-marker { display:none; }
[data-testid="stMarkdownContainer"]:has(.stop-marker) ~ [data-testid="stButton"] > button {
  background: #dc2626 !important;
  color: #ffffff !important;
  border: 1px solid #dc2626 !important;
  box-shadow: 0 4px 12px rgba(220,38,38,.28) !important;
  font-size: 15px !important;
  font-weight: 700 !important;
  padding: .75rem 1.5rem !important;
  border-radius: var(--r3) !important;
}
[data-testid="stMarkdownContainer"]:has(.stop-marker) ~ [data-testid="stButton"] > button:hover {
  background: #b91c1c !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 8px 20px rgba(220,38,38,.36) !important;
}

div[data-testid="stMarkdownContainer"] .config-marker { display:none; }
[data-testid="stMarkdownContainer"]:has(.config-marker) ~ [data-testid="stButton"] > button {
  background: var(--p) !important;
  color: #ffffff !important;
  border: 1px solid transparent !important;
  box-shadow: var(--sp) !important;
  font-size: 15px !important;
  font-weight: 700 !important;
  padding: .75rem 1.5rem !important;
  border-radius: var(--r3) !important;
}
[data-testid="stMarkdownContainer"]:has(.config-marker) ~ [data-testid="stButton"] > button:hover {
  background: var(--ph) !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 12px 28px rgba(37,99,235,.34) !important;
}

/* ── 15. RESPONSIVE ─────────────────────────────────────────────────── */
@media(max-width:1024px) {
  .jh-hero { grid-template-columns:1fr; }
  .jh-features { grid-template-columns:repeat(2,1fr); }
  .jh-metrics { grid-template-columns:repeat(2,1fr); }
}
@media(max-width:768px) {
  div.block-container,div[data-testid="stMainBlockContainer"] {
    padding:1rem 1rem 3rem !important;
  }
  .jh-hero { padding:1.5rem; }
  .jh-stepper { grid-template-columns:repeat(2,1fr); }
  .jh-hero-title { font-size:clamp(1.6rem,6vw,2.2rem); }
}
@media(max-width:640px) {
  .jh-features,.jh-metrics,.jh-stepper { grid-template-columns:1fr; }
}

/* ── 16. DARK MODE (html[data-theme="dark"]) ─────────────────────────────── */
html[data-theme="dark"] {
  color-scheme: dark only !important;
  forced-color-adjust: none !important;

  /* Design tokens redefinidos para dark */
  --bg:        #0f172a;
  --surface:   #1e293b;
  --surface-2: #263548;
  --surface-3: #304562;

  --t1: #f1f5f9;
  --t2: #cbd5e1;
  --t3: #94a3b8;
  --ti: #0f172a;

  --b1: #2d3f55;
  --b2: #3d5470;

  --ps:  #1e3a8a;  --pm: #1e40af;
  --as:  #2e1065;
  --oks: #052e16;  --okm: #14532d;
  --wns: #422006;
  --ers: #450a0a;

  --s0: 0 1px 2px rgba(0,0,0,.5);
  --s1: 0 1px 3px rgba(0,0,0,.6),0 1px 2px rgba(0,0,0,.4);
  --s2: 0 4px 8px rgba(0,0,0,.55),0 2px 4px rgba(0,0,0,.35);
  --s3: 0 12px 24px rgba(0,0,0,.6),0 4px 8px rgba(0,0,0,.4);
  --s4: 0 24px 48px rgba(0,0,0,.7),0 8px 16px rgba(0,0,0,.45);
  --sp: 0 8px 24px rgba(37,99,235,.5);

  /* Variables internas de Streamlit */
  --text-color: #f1f5f9 !important;
  --background-color: #0f172a !important;
  --secondary-background-color: #1e293b !important;
  --primary-color: #3b82f6 !important;
}

/* ── Fondos principales ─────────────────────────────────────────────────── */
html[data-theme="dark"],
html[data-theme="dark"] body,
html[data-theme="dark"] .stApp,
html[data-theme="dark"] [data-testid="stAppViewContainer"],
html[data-theme="dark"] [data-testid="stMain"],
html[data-theme="dark"] [data-testid="stMainBlockContainer"],
html[data-theme="dark"] div.block-container {
  background: var(--bg) !important;
  color: var(--t1) !important;
}

/* ── Texto genérico: hex directo para no depender de var() ──────────────── */
/* #f1f5f9 = --t1 (text primary)  #cbd5e1 = --t2  #94a3b8 = --t3           */
html[data-theme="dark"] h1,
html[data-theme="dark"] h2,
html[data-theme="dark"] h3,
html[data-theme="dark"] h4,
html[data-theme="dark"] h5,
html[data-theme="dark"] h6 { color: #f1f5f9 !important; }

html[data-theme="dark"] p   { color: #cbd5e1 !important; }
html[data-theme="dark"] li  { color: #cbd5e1 !important; }
html[data-theme="dark"] span { color: inherit !important; }
html[data-theme="dark"] label { color: #cbd5e1 !important; }

/* Streamlit markdown wrapper */
html[data-theme="dark"] [data-testid="stMarkdownContainer"] h1,
html[data-theme="dark"] [data-testid="stMarkdownContainer"] h2,
html[data-theme="dark"] [data-testid="stMarkdownContainer"] h3,
html[data-theme="dark"] [data-testid="stMarkdownContainer"] h4 { color: #f1f5f9 !important; }
html[data-theme="dark"] [data-testid="stMarkdownContainer"] p  { color: #cbd5e1 !important; }
html[data-theme="dark"] [data-testid="stMarkdownContainer"] li { color: #cbd5e1 !important; }
html[data-theme="dark"] [data-testid="stMarkdownContainer"] strong,
html[data-theme="dark"] [data-testid="stMarkdownContainer"] b  { color: #f1f5f9 !important; }
html[data-theme="dark"] [data-testid="stMarkdownContainer"] span { color: inherit !important; }

/* Widget labels (todos los widgets nativos de Streamlit) */
html[data-theme="dark"] [data-testid="stWidgetLabel"] p,
html[data-theme="dark"] [data-testid="stWidgetLabel"] span,
html[data-theme="dark"] [data-testid="stWidgetLabel"] label,
html[data-theme="dark"] [data-testid="stWidgetLabel"] { color: #cbd5e1 !important; }

/* Caption / small text */
html[data-theme="dark"] [data-testid="stCaptionContainer"] p,
html[data-theme="dark"] [data-testid="stCaptionContainer"],
html[data-theme="dark"] small { color: #94a3b8 !important; }

/* Streamlit "st.markdown" usado como párrafo suelto */
html[data-theme="dark"] [data-testid="stText"] { color: #cbd5e1 !important; }

/* Texto dentro de expanders */
html[data-theme="dark"] [data-testid="stExpanderDetails"] p,
html[data-theme="dark"] [data-testid="stExpanderDetails"] span,
html[data-theme="dark"] [data-testid="stExpanderDetails"] label { color: #cbd5e1 !important; }
html[data-theme="dark"] [data-testid="stExpanderDetails"] h3,
html[data-theme="dark"] [data-testid="stExpanderDetails"] h4 { color: #f1f5f9 !important; }

/* Checkbox y radio labels */
html[data-theme="dark"] [data-testid="stCheckbox"] p,
html[data-theme="dark"] [data-testid="stRadio"] p,
html[data-theme="dark"] [data-testid="stCheckbox"] span,
html[data-theme="dark"] [data-testid="stRadio"] span { color: #cbd5e1 !important; }

/* Número de pasos, tooltips y helper texts */
html[data-theme="dark"] [data-testid="stTooltipIcon"] { color: #94a3b8 !important; }

/* ── Inputs: text, number, textarea ────────────────────────────────────── */
html[data-theme="dark"] input,
html[data-theme="dark"] textarea,
html[data-theme="dark"] [data-baseweb="input"] input,
html[data-theme="dark"] [data-baseweb="textarea"] textarea {
  background: var(--surface-2) !important;
  color: var(--t1) !important;
  border-color: var(--b2) !important;
}
html[data-theme="dark"] [data-baseweb="input"],
html[data-theme="dark"] [data-baseweb="base-input"],
html[data-theme="dark"] [data-baseweb="textarea"] {
  background: var(--surface-2) !important;
  border-color: var(--b2) !important;
}
html[data-theme="dark"] input::placeholder,
html[data-theme="dark"] textarea::placeholder { color: var(--t3) !important; }

/* ── Select / dropdown ──────────────────────────────────────────────────── */
html[data-theme="dark"] [data-baseweb="select"] > div,
html[data-theme="dark"] [data-baseweb="select"] [role="combobox"] {
  background: var(--surface-2) !important;
  border-color: var(--b2) !important;
  color: var(--t1) !important;
}
html[data-theme="dark"] [data-baseweb="select"] [data-testid="stSelectboxVirtualDropdown"],
html[data-theme="dark"] [data-baseweb="popover"],
html[data-theme="dark"] [data-baseweb="menu"] {
  background: var(--surface) !important;
  border: 1px solid var(--b2) !important;
}
html[data-theme="dark"] [data-baseweb="option"] {
  background: var(--surface) !important;
  color: var(--t1) !important;
}
html[data-theme="dark"] [data-baseweb="option"]:hover,
html[data-theme="dark"] [data-baseweb="option"][aria-selected="true"] {
  background: var(--surface-2) !important;
}
html[data-theme="dark"] [data-baseweb="tag"] {
  background: var(--pm) !important; color: #bfdbfe !important;
}

/* ── Checkboxes / radios ────────────────────────────────────────────────── */
html[data-theme="dark"] [data-testid="stCheckbox"] span,
html[data-theme="dark"] [data-testid="stRadio"] span { color: var(--t1) !important; }
html[data-theme="dark"] [data-baseweb="checkbox"] [type="checkbox"] + span,
html[data-theme="dark"] [data-baseweb="radio"] [type="radio"] + span {
  border-color: var(--b2) !important;
  background: var(--surface-2) !important;
}

/* ── Buttons (Streamlit nativos) ────────────────────────────────────────── */
html[data-theme="dark"] [data-testid="stBaseButton-secondary"],
html[data-theme="dark"] button[kind="secondary"] {
  background: var(--surface-2) !important;
  border-color: var(--b2) !important;
  color: var(--t1) !important;
}
html[data-theme="dark"] [data-testid="stBaseButton-secondary"]:hover {
  background: var(--surface-3) !important;
  border-color: var(--b2) !important;
}
html[data-theme="dark"] [data-testid="stToolbar"] button,
html[data-theme="dark"] [data-testid="stAppDeployButton"] button {
  color: var(--t2) !important; background: transparent !important;
}

/* ── Tabs ───────────────────────────────────────────────────────────────── */
html[data-theme="dark"] [data-testid="stTabs"] [role="tablist"] {
  border-bottom-color: var(--b1) !important;
}
html[data-theme="dark"] [data-testid="stTabs"] [role="tab"] {
  color: var(--t3) !important;
}
html[data-theme="dark"] [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
  color: var(--p) !important;
  border-bottom-color: var(--p) !important;
}
html[data-theme="dark"] div[data-testid="stTabs"] [role="tabpanel"] {
  background: transparent !important;
}

/* ── Metrics ────────────────────────────────────────────────────────────── */
html[data-theme="dark"] [data-testid="stMetric"] label,
html[data-theme="dark"] [data-testid="stMetricLabel"] { color: var(--t3) !important; }
html[data-theme="dark"] [data-testid="stMetricValue"],
html[data-theme="dark"] [data-testid="stMetricValue"] * { color: var(--t1) !important; }

/* ── Expander ───────────────────────────────────────────────────────────── */
html[data-theme="dark"] [data-testid="stExpander"],
html[data-theme="dark"] div[data-testid="stExpander"] summary {
  background: var(--surface) !important;
  border-color: var(--b1) !important;
}
html[data-theme="dark"] div[data-testid="stExpander"] summary span { color: var(--t1) !important; }
html[data-theme="dark"] div[data-testid="stExpander"] div[data-testid="stExpanderDetails"] {
  background: var(--surface) !important;
}

/* ── Alerts / info boxes ────────────────────────────────────────────────── */
html[data-theme="dark"] [data-testid="stAlert"],
html[data-theme="dark"] [data-testid="stInfo"],
html[data-theme="dark"] [data-testid="stSuccess"],
html[data-theme="dark"] [data-testid="stWarning"],
html[data-theme="dark"] [data-testid="stError"] {
  background: var(--surface-2) !important;
  border-color: var(--b2) !important;
  color: var(--t1) !important;
}

/* ── Header de Streamlit ────────────────────────────────────────────────── */
html[data-theme="dark"] header[data-testid="stHeader"] {
  background: var(--surface) !important;
  border-bottom: 1px solid var(--b1) !important;
}
html[data-theme="dark"] header[data-testid="stHeader"] * { color: var(--t2) !important; }

/* ── Code blocks ────────────────────────────────────────────────────────── */
html[data-theme="dark"] code {
  background: var(--surface-2) !important;
  color: #7dd3fc !important;
}

/* ── Separadores ────────────────────────────────────────────────────────── */
html[data-theme="dark"] hr { border-color: var(--b1) !important; }

/* ── Componentes custom del app (JH) ────────────────────────────────────── */
html[data-theme="dark"] .jh-hero {
  background: linear-gradient(135deg,rgba(37,99,235,.10) 0%,rgba(124,58,237,.09) 100%), var(--surface) !important;
  border-color: var(--b1) !important;
}
html[data-theme="dark"] .jh-card {
  background: var(--surface) !important;
  border-color: var(--b1) !important;
}
html[data-theme="dark"] .jh-card:hover { border-color: var(--b2) !important; }
html[data-theme="dark"] .jh-stepper { background: var(--surface-2) !important; }
html[data-theme="dark"] .jh-step-dot { border-color: var(--b2) !important; }
html[data-theme="dark"] .jh-step-label { color: var(--t3) !important; }
html[data-theme="dark"] .jh-step-active .jh-step-label { color: var(--t1) !important; }
html[data-theme="dark"] .jh-panel { background: var(--surface) !important; border-color: var(--b1) !important; }
html[data-theme="dark"] .jh-panel-note { background: var(--surface-2) !important; border-color: var(--b1) !important; color: var(--t2) !important; }
html[data-theme="dark"] .jh-feature { background: var(--surface) !important; border-color: var(--b1) !important; }
html[data-theme="dark"] .jh-f-icon { background: var(--pm) !important; color: #bfdbfe !important; }
html[data-theme="dark"] .jh-f-title { color: var(--t1) !important; }
html[data-theme="dark"] .jh-f-desc  { color: var(--t2) !important; }
html[data-theme="dark"] .jh-tag { opacity: .85; }
html[data-theme="dark"] .jh-tag-blue   { background: #1e3a8a !important; color: #bfdbfe !important; }
html[data-theme="dark"] .jh-tag-violet { background: #2e1065 !important; color: #ddd6fe !important; }
html[data-theme="dark"] .jh-tag-green  { background: #052e16 !important; color: #6ee7b7 !important; }
html[data-theme="dark"] .jh-tag-gray   { background: var(--surface-3) !important; color: var(--t2) !important; }
html[data-theme="dark"] .jh-stat strong { color: var(--t1) !important; }
html[data-theme="dark"] .jh-stat span   { color: var(--t3) !important; }
html[data-theme="dark"] .jh-badge-ok  { background: #052e16 !important; color: #6ee7b7 !important; }
html[data-theme="dark"] .jh-badge-wn  { background: #422006 !important; color: #fcd34d !important; }
html[data-theme="dark"] .jh-badge-er  { background: #450a0a !important; color: #fca5a5 !important; }
html[data-theme="dark"] .jh-score     { background: var(--surface-3) !important; color: var(--t1) !important; }
html[data-theme="dark"] .jh-why-title { color: var(--t2) !important; }
html[data-theme="dark"] .jh-label     { color: var(--t3) !important; }
html[data-theme="dark"] .jh-title     { color: var(--t1) !important; }
html[data-theme="dark"] .jh-copy      { color: var(--t2) !important; }
</style>
""", unsafe_allow_html=True)

# ─── Session state ────────────────────────────────────────────────────────────
# Nada se guarda en disco: cada sesión de navegador empieza limpia.
# Los datos persisten mientras la pestaña esté abierta.
_defaults = {
    "show_dialog":        False,
    "config_step":        1,
    "cv_analyzed":        False,
    "run_search":         False,
    "search_done":        False,
    "gemini_key":         "",
    "selected_model":     "models/gemini-3.1-flash-lite",
    "send_email":         False,
    "email_sender":       "",
    "email_password_raw": "",
    "email_recipient":    "",
    "keywords_list":      [],
    "kw_options":         [],
    "min_score":          65,
    "only_remote":        False,
    "use_max_results":    False,
    "max_results_limit":  100,
    "use_remotive":       True,
    "use_arbeitnow":      True,
    "use_wwr":            True,
    "use_himalayas":      True,
    "use_remoteok":       True,
    "use_jobicy":         True,
    "use_getonboard":     True,
    "use_puentetalent":   True,
    "use_latojobs":       True,
    # Portales con login — solo se usan cuando IS_CLOUD es False
    "use_linkedin_browser":      False,
    "use_bumeran_browser":       False,
    "use_computrabajo_browser":  False,
    "use_indeed_browser":        False,
    "browser_profile_dir":       str(Path(".browser_profiles").resolve()),
    "use_workingnomads":  True,
    "use_themuse":        True,
    "use_remoteco":       True,
    "use_jobspresso":     True,
    "use_justjoinit":     False,
    "use_authenticjobs":  True,
    "result_page":        0,
    "result_page_all":    0,
    "candidate_profile":  "",
    "scored_jobs":        [],   # persiste entre reruns de paginación
    "top_matches":        [],   # idem
    "min_score_last":     65,   # score usado en la última búsqueda (para métricas)
    # ── Preferencias visuales ─────────────────────────────────────────────
    "dark_mode":          False,  # False = light (default), True = dark
    "lang":               "es",   # "es" = Español (default), "en" = English
    # ── Control de búsqueda en curso ──────────────────────────────────
    "is_searching":       False,  # True mientras la búsqueda corre
    "cancel_search":      False,  # señal para abortar entre plataformas
    "cancel_and_config":  False,  # abortar Y abrir wizard
    # Estado interno del scraping por pasos (permite cancelar entre plataformas)
    "_scrape_phase":      "idle",   # idle | scraping | scoring | letters | done
    "_scrape_idx":        0,        # índice de plataforma actual
    "_scrape_jobs":       [],       # acumulador de trabajos scrapeados
    "_scrape_seen":       set(),    # deduplicación entre plataformas
    "_scrape_cfg":        {},       # config snapshot al iniciar búsqueda
}
for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─── Sincronizar query params → preferencias visuales ────────────────────────
_qp = st.query_params
if "dark" in _qp:
    st.session_state.dark_mode = (_qp.get("dark", "0") == "1")
if "lang" in _qp:
    _lv = _qp.get("lang", "es")
    if _lv in ("es", "en"):
        st.session_state.lang = _lv

# ─── Traducciones / Translations ─────────────────────────────────────────────
TRANSLATIONS: dict[str, dict[str, str]] = {
    "es": {
        # Hero — estado inicial
        "hero_eyebrow_search":  "Búsqueda de empleo con IA",
        "hero_title_search":    "Encontrá el trabajo que realmente encaja.",
        "hero_sub_search":      "Job Hunter reúne ofertas de 15+ portales, las puntúa según tu perfil y genera cartas de presentación listas para enviar.",
        "hero_note_search":     "Toda la lógica corre en tu máquina. Tus credenciales nunca salen del navegador.",
        "hero_tag_scoring":     "Scoring con IA",
        "hero_tag_multi":       "Multi-source",
        "hero_tag_letters":     "Cover letters",
        "hero_tag_local":       "Local-first",
        "hero_stat_sources":    "fuentes activas",
        "hero_stat_score":      "score por oferta",
        "hero_stat_ai":         "cover letters",
        "hero_stat_time":       "por búsqueda",
        # Hero — resultados
        "hero_eyebrow_results": "Panel de resultados",
        "hero_title_results":   "Tus oportunidades, priorizadas.",
        "hero_sub_results":     "La IA evaluó cada oferta contra tu perfil. Las recomendadas están en la pestaña de abajo, ordenadas por score.",
        "hero_note_results":    "Resultados listos. Refiná las búsquedas o exportá las cartas.",
        "hero_tag_done":        "Búsqueda completada",
        "hero_stat_analyzed":   "analizadas",
        "hero_stat_rec":        "recomendadas",
        "hero_stat_best":       "mejor score",
        "hero_stat_threshold":  "umbral",
        # Empty state
        "empty_label":  "Cómo funciona",
        "empty_title":  "Un flujo de 4 pasos, sin ruido visual.",
        "empty_copy":   "Configurás una vez, lanzás la búsqueda y recibís resultados ordenados por relevancia con cartas listas para enviar.",
        "feat1_title":  "Descubrí",
        "feat1_desc":   "Remotive, Get on Board, Himalayas, LatoJobs, WeWorkRemotely y 10+ fuentes más en una sola búsqueda.",
        "feat2_title":  "Priorizá",
        "feat2_desc":   "La IA puntúa cada oferta del 0 al 100 comparando el job description con tu perfil real. Sin inflado de seniority.",
        "feat3_title":  "Redactá",
        "feat3_desc":   "Genera una cover letter única por oferta, en el idioma del aviso, con referencias específicas al puesto.",
        "feat4_title":  "Actuá",
        "feat4_desc":   "Descargá las cartas individualmente, exportá todo como JSON o recibí un digest por email.",
        # Botones de acción
        "searching_notice": "La búsqueda está en curso — podés detenerla en cualquier momento.",
        "btn_stop":          "Detener",
        "btn_stop_config":   "Detener & Configurar",
        "btn_new_search":    "Nueva búsqueda",
        "btn_config_search": "Configurar búsqueda",
        "search_time_hint":  "Una búsqueda completa suele tardar entre 6 y 8 minutos.",
        # Resultados
        "tab_recommended":       "Recomendadas",
        "tab_all":               "Todas",
        "metric_analyzed":       "Analizadas",
        "metric_recommended":    "Recomendadas",
        "metric_best":           "Mejor score",
        "metric_excellent":      "Excelentes 80+",
        "showing":               "Mostrando",
        "of":                    "de",
        "offers":                "ofertas",
        "no_recommended":        "Ninguna oferta superó el puntaje mínimo de {score}. Probá bajar el valor en la configuración.",
        "all_tab_caption":       "Ordenadas de mayor a menor puntaje.",
        "btn_prev":              "← Anterior",
        "btn_next":              "Siguiente →",
        "page_of":               "Página {page} de {pages}",
        "btn_download_json":     "⬇ Descargar resultados completos (JSON)",
        "why_fits":              "Por qué encaja",
        "what_missing":          "Lo que podría faltar",
        "no_reasons":            "Sin razones calculadas.",
        "no_missing":            "Sin faltantes críticos.",
        "cover_letter_expander": "Carta de presentación generada",
        "btn_download_letter":   "Descargar carta (.txt)",
        "offer_link":            "Ver oferta →",
        "remote_tag":            "Remota",
        "best_so_far":           "Mejores hasta ahora",
        # Wizard
        "wiz_label":   "Configuración",
        "wiz_title":   "Preparar búsqueda",
        "wiz_copy":    "Completá los 4 pasos para lanzar tu búsqueda personalizada.",
        "wiz_close":   "Cerrar",
        "step1_lbl":   "Credenciales",  "step1_desc": "API key y email",
        "step2_lbl":   "Tu CV",         "step2_desc": "Importá tu perfil",
        "step3_lbl":   "Búsqueda",      "step3_desc": "Fuentes y keywords",
        "step4_lbl":   "Perfil",        "step4_desc": "Texto para la IA",
        # Paso 1
        "step1_header":       "**🔑 Acceso a la IA**",
        "step1_gemini_help":  "¿Cómo obtengo la API key de Gemini?",
        "step1_key_label":    "API Key de Gemini",
        "step1_model_label":  "Modelo de IA",
        "step1_email_chk":    "Recibir resumen por email al terminar",
        "step1_email_help":   "¿Cómo obtengo la contraseña de app de Gmail?",
        "step1_gmail_label":  "Tu Gmail",
        "step1_recip_label":  "Email destinatario",
        "step1_pass_label":   "Contraseña de app (16 caracteres)",
        "btn_next_arrow":     "Siguiente →",
        "err_key":            "API key inválida.",
        "err_email":          "Email de envío inválido.",
        "err_pass":           "Contraseña de app: 16 caracteres.",
        "err_recip":          "Email destinatario inválido.",
        # Paso 2
        "step2_header":    "**📄 Subí tu CV**",
        "step2_caption":   "La IA extrae keywords y arma tu perfil automáticamente. Podés editarlos después o saltear este paso.",
        "step2_file":      "CV (PDF, DOCX o TXT)",
        "step2_analyze":   "🤖 Analizar CV con IA",
        "step2_spinning":  "Analizando tu CV…",
        "step2_extracted": "**📋 Extraído de tu CV — revisá antes de continuar:**",
        "step2_profile_prefix": "Perfil: ",
        "btn_back":        "← Atrás",
        "toast_cv_ok":     "✅ {n} keywords extraídas. Revisalas en el paso siguiente.",
        "toast_cv_err":    "No se pudo analizar el CV. Continuá y completá los datos a mano.",
        # Paso 3
        "step3_header":        "**🔍 Keywords de búsqueda**",
        "step3_kw_ph":         "Tus keywords — × para quitar",
        "step3_add_ph":        "Agregar keyword...",
        "step3_add_btn":       "+ Agregar",
        "step3_params":        "**⚙️ Parámetros**",
        "step3_remote_chk":    "Solo ofertas remotas",
        "step3_remote_help":   "Activa esta opción solo si tu CV especifica preferencia remota. Desactivado por defecto para no perder ofertas híbridas o presenciales.",
        "step3_score_label":   "Puntaje mínimo para 'Recomendadas' y cartas",
        "step3_score_help":    "Umbral para la pestaña 'Recomendadas' y generación de cartas. Las ofertas por debajo del umbral siguen visibles en 'Todas'.",
        "step3_sources":       "**Fuentes de búsqueda**",
        "step3_global":        "🌍 Remoto global",
        "step3_latam":         "🌎 Latinoamérica",
        "step3_login":         "🔐 Login requerido (beta)",
        "step3_browser_dir":   "Directorio de sesión del navegador",
        "step3_browser_help":  "Usá un perfil persistente creado con `python browser_login.py <portal>`.",
        "step3_browser_note":  "Beta: estas fuentes leen vacantes desde una sesión real guardada en Chromium. No automatizan postulaciones.",
        "step3_us":            "🇺🇸 EEUU / Anglófono",
        "step3_eu":            "🇪🇺 Europa",
        "step3_other":         "📌 Otros",
        "step3_limit_chk":     "Limitar cantidad de ofertas a analizar",
        "step3_limit_help":    "Útil para pruebas rápidas o para ahorrar cuota de IA.",
        "step3_limit_label":   "Máximo de ofertas",
        "toast_no_kw":         "Agregá al menos una keyword.",
        "toast_no_src":        "Seleccioná al menos una fuente.",
        # Paso 4
        "step4_header":    "**👤 Tu perfil profesional**",
        "step4_caption":   "La IA usa este texto para evaluar qué tan bien encaja cada oferta con vos.",
        "step4_ph":        "Rol buscado, stack técnico, experiencia, idiomas...",
        "step4_warning":   "El perfil está vacío. Sin un perfil el scoring de IA no tiene base para evaluar las ofertas — todos los puntajes serán bajos o arbitrarios. Completá el texto o volvé al paso anterior para analizar tu CV.",
        "btn_start":       "🚀 Iniciar búsqueda",
        # Validate config
        "val_key":         "API key de Gemini inválida.",
        "val_email":       "Email de envío inválido.",
        "val_pass":        "La contraseña de app debe tener 16 caracteres.",
        "val_recip":       "Email destinatario inválido.",
        "val_no_kw":       "Agregá al menos una keyword.",
        "val_no_src":      "Seleccioná al menos una fuente.",
        # Workflow
        "wf_step_label":   "Paso {n}  ·  {title}",
        "wf_step1_title":  "Buscar ofertas",
        "wf_step2_title":  "Analizar con IA",
        "wf_step3_title":  "Generar cartas",
        "wf_step4_title":  "Enviar resumen por email",
        "wf_starting":     "Iniciando...",
        "wf_searching":    "Buscando en **{platform}**...",
        "wf_stopped":      "⏹️ Búsqueda detenida por el usuario tras {n} fuente(s) — {jobs} ofertas encontradas hasta ahora.",
        "wf_found":        "✅ **{jobs} ofertas únicas** encontradas — {time}",
        "wf_no_jobs":      "No se encontraron ofertas para analizar.",
        "wf_scoring":      "Analizando **{i}/{n}**: {title} @ {company}",
        "wf_quota":        "Se agotó la cuota diaria de Gemini. Se analizaron {i} de {n} ofertas.",
        "wf_scored":       "✅ **{top} recomendadas** de {total} analizadas — {time}",
        "wf_letter":       "Generando carta **{i}/{n}** — {title}",
        "wf_letter_1":     "carta generada",
        "wf_letter_n":     "cartas generadas",
        "wf_email_send":   "Enviando resumen a {recipient}...",
        "wf_email_ok":     "✅ Resumen enviado a **{recipient}**.",
        "wf_email_err":    "No se pudo enviar el email: {error}",
        "wf_src_prog":     "{done}/{total} fuentes{eta}",
        "wf_ai_prog":      "{done}/{total} analizadas{eta}",
        "wf_let_prog":     "{done}/{total} cartas{eta}",
        "wf_eta":          "  ·  ~{time} restantes",
        "wf_err_platform": "⚠️ Error en {platform}: {error}",
        "wf_best_label":   "Mejores hasta ahora",
    },
    "en": {
        # Hero — initial state
        "hero_eyebrow_search":  "AI-Powered Job Search",
        "hero_title_search":    "Find the job that truly fits.",
        "hero_sub_search":      "Job Hunter gathers listings from 15+ portals, scores them against your profile, and generates ready-to-send cover letters.",
        "hero_note_search":     "All logic runs on your machine. Your credentials never leave the browser.",
        "hero_tag_scoring":     "AI Scoring",
        "hero_tag_multi":       "Multi-source",
        "hero_tag_letters":     "Cover letters",
        "hero_tag_local":       "Local-first",
        "hero_stat_sources":    "active sources",
        "hero_stat_score":      "score per listing",
        "hero_stat_ai":         "cover letters",
        "hero_stat_time":       "per search",
        # Hero — results
        "hero_eyebrow_results": "Results Dashboard",
        "hero_title_results":   "Your opportunities, prioritized.",
        "hero_sub_results":     "The AI evaluated each listing against your profile. Recommended ones are in the tab below, sorted by score.",
        "hero_note_results":    "Results ready. Refine the search or export the letters.",
        "hero_tag_done":        "Search completed",
        "hero_stat_analyzed":   "analyzed",
        "hero_stat_rec":        "recommended",
        "hero_stat_best":       "best score",
        "hero_stat_threshold":  "threshold",
        # Empty state
        "empty_label":  "How it works",
        "empty_title":  "A 4-step flow, no visual noise.",
        "empty_copy":   "Configure once, launch the search, and receive results sorted by relevance with letters ready to send.",
        "feat1_title":  "Discover",
        "feat1_desc":   "Remotive, Get on Board, Himalayas, LatoJobs, WeWorkRemotely and 10+ more sources in a single search.",
        "feat2_title":  "Prioritize",
        "feat2_desc":   "The AI scores each listing from 0 to 100, comparing the job description with your real profile. No seniority inflation.",
        "feat3_title":  "Write",
        "feat3_desc":   "Generates a unique cover letter per listing, in the language of the ad, with specific references to the role.",
        "feat4_title":  "Act",
        "feat4_desc":   "Download letters individually, export everything as JSON, or receive a digest by email.",
        # Action buttons
        "searching_notice": "Search in progress — you can stop it at any time.",
        "btn_stop":          "Stop",
        "btn_stop_config":   "Stop & Configure",
        "btn_new_search":    "New search",
        "btn_config_search": "Configure search",
        "search_time_hint":  "A full search typically takes 6 to 8 minutes.",
        # Results
        "tab_recommended":       "Recommended",
        "tab_all":               "All",
        "metric_analyzed":       "Analyzed",
        "metric_recommended":    "Recommended",
        "metric_best":           "Best score",
        "metric_excellent":      "Excellent 80+",
        "showing":               "Showing",
        "of":                    "of",
        "offers":                "listings",
        "no_recommended":        "No listing exceeded the minimum score of {score}. Try lowering the value in settings.",
        "all_tab_caption":       "Sorted from highest to lowest score.",
        "btn_prev":              "← Previous",
        "btn_next":              "Next →",
        "page_of":               "Page {page} of {pages}",
        "btn_download_json":     "⬇ Download full results (JSON)",
        "why_fits":              "Why it fits",
        "what_missing":          "What might be missing",
        "no_reasons":            "No reasons calculated.",
        "no_missing":            "No critical gaps.",
        "cover_letter_expander": "Generated cover letter",
        "btn_download_letter":   "Download letter (.txt)",
        "offer_link":            "View listing →",
        "remote_tag":            "Remote",
        "best_so_far":           "Best so far",
        # Wizard
        "wiz_label":   "Setup",
        "wiz_title":   "Prepare search",
        "wiz_copy":    "Complete the 4 steps to launch your personalized search.",
        "wiz_close":   "Close",
        "step1_lbl":   "Credentials",   "step1_desc": "API key & email",
        "step2_lbl":   "Your CV",       "step2_desc": "Import your profile",
        "step3_lbl":   "Search",        "step3_desc": "Sources & keywords",
        "step4_lbl":   "Profile",       "step4_desc": "Text for the AI",
        # Step 1
        "step1_header":       "**🔑 AI Access**",
        "step1_gemini_help":  "How do I get the Gemini API key?",
        "step1_key_label":    "Gemini API Key",
        "step1_model_label":  "AI Model",
        "step1_email_chk":    "Receive summary by email when done",
        "step1_email_help":   "How do I get the Gmail app password?",
        "step1_gmail_label":  "Your Gmail",
        "step1_recip_label":  "Recipient email",
        "step1_pass_label":   "App password (16 characters)",
        "btn_next_arrow":     "Next →",
        "err_key":            "Invalid API key.",
        "err_email":          "Invalid sender email.",
        "err_pass":           "App password: 16 characters.",
        "err_recip":          "Invalid recipient email.",
        # Step 2
        "step2_header":    "**📄 Upload your CV**",
        "step2_caption":   "The AI extracts keywords and builds your profile automatically. You can edit them later or skip this step.",
        "step2_file":      "CV (PDF, DOCX or TXT)",
        "step2_analyze":   "🤖 Analyze CV with AI",
        "step2_spinning":  "Analyzing your CV…",
        "step2_extracted": "**📋 Extracted from your CV — review before continuing:**",
        "step2_profile_prefix": "Profile: ",
        "btn_back":        "← Back",
        "toast_cv_ok":     "✅ {n} keywords extracted. Review them in the next step.",
        "toast_cv_err":    "Could not analyze the CV. Continue and fill in data manually.",
        # Step 3
        "step3_header":        "**🔍 Search keywords**",
        "step3_kw_ph":         "Your keywords — × to remove",
        "step3_add_ph":        "Add keyword...",
        "step3_add_btn":       "+ Add",
        "step3_params":        "**⚙️ Parameters**",
        "step3_remote_chk":    "Remote listings only",
        "step3_remote_help":   "Enable only if your CV specifies remote preference. Disabled by default to avoid missing hybrid or on-site listings.",
        "step3_score_label":   "Minimum score for 'Recommended' and letters",
        "step3_score_help":    "Threshold for the 'Recommended' tab and letter generation. Listings below the threshold remain visible in 'All'.",
        "step3_sources":       "**Search sources**",
        "step3_global":        "🌍 Global remote",
        "step3_latam":         "🌎 Latin America",
        "step3_login":         "🔐 Login required (beta)",
        "step3_browser_dir":   "Browser session directory",
        "step3_browser_help":  "Use a persistent profile created with `python browser_login.py <portal>`.",
        "step3_browser_note":  "Beta: these sources read listings from a real saved session in Chromium. They do not automate applications.",
        "step3_us":            "🇺🇸 US / English-speaking",
        "step3_eu":            "🇪🇺 Europe",
        "step3_other":         "📌 Other",
        "step3_limit_chk":     "Limit number of listings to analyze",
        "step3_limit_help":    "Useful for quick tests or to save AI quota.",
        "step3_limit_label":   "Maximum listings",
        "toast_no_kw":         "Add at least one keyword.",
        "toast_no_src":        "Select at least one source.",
        # Step 4
        "step4_header":    "**👤 Your professional profile**",
        "step4_caption":   "The AI uses this text to evaluate how well each listing fits you.",
        "step4_ph":        "Target role, tech stack, experience, languages...",
        "step4_warning":   "Profile is empty. Without a profile the AI scoring has no basis to evaluate listings — all scores will be low or arbitrary. Fill in the text or go back to analyze your CV.",
        "btn_start":       "🚀 Start search",
        # Validate config
        "val_key":         "Invalid Gemini API key.",
        "val_email":       "Invalid sender email.",
        "val_pass":        "App password must be 16 characters.",
        "val_recip":       "Invalid recipient email.",
        "val_no_kw":       "Add at least one keyword.",
        "val_no_src":      "Select at least one source.",
        # Workflow
        "wf_step_label":   "Step {n}  ·  {title}",
        "wf_step1_title":  "Search listings",
        "wf_step2_title":  "Analyze with AI",
        "wf_step3_title":  "Generate letters",
        "wf_step4_title":  "Send summary by email",
        "wf_starting":     "Starting...",
        "wf_searching":    "Searching **{platform}**...",
        "wf_stopped":      "⏹️ Search stopped after {n} source(s) — {jobs} listings found so far.",
        "wf_found":        "✅ **{jobs} unique listings** found — {time}",
        "wf_no_jobs":      "No listings found to analyze.",
        "wf_scoring":      "Analyzing **{i}/{n}**: {title} @ {company}",
        "wf_quota":        "Daily Gemini quota exceeded. Analyzed {i} of {n} listings.",
        "wf_scored":       "✅ **{top} recommended** of {total} analyzed — {time}",
        "wf_letter":       "Generating letter **{i}/{n}** — {title}",
        "wf_letter_1":     "letter generated",
        "wf_letter_n":     "letters generated",
        "wf_email_send":   "Sending summary to {recipient}...",
        "wf_email_ok":     "✅ Summary sent to **{recipient}**.",
        "wf_email_err":    "Could not send email: {error}",
        "wf_src_prog":     "{done}/{total} sources{eta}",
        "wf_ai_prog":      "{done}/{total} analyzed{eta}",
        "wf_let_prog":     "{done}/{total} letters{eta}",
        "wf_eta":          "  ·  ~{time} remaining",
        "wf_err_platform": "⚠️ Error on {platform}: {error}",
        "wf_best_label":   "Best so far",
    },
}


def _t(key: str, **kw) -> str:
    """Devuelve el texto en el idioma activo, interpolando kwargs si los hay."""
    lang = st.session_state.get("lang", "es")
    d    = TRANSLATIONS.get(lang, TRANSLATIONS["es"])
    txt  = d.get(key, TRANSLATIONS["es"].get(key, key))
    return txt.format(**kw) if kw else txt


st.markdown("""
<style>
#jh-toggles {
  position: fixed; top: 60px; right: 7.5rem;
  z-index: 100000; display: flex; gap: 7px; align-items: center;
}
.jh-seg {
  display: inline-flex; align-items: center;
  background: var(--surface); border: 1px solid var(--b2);
  border-radius: 9999px; padding: 2px; gap: 1px; box-shadow: var(--s1);
}
.jh-seg-o {
  display: inline-flex; align-items: center; justify-content: center;
  height: 24px; padding: 0 9px; border-radius: 9999px;
  color: var(--t3); font-size: 12px; font-weight: 600;
  font-family: 'Inter', sans-serif; cursor: pointer;
  text-decoration: none !important; user-select: none;
  transition: all 120ms ease; line-height: 1;
}
.jh-seg-o:hover { color: var(--t1); background: var(--surface-2); }
.jh-seg-o.on    { background: var(--pm); color: var(--p); font-weight: 700; }
</style>

<div id="jh-toggles">
  <div class="jh-seg" title="Modo claro / Dark mode">
    <a class="jh-seg-o" data-theme-opt="light" id="btn-light">☀️</a>
    <a class="jh-seg-o" data-theme-opt="dark"  id="btn-dark">🌙</a>
  </div>
  <div class="jh-seg" title="Idioma / Language">
    <a class="jh-seg-o" data-lang-opt="es" id="btn-es">ES</a>
    <a class="jh-seg-o" data-lang-opt="en" id="btn-en">EN</a>
  </div>
</div>
""", unsafe_allow_html=True)

# JS en component separado — st.markdown NO ejecuta <script>, components.html sí
components.html("""<script>
(function() {

  /* ── Acceso al documento y localStorage del padre (Streamlit) ────────── */
  var ROOT = window.parent.document;
  var LS   = window.parent.localStorage;

  /* ── Traducciones ────────────────────────────────────────────────────── */
  var T = {
    es: {
      "hero_eyebrow_search":  "Búsqueda de empleo con IA",
      "hero_title_search":    "Encontrá el trabajo que realmente encaja.",
      "hero_sub_search":      "Job Hunter reúne ofertas de 15+ portales, las puntúa según tu perfil y genera cartas de presentación listas para enviar.",
      "hero_note_search":     "Toda la lógica corre en tu máquina. Tus credenciales nunca salen del navegador.",
      "hero_tag_scoring":     "Scoring con IA",
      "hero_tag_multi":       "Multi-source",
      "hero_tag_letters":     "Cover letters",
      "hero_tag_local":       "Local-first",
      "hero_stat_sources":    "fuentes activas",
      "hero_stat_score":      "score por oferta",
      "hero_stat_ai":         "cover letters",
      "hero_stat_time":       "por búsqueda",
      "hero_eyebrow_results": "Panel de resultados",
      "hero_title_results":   "Tus oportunidades, priorizadas.",
      "hero_sub_results":     "La IA evaluó cada oferta contra tu perfil. Las recomendadas están en la pestaña de abajo, ordenadas por score.",
      "hero_note_results":    "Resultados listos. Refiná las búsquedas o exportá las cartas.",
      "hero_tag_done":        "Búsqueda completada",
      "hero_stat_analyzed":   "analizadas",
      "hero_stat_rec":        "recomendadas",
      "hero_stat_best":       "mejor score",
      "hero_stat_threshold":  "umbral",
      "empty_label":  "Cómo funciona",
      "empty_title":  "Un flujo de 4 pasos, sin ruido visual.",
      "empty_copy":   "Configurás una vez, lanzás la búsqueda y recibís resultados ordenados por relevancia con cartas listas para enviar.",
      "feat1_title":  "Descubrí",
      "feat1_desc":   "Remotive, Get on Board, Himalayas, LatoJobs, WeWorkRemotely y 10+ fuentes más en una sola búsqueda.",
      "feat2_title":  "Priorizá",
      "feat2_desc":   "La IA puntúa cada oferta del 0 al 100 comparando el job description con tu perfil real. Sin inflado de seniority.",
      "feat3_title":  "Redactá",
      "feat3_desc":   "Genera una cover letter única por oferta, en el idioma del aviso, con referencias específicas al puesto.",
      "feat4_title":  "Actuá",
      "feat4_desc":   "Descargá las cartas individualmente, exportá todo como JSON o recibí un digest por email.",
      "searching_notice": "La búsqueda está en curso — podés detenerla en cualquier momento.",
      "search_time_hint":  "Una búsqueda completa suele tardar entre 6 y 8 minutos.",
      "metric_analyzed":    "Analizadas",
      "metric_recommended": "Recomendadas",
      "metric_best":        "Mejor score",
      "metric_excellent":   "Excelentes 80+",
      "wf_best_label":    "Mejores hasta ahora",
      "why_fits":         "Por qué encaja",
      "what_missing":     "Lo que podría faltar",
      "no_reasons":       "Sin razones calculadas.",
      "no_missing":       "Sin faltantes críticos.",
      "remote_tag":       "Remota",
      "offer_link":       "Ver oferta →"
    },
    en: {
      "hero_eyebrow_search":  "AI-Powered Job Search",
      "hero_title_search":    "Find the job that truly fits.",
      "hero_sub_search":      "Job Hunter gathers listings from 15+ portals, scores them against your profile, and generates ready-to-send cover letters.",
      "hero_note_search":     "All logic runs on your machine. Your credentials never leave the browser.",
      "hero_tag_scoring":     "AI Scoring",
      "hero_tag_multi":       "Multi-source",
      "hero_tag_letters":     "Cover letters",
      "hero_tag_local":       "Local-first",
      "hero_stat_sources":    "active sources",
      "hero_stat_score":      "score per listing",
      "hero_stat_ai":         "cover letters",
      "hero_stat_time":       "per search",
      "hero_eyebrow_results": "Results Dashboard",
      "hero_title_results":   "Your opportunities, prioritized.",
      "hero_sub_results":     "The AI evaluated each listing against your profile. Recommended ones are in the tab below, sorted by score.",
      "hero_note_results":    "Results ready. Refine the search or export the letters.",
      "hero_tag_done":        "Search completed",
      "hero_stat_analyzed":   "analyzed",
      "hero_stat_rec":        "recommended",
      "hero_stat_best":       "best score",
      "hero_stat_threshold":  "threshold",
      "empty_label":  "How it works",
      "empty_title":  "A 4-step flow, no visual noise.",
      "empty_copy":   "Configure once, launch the search, and receive results sorted by relevance with letters ready to send.",
      "feat1_title":  "Discover",
      "feat1_desc":   "Remotive, Get on Board, Himalayas, LatoJobs, WeWorkRemotely and 10+ more sources in a single search.",
      "feat2_title":  "Prioritize",
      "feat2_desc":   "The AI scores each listing from 0 to 100, comparing the job description with your real profile. No seniority inflation.",
      "feat3_title":  "Write",
      "feat3_desc":   "Generates a unique cover letter per listing, in the language of the ad, with specific references to the role.",
      "feat4_title":  "Act",
      "feat4_desc":   "Download letters individually, export everything as JSON, or receive a digest by email.",
      "searching_notice": "Search in progress — you can stop it at any time.",
      "search_time_hint":  "A full search typically takes 6 to 8 minutes.",
      "metric_analyzed":    "Analyzed",
      "metric_recommended": "Recommended",
      "metric_best":        "Best score",
      "metric_excellent":   "Excellent 80+",
      "wf_best_label":    "Best so far",
      "why_fits":         "Why it fits",
      "what_missing":     "What might be missing",
      "no_reasons":       "No reasons calculated.",
      "no_missing":       "No critical gaps.",
      "remote_tag":       "Remote",
      "offer_link":       "View listing →"
    }
  };

  /* ── Aplicar tema ────────────────────────────────────────────────────── */
  function applyTheme(theme) {
    ROOT.documentElement.setAttribute('data-theme', theme);
    ROOT.querySelectorAll('[data-theme-opt]').forEach(function(el) {
      el.classList.toggle('on', el.getAttribute('data-theme-opt') === theme);
    });
  }

  /* ── Aplicar idioma ──────────────────────────────────────────────────── */
  function applyLang(lang) {
    var d = T[lang];
    if (!d) return;
    ROOT.querySelectorAll('[data-i18n]').forEach(function(el) {
      var v = d[el.getAttribute('data-i18n')];
      if (v !== undefined) el.innerHTML = v;
    });
    ROOT.querySelectorAll('[data-lang-opt]').forEach(function(el) {
      el.classList.toggle('on', el.getAttribute('data-lang-opt') === lang);
    });
  }

  /* ── Leer localStorage y aplicar todo ───────────────────────────────── */
  var _applying = false;
  function applyAll() {
    if (_applying) return;
    _applying = true;
    try {
      applyTheme(LS.getItem('jh_theme') || 'light');
      applyLang(LS.getItem('jh_lang') || 'es');
    } finally { _applying = false; }
  }

  /* ── Conectar botones (están en el DOM del padre) ────────────────────── */
  var _wired = false;
  function wireButtons() {
    if (_wired) return;
    var light = ROOT.getElementById('btn-light');
    var dark  = ROOT.getElementById('btn-dark');
    var es    = ROOT.getElementById('btn-es');
    var en    = ROOT.getElementById('btn-en');
    if (!light || !dark || !es || !en) return;
    _wired = true;
    light.addEventListener('click', function(e) { e.preventDefault(); jhSetTheme('light'); });
    dark .addEventListener('click', function(e) { e.preventDefault(); jhSetTheme('dark');  });
    es   .addEventListener('click', function(e) { e.preventDefault(); jhSetLang('es');     });
    en   .addEventListener('click', function(e) { e.preventDefault(); jhSetLang('en');     });
  }

  function jhSetTheme(theme) {
    LS.setItem('jh_theme', theme);
    applyTheme(theme);
  }

  function jhSetLang(lang) {
    // Los labels de widgets Streamlit son server-rendered (Python _t()).
    // Requieren un rerun del servidor → navegamos con ?lang=X.
    // El dark mode sobrevive porque MutationObserver lo re-aplica al recargar.
    var cur = LS.getItem('jh_lang') || 'es';
    LS.setItem('jh_lang', lang);
    applyLang(lang); // actualiza data-i18n inmediatamente mientras carga
    if (lang !== cur) {
      try {
        var u = new URL(window.parent.location.href);
        u.searchParams.set('lang', lang);
        window.parent.location.href = u.toString(); // rerun Streamlit
      } catch(e) {}
    }
  }

  /* ── Inicialización ──────────────────────────────────────────────────── */
  applyAll();
  setTimeout(function() { applyAll(); wireButtons(); }, 100);

  /* ── MutationObserver: re-aplicar tras cada rerun de Streamlit ───────── */
  if (!window.parent._jhObserver) {
    var _dbt;
    window.parent._jhObserver = new MutationObserver(function() {
      clearTimeout(_dbt);
      _dbt = setTimeout(function() {
        _wired = false;
        applyAll();
        wireButtons();
      }, 120);
    });
    window.parent._jhObserver.observe(ROOT.body, { childList: true, subtree: true });
  }

})();
</script>""", height=0)


# ─── Helpers ──────────────────────────────────────────────────────────────────
def validate_config():
    errors = []
    if not st.session_state.gemini_key or not st.session_state.gemini_key.startswith("AIza"):
        errors.append(_t("val_key"))
    if st.session_state.send_email:
        if not st.session_state.email_sender or "@" not in st.session_state.email_sender:
            errors.append(_t("val_email"))
        if len(st.session_state.email_password_raw.replace(" ", "")) != 16:
            errors.append(_t("val_pass"))
        if not st.session_state.email_recipient or "@" not in st.session_state.email_recipient:
            errors.append(_t("val_recip"))
    if not st.session_state.keywords_list:
        errors.append(_t("val_no_kw"))
    browser_sources = [] if IS_CLOUD else [
        st.session_state.use_linkedin_browser,
        st.session_state.use_bumeran_browser,
        st.session_state.use_computrabajo_browser,
        st.session_state.use_indeed_browser,
    ]
    if not any([st.session_state.use_remotive, st.session_state.use_arbeitnow,
                st.session_state.use_wwr, st.session_state.use_himalayas,
                st.session_state.use_remoteok, st.session_state.use_jobicy,
                st.session_state.use_getonboard, st.session_state.use_puentetalent,
                st.session_state.use_latojobs, st.session_state.use_workingnomads,
                st.session_state.use_themuse, st.session_state.use_remoteco,
                st.session_state.use_jobspresso, st.session_state.use_justjoinit,
                st.session_state.use_authenticjobs, *browser_sources]):
        errors.append(_t("val_no_src"))
    return errors


def format_duration(seconds):
    seconds = max(0, int(round(seconds)))
    m, s = divmod(seconds, 60)
    return f"{m} min {s:02d} s" if m else f"{s} s"


def _render_stepper(step: int) -> None:
    steps = [
        (_t("step1_lbl"), _t("step1_desc")),
        (_t("step2_lbl"), _t("step2_desc")),
        (_t("step3_lbl"), _t("step3_desc")),
        (_t("step4_lbl"), _t("step4_desc")),
    ]
    cards = []
    for i, (label, desc) in enumerate(steps, 1):
        if i < step:   cls = "jh-step jh-step--done";    num = "✓"
        elif i == step: cls = "jh-step jh-step--active"; num = str(i)
        else:           cls = "jh-step jh-step--pending"; num = str(i)
        cards.append(
            f'<div class="{cls}">'
            f'<span class="jh-step-num">{num}</span>'
            f'<div><div class="jh-step-lbl">{label}</div>'
            f'<div class="jh-step-desc">{desc}</div></div>'
            f'</div>'
        )
    st.markdown(
        f'<div class="jh-stepper">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )


def _analyze_cv(uploaded_file, api_key: str, model: str) -> dict | None:
    """Envía el CV a Gemini y devuelve {keywords, profile}."""
    import json, re
    from google import genai
    from google.genai import types

    _PROMPT = (
        "Analyze this CV/resume carefully and extract ALL information as faithfully and completely as possible. "
        "Your goal is maximum detail — do not summarize, abbreviate, or omit any section. "
        "Return ONLY a raw JSON object — no markdown, no explanation.\n\n"
        "Strict rules:\n"
        "- Use only information explicitly present in the CV.\n"
        "- Do NOT infer seniority, expertise, achievements, impact, leadership, ownership, or implementation work unless the CV states it clearly.\n"
        "- Do NOT upgrade the candidate's level with words such as senior, semi senior, expert, lead, principal, staff, architect, etc. unless those exact levels appear in the CV.\n"
        "- If the CV says the person analyzed, supported, collaborated, documented, tested, or learned something, describe it exactly that way. Do not rewrite it as implemented, built, led, owned, or delivered.\n"
        "- If years of experience are not explicit or cannot be calculated reliably from dates in the CV, do not invent them.\n"
        "- If remote preference, location, languages, or target role are not explicit, say that they are not specified in the CV.\n"
        "- CRITICAL: Extract EVERY job position, project, technology, tool, certification, education entry, and skill explicitly listed. Do NOT skip items due to length.\n"
        "- List ALL technologies/tools mentioned anywhere in the CV (in skills sections, job descriptions, projects, certifications, etc.).\n"
        "- For each work experience, include: company name, role/title, dates (start–end or duration if stated), and ALL responsibilities/tasks described for that role.\n"
        "- For each project, include: project name, technologies used, and what the candidate did (using the CV's exact verbs).\n"
        "- For education: include institution, degree, field, and dates if present.\n"
        "- For certifications/courses: list each one with provider and year if stated.\n"
        "- Do NOT truncate lists of technologies, responsibilities, or projects — include everything.\n\n"
        "Output schema:\n"
        '{'
        '"keywords": ["8 to 15 job-board search terms derived directly from explicit roles, technologies, and domains in the CV. Include ALL main technologies, frameworks, and roles found."], '
        '"profile": "Write in the same language as the CV. Write as many paragraphs or sections as needed to cover ALL the following — do NOT limit length: (1) Personal info: name, location, contact if present. (2) Professional summary if the CV has one. (3) ALL work experiences in chronological order: company, role, dates, and every responsibility/task listed. (4) ALL projects with technologies and contributions. (5) Education: all entries with institution, degree, field, dates. (6) ALL technical skills and tools explicitly listed. (7) ALL certifications and courses with provider and year. (8) Languages. (9) Any other section present in the CV (e.g. awards, publications, volunteering). When something is not specified in the CV, say so explicitly."'
        '}'
    )

    try:
        _client = genai.Client(api_key=api_key)
        file_bytes = uploaded_file.getvalue()
        mime = uploaded_file.type  # "application/pdf" or "text/plain"

        if mime == "text/plain":
            cv_text = file_bytes.decode("utf-8", errors="replace")[:30000]
            contents = f"{_PROMPT}\n\nCV:\n{cv_text}"
        elif mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            import io
            from docx import Document as DocxDocument
            doc = DocxDocument(io.BytesIO(file_bytes))
            cv_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())[:30000]
            contents = f"{_PROMPT}\n\nCV:\n{cv_text}"
        else:
            contents = [
                types.Part.from_bytes(data=file_bytes, mime_type="application/pdf"),
                types.Part.from_text(text=_PROMPT),
            ]

        resp = _client.models.generate_content(model=model, contents=contents)
        raw = resp.text.strip().replace("```json", "").replace("```", "").strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"\{[\s\S]*\}", raw)
            if m:
                return json.loads(m.group())
        return None
    except Exception as e:
        st.error(f"Error analizando el CV: {e}")
        return None


# ─── Wizard inline (sin @st.dialog para garantizar cierre correcto) ───────────
def show_config_wizard():
    step = st.session_state.config_step

    # Header
    h_col, cancel_col = st.columns([5, 1])
    with h_col:
        st.markdown(
            f'<div class="jh-section" style="margin-top:.5rem;">'
            f'<span class="jh-label">{_t("wiz_label")}</span>'
            f'<h2 class="jh-title">{_t("wiz_title")}</h2>'
            f'<p class="jh-copy">{_t("wiz_copy")}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with cancel_col:
        st.markdown('<div class="cancel-marker" style="height:4rem;"></div>', unsafe_allow_html=True)
        if st.button(
            _t("wiz_close"),
            use_container_width=True,
            key="wizard_cancel",
            help="Cierra el formulario sin ejecutar búsqueda.",
        ):
            st.session_state.show_dialog = False
            st.rerun()

    _render_stepper(step)

    # ── Paso 1: Credenciales ──────────────────────────────────────────────
    if step == 1:
        with st.container(border=True):
            st.markdown(_t("step1_header"))
            with st.expander(_t("step1_gemini_help"), icon="❓"):
                st.markdown("""
1. Ir a [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Iniciar sesión con Google → **Create API Key**
3. Copiar la clave — es gratis, no requiere tarjeta.
""")
            st.session_state.gemini_key = st.text_input(
                _t("step1_key_label"),
                value=st.session_state.gemini_key,
                type="password",
                placeholder="AIzaXXXXXXXXXXXXXXXXX",
            )
            _models = [
                "models/gemini-3.1-pro",
                "models/gemini-3.1-flash-lite",
                "models/gemini-3.0-flash",
                "models/gemini-2.5-pro",
                "models/gemini-2.5-flash",
                "models/gemini-2.5-flash-lite",
                "models/gemini-2.0-flash",
                "models/gemini-2.0-flash-lite",
                "models/gemini-1.5-pro",
                "models/gemini-1.5-flash",
                "models/gemini-1.5-flash-8b",
            ]
            if st.session_state.selected_model not in _models:
                st.session_state.selected_model = "models/gemini-3.1-flash-lite"
            _idx = _models.index(st.session_state.selected_model)
            st.session_state.selected_model = st.selectbox(_t("step1_model_label"), _models, index=_idx)

        with st.container(border=True):
            st.checkbox(_t("step1_email_chk"), key="send_email")
            if st.session_state.send_email:
                with st.expander(_t("step1_email_help"), icon="❓"):
                    st.markdown("""
1. [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Verificación en 2 pasos **activada**
3. Crear app `Job Hunter` → copiar los 16 caracteres
""")
                c1, c2 = st.columns(2)
                with c1:
                    st.session_state.email_sender = st.text_input(
                        _t("step1_gmail_label"),
                        value=st.session_state.email_sender,
                        placeholder="tu@gmail.com",
                    )
                with c2:
                    st.session_state.email_recipient = st.text_input(
                        _t("step1_recip_label"),
                        value=st.session_state.email_recipient,
                        placeholder="destino@gmail.com",
                    )
                st.session_state.email_password_raw = st.text_input(
                    _t("step1_pass_label"),
                    value=st.session_state.email_password_raw,
                    type="password",
                    placeholder="abcd efgh ijkl mnop",
                )

        if st.button(_t("btn_next_arrow"), type="primary", use_container_width=True):
            err = []
            if not st.session_state.gemini_key or not st.session_state.gemini_key.startswith("AIza"):
                err.append(_t("err_key"))
            if st.session_state.send_email:
                if not st.session_state.email_sender or "@" not in st.session_state.email_sender:
                    err.append(_t("err_email"))
                if len(st.session_state.email_password_raw.replace(" ", "")) != 16:
                    err.append(_t("err_pass"))
                if not st.session_state.email_recipient or "@" not in st.session_state.email_recipient:
                    err.append(_t("err_recip"))
            if err:
                st.toast(" · ".join(err), icon="⚠️")
            else:
                st.session_state.config_step = 2
                st.rerun()

    # ── Paso 2: CV ────────────────────────────────────────────────────────
    elif step == 2:
        with st.container(border=True):
            st.markdown(_t("step2_header"))
            st.caption(_t("step2_caption"))
            uploaded_file = st.file_uploader(
                _t("step2_file"),
                type=["pdf", "docx", "txt"],
                label_visibility="collapsed",
                key="cv_upload",
            )
            if uploaded_file:
                if st.button(_t("step2_analyze"), type="primary", use_container_width=True):
                    with st.spinner(_t("step2_spinning")):
                        result = _analyze_cv(
                            uploaded_file,
                            st.session_state.gemini_key,
                            st.session_state.selected_model,
                        )
                    if result:
                        kws  = [k for k in result.get("keywords", []) if k.strip()]
                        prof = result.get("profile", "").strip()
                        if kws:
                            st.session_state.keywords_list = kws
                            st.session_state["kw_options"] = list(kws)
                            st.session_state["kw_tags"] = list(kws)
                        if prof:
                            st.session_state.candidate_profile = prof
                        st.session_state.cv_analyzed = True
                        st.toast(_t("toast_cv_ok", n=len(kws)), icon="✅")
                    else:
                        st.toast(_t("toast_cv_err"), icon="⚠️")

        if st.session_state.cv_analyzed:
            with st.container(border=True):
                st.markdown(_t("step2_extracted"))
                kw_html = "".join(
                    f'<span style="display:inline-block;padding:3px 11px;margin:2px 3px;'
                    f'background:#ede9fe;color:#4f46e5;border-radius:20px;'
                    f'font-size:13px;font-weight:500;">{k}</span>'
                    for k in st.session_state.keywords_list
                )
                st.markdown(
                    f'<div style="margin:0.35rem 0 0.5rem 0;">{kw_html}</div>',
                    unsafe_allow_html=True,
                )
                st.caption(_t("step2_profile_prefix") + st.session_state.candidate_profile[:220].replace("\n", " ") + "…")

        col_back, col_next = st.columns(2)
        with col_back:
            if st.button(_t("btn_back"), use_container_width=True):
                st.session_state.config_step = 1
                st.rerun()
        with col_next:
            if st.button(_t("btn_next_arrow"), type="primary", use_container_width=True):
                st.session_state.config_step = 3
                st.rerun()

    # ── Paso 3: Keywords y fuentes ────────────────────────────────────────
    elif step == 3:
        with st.container(border=True):
            st.markdown(_t("step3_header"))

            # Procesar keyword pendiente ANTES de instanciar el multiselect
            if "_pending_add" in st.session_state:
                _kw = st.session_state.pop("_pending_add")
                if _kw:
                    if _kw not in st.session_state["kw_options"]:
                        st.session_state["kw_options"].append(_kw)
                    if _kw not in st.session_state.keywords_list:
                        st.session_state.keywords_list.append(_kw)
                st.session_state["kw_tags"] = list(st.session_state.keywords_list)

            if "kw_tags" not in st.session_state:
                st.session_state["kw_tags"] = list(st.session_state.keywords_list)

            selected = st.multiselect(
                "Keywords",
                options=st.session_state["kw_options"],
                key="kw_tags",
                placeholder=_t("step3_kw_ph"),
                label_visibility="collapsed",
            )
            st.session_state.keywords_list = list(selected)

            with st.form("add_kw", clear_on_submit=True):
                c1, c2 = st.columns([5, 1])
                with c1:
                    new_kw = st.text_input(
                        "kw", placeholder=_t("step3_add_ph"),
                        label_visibility="collapsed",
                    )
                with c2:
                    add_submitted = st.form_submit_button(_t("step3_add_btn"), use_container_width=True)
                if add_submitted and new_kw.strip():
                    st.session_state["_pending_add"] = new_kw.strip()
                    st.rerun()

        with st.container(border=True):
            st.markdown(_t("step3_params"))
            st.session_state.only_remote = st.checkbox(
                _t("step3_remote_chk"),
                value=st.session_state.only_remote,
                help=_t("step3_remote_help"),
            )
            st.session_state.min_score = st.slider(
                _t("step3_score_label"),
                min_value=30, max_value=90, step=5,
                value=st.session_state.min_score,
                help=_t("step3_score_help"),
            )
            st.markdown(_t("step3_sources"))
            st.caption(_t("step3_global"))
            g1, g2, g3, g4, g5 = st.columns(5)
            with g1:
                st.session_state.use_remotive     = st.checkbox("Remotive",       value=st.session_state.use_remotive)
            with g2:
                st.session_state.use_himalayas    = st.checkbox("Himalayas",      value=st.session_state.use_himalayas)
            with g3:
                st.session_state.use_remoteok     = st.checkbox("RemoteOK",       value=st.session_state.use_remoteok)
            with g4:
                st.session_state.use_jobicy       = st.checkbox("Jobicy",         value=st.session_state.use_jobicy)
            with g5:
                st.session_state.use_workingnomads = st.checkbox("WorkingNomads", value=st.session_state.use_workingnomads)

            st.caption("🌎 Latinoamérica")
            l1, l2, l3, l4, l5 = st.columns(5)
            with l1:
                st.session_state.use_getonboard   = st.checkbox("Get on Board",   value=st.session_state.use_getonboard)
            with l2:
                st.session_state.use_latojobs     = st.checkbox("LatoJobs",       value=st.session_state.use_latojobs)
            with l3:
                st.session_state.use_puentetalent = st.checkbox("Puente Talent",  value=st.session_state.use_puentetalent)
            with l4:
                st.empty()
            with l5:
                st.empty()

            if not IS_CLOUD:
                st.caption(_t("step3_login"))
                b1, b2, b3, b4 = st.columns(4)
                with b1:
                    st.session_state.use_linkedin_browser = st.checkbox("LinkedIn", value=st.session_state.use_linkedin_browser)
                with b2:
                    st.session_state.use_bumeran_browser = st.checkbox("Bumeran", value=st.session_state.use_bumeran_browser)
                with b3:
                    st.session_state.use_computrabajo_browser = st.checkbox("Computrabajo", value=st.session_state.use_computrabajo_browser)
                with b4:
                    st.session_state.use_indeed_browser = st.checkbox("Indeed", value=st.session_state.use_indeed_browser)

                if any([
                    st.session_state.use_linkedin_browser,
                    st.session_state.use_bumeran_browser,
                    st.session_state.use_computrabajo_browser,
                    st.session_state.use_indeed_browser,
                ]):
                    st.session_state.browser_profile_dir = st.text_input(
                        _t("step3_browser_dir"),
                        value=st.session_state.browser_profile_dir,
                        help=_t("step3_browser_help"),
                    )
                    st.caption(_t("step3_browser_note"))

            st.caption(_t("step3_us"))
            a1, a2, a3, a4, a5 = st.columns(5)
            with a1:
                st.session_state.use_arbeitnow    = st.checkbox("Arbeitnow",      value=st.session_state.use_arbeitnow)
            with a2:
                st.session_state.use_wwr          = st.checkbox("WeWorkRemotely", value=st.session_state.use_wwr)
            with a3:
                st.session_state.use_themuse      = st.checkbox("The Muse",       value=st.session_state.use_themuse)
            with a4:
                st.session_state.use_jobspresso   = st.checkbox("Jobspresso",     value=st.session_state.use_jobspresso)
            with a5:
                st.session_state.use_remoteco     = st.checkbox("Remote.co",      value=st.session_state.use_remoteco)

            st.caption(_t("step3_eu"))
            e1, _ = st.columns([1, 4])
            with e1:
                st.session_state.use_justjoinit   = st.checkbox("JustJoin.it",   value=st.session_state.use_justjoinit)

            st.caption(_t("step3_other"))
            o1, _ = st.columns([1, 4])
            with o1:
                st.session_state.use_authenticjobs = st.checkbox("AuthenticJobs", value=st.session_state.use_authenticjobs)

            st.session_state.use_max_results = st.checkbox(
                _t("step3_limit_chk"),
                value=st.session_state.use_max_results,
                help=_t("step3_limit_help"),
            )
            if st.session_state.use_max_results:
                st.session_state.max_results_limit = st.slider(
                    _t("step3_limit_label"), min_value=10, max_value=500, step=10,
                    value=st.session_state.max_results_limit,
                )

        col_back, col_next = st.columns(2)
        with col_back:
            if st.button(_t("btn_back"), use_container_width=True):
                st.session_state.config_step = 2
                st.rerun()
        with col_next:
            if st.button(_t("btn_next_arrow"), type="primary", use_container_width=True):
                _browser = [] if IS_CLOUD else [
                    st.session_state.use_linkedin_browser,
                    st.session_state.use_bumeran_browser,
                    st.session_state.use_computrabajo_browser,
                    st.session_state.use_indeed_browser,
                ]
                if not st.session_state.keywords_list:
                    st.toast(_t("toast_no_kw"), icon="⚠️")
                elif not any([st.session_state.use_remotive, st.session_state.use_arbeitnow,
                              st.session_state.use_wwr, st.session_state.use_himalayas,
                              st.session_state.use_remoteok, st.session_state.use_jobicy,
                              st.session_state.use_getonboard, st.session_state.use_puentetalent,
                              st.session_state.use_latojobs, st.session_state.use_workingnomads,
                              st.session_state.use_themuse, st.session_state.use_remoteco,
                              st.session_state.use_jobspresso, st.session_state.use_justjoinit,
                              st.session_state.use_authenticjobs, *_browser]):
                    st.toast(_t("toast_no_src"), icon="⚠️")
                else:
                    st.session_state.config_step = 4
                    st.rerun()

    # ── Paso 4: Perfil ────────────────────────────────────────────────────
    elif step == 4:
        with st.container(border=True):
            st.markdown(_t("step4_header"))
            st.caption(_t("step4_caption"))
            st.session_state.candidate_profile = st.text_area(
                "perfil",
                value=st.session_state.candidate_profile,
                height=195,
                label_visibility="collapsed",
                placeholder=_t("step4_ph"),
            )

        if not st.session_state.candidate_profile.strip():
            st.warning(_t("step4_warning"), icon="⚠️")

        col_back, col_start = st.columns(2)
        with col_back:
            if st.button(_t("btn_back"), use_container_width=True):
                st.session_state.config_step = 3
                st.rerun()
        with col_start:
            if st.button(_t("btn_start"), type="primary", use_container_width=True):
                errors = validate_config()
                if errors:
                    st.toast(" · ".join(errors), icon="⚠️")
                else:
                    st.session_state.show_dialog   = False
                    st.session_state.run_search    = True
                    st.session_state.is_searching  = True   # ← debe estar True ANTES del rerun
                    st.session_state.search_done   = False
                    st.session_state.cancel_search = False
                    st.session_state.scored_jobs   = []
                    st.session_state.top_matches   = []
                    st.rerun()  # rerun desde contexto principal — siempre full-page


# ─── Wizard (toma la pantalla completa cuando está activo) ────────────────────
# Si el usuario vino de "Detener & Configurar", abrir en paso 3 (keywords/fuentes)
# para que pueda ajustar rápidamente y relanzar.
if st.session_state.cancel_and_config:
    st.session_state.cancel_and_config = False
    st.session_state.show_dialog       = True
    st.session_state.config_step       = 3   # Abre en Keywords/Fuentes directamente

if st.session_state.show_dialog:
    show_config_wizard()
    st.stop()

# ─── Hero ─────────────────────────────────────────────────────────────────────
def _render_hero():
    if st.session_state.search_done and st.session_state.scored_jobs:
        _s   = st.session_state.scored_jobs
        _top = st.session_state.top_matches
        best = _s[0].score if _s else 0
        stat_html = (
            f'<div class="jh-stat-grid">'
            f'<div class="jh-stat"><strong>{len(_s)}</strong><span data-i18n="hero_stat_analyzed">{_t("hero_stat_analyzed")}</span></div>'
            f'<div class="jh-stat"><strong>{len(_top)}</strong><span data-i18n="hero_stat_rec">{_t("hero_stat_rec")}</span></div>'
            f'<div class="jh-stat"><strong>{best}/100</strong><span data-i18n="hero_stat_best">{_t("hero_stat_best")}</span></div>'
            f'<div class="jh-stat"><strong>{st.session_state.min_score_last}</strong><span data-i18n="hero_stat_threshold">{_t("hero_stat_threshold")}</span></div>'
            f'</div>'
        )
        note_key    = "hero_note_results"
        eyebrow_key = "hero_eyebrow_results"
        title_key   = "hero_title_results"
        sub_key     = "hero_sub_results"
        tag_key     = "hero_tag_done"
        note    = _t(note_key);    eyebrow = _t(eyebrow_key)
        title   = _t(title_key);  sub     = _t(sub_key)
        tags    = f'<span class="jh-tag jh-tag-blue" data-i18n="{tag_key}">{_t(tag_key)}</span>'
    else:
        stat_html = (
            f'<div class="jh-stat-grid">'
            f'<div class="jh-stat"><strong>15+</strong><span data-i18n="hero_stat_sources">{_t("hero_stat_sources")}</span></div>'
            f'<div class="jh-stat"><strong>0–100</strong><span data-i18n="hero_stat_score">{_t("hero_stat_score")}</span></div>'
            f'<div class="jh-stat"><strong>IA</strong><span data-i18n="hero_stat_ai">{_t("hero_stat_ai")}</span></div>'
            f'<div class="jh-stat"><strong>6–8 min</strong><span data-i18n="hero_stat_time">{_t("hero_stat_time")}</span></div>'
            f'</div>'
        )
        note_key    = "hero_note_search"
        eyebrow_key = "hero_eyebrow_search"
        title_key   = "hero_title_search"
        sub_key     = "hero_sub_search"
        note    = _t(note_key);    eyebrow = _t(eyebrow_key)
        title   = _t(title_key);  sub     = _t(sub_key)
        tags    = (
            f'<span class="jh-tag jh-tag-blue"   data-i18n="hero_tag_scoring">{_t("hero_tag_scoring")}</span>'
            f'<span class="jh-tag jh-tag-violet" data-i18n="hero_tag_multi">{_t("hero_tag_multi")}</span>'
            f'<span class="jh-tag jh-tag-green"  data-i18n="hero_tag_letters">{_t("hero_tag_letters")}</span>'
            f'<span class="jh-tag jh-tag-gray"   data-i18n="hero_tag_local">{_t("hero_tag_local")}</span>'
        )

    st.markdown(f"""
<div class="jh-hero">
  <div class="jh-hero-copy">
    <span class="jh-eyebrow" data-i18n="{eyebrow_key}">{eyebrow}</span>
    <h1 class="jh-hero-title" data-i18n="{title_key}">{title}</h1>
    <p class="jh-hero-sub" data-i18n="{sub_key}">{sub}</p>
    <div class="jh-tags">{tags}</div>
  </div>
  <aside class="jh-panel">
    {stat_html}
    <p class="jh-panel-note" data-i18n="{note_key}">{note}</p>
  </aside>
</div>
""", unsafe_allow_html=True)

_render_hero()

# ─── Placeholders ─────────────────────────────────────────────────────────────
st.divider()
action_placeholder      = st.empty()
workflow_placeholder    = st.empty()
results_placeholder     = st.empty()
empty_state_placeholder = st.empty()


def render_empty_state():
    with empty_state_placeholder.container():
        st.markdown(f"""
<div class="jh-section" style="margin-top:1.5rem;">
  <span class="jh-label" data-i18n="empty_label">{_t("empty_label")}</span>
  <h2 class="jh-title" data-i18n="empty_title">{_t("empty_title")}</h2>
  <p class="jh-copy" data-i18n="empty_copy">{_t("empty_copy")}</p>
</div>
<div class="jh-features">
  <div class="jh-feature">
    <span class="jh-f-icon">01</span>
    <div class="jh-f-title" data-i18n="feat1_title">{_t("feat1_title")}</div>
    <p class="jh-f-desc" data-i18n="feat1_desc">{_t("feat1_desc")}</p>
  </div>
  <div class="jh-feature">
    <span class="jh-f-icon">02</span>
    <div class="jh-f-title" data-i18n="feat2_title">{_t("feat2_title")}</div>
    <p class="jh-f-desc" data-i18n="feat2_desc">{_t("feat2_desc")}</p>
  </div>
  <div class="jh-feature">
    <span class="jh-f-icon">03</span>
    <div class="jh-f-title" data-i18n="feat3_title">{_t("feat3_title")}</div>
    <p class="jh-f-desc" data-i18n="feat3_desc">{_t("feat3_desc")}</p>
  </div>
  <div class="jh-feature">
    <span class="jh-f-icon">04</span>
    <div class="jh-f-title" data-i18n="feat4_title">{_t("feat4_title")}</div>
    <p class="jh-f-desc" data-i18n="feat4_desc">{_t("feat4_desc")}</p>
  </div>
</div>
""", unsafe_allow_html=True)


# ─── Botón de acción ──────────────────────────────────────────────────────────
with action_placeholder.container():
    st.markdown('<div style="height:.75rem;"></div>', unsafe_allow_html=True)

    if st.session_state.is_searching:
        # ── Botones de control durante búsqueda ──────────────────────────────
        st.markdown(
            f'<p style="text-align:center;font-size:13px;font-weight:600;'
            f'color:var(--t2);margin-bottom:.75rem;letter-spacing:-.01em;"'
            f' data-i18n="searching_notice">{_t("searching_notice")}</p>',
            unsafe_allow_html=True,
        )
        c1, c_gap, c2 = st.columns([1, 0.12, 1.4])
        with c1:
            st.markdown('<div class="stop-marker"></div>', unsafe_allow_html=True)
            if st.button(_t("btn_stop"), use_container_width=True, key="btn_stop"):
                st.session_state.cancel_search = True
                st.session_state.is_searching  = False
                st.rerun()
        with c2:
            st.markdown('<div class="config-marker"></div>', unsafe_allow_html=True)
            if st.button(_t("btn_stop_config"), use_container_width=True, key="btn_stop_config"):
                st.session_state.cancel_search     = True
                st.session_state.cancel_and_config = True
                st.session_state.is_searching      = False
                st.rerun()
    else:
        # ── Botón normal ──────────────────────────────────────────────────────
        c_l, c_btn, c_r = st.columns([2, 1.2, 2])
        with c_btn:
            _label = _t("btn_new_search") if st.session_state.search_done else _t("btn_config_search")
            if st.button(_label, type="primary", use_container_width=True):
                st.session_state.show_dialog = True
                st.session_state.config_step = 1
                st.rerun()
        if not st.session_state.search_done:
            st.markdown(
                f'<p style="text-align:center;font-size:13px;color:var(--t3);margin-top:.5rem;"'
                f' data-i18n="search_time_hint">{_t("search_time_hint")}</p>',
                unsafe_allow_html=True,
            )

if not st.session_state.run_search and not st.session_state.search_done:
    render_empty_state()

# ─── Ejecución de la búsqueda ─────────────────────────────────────────────────
if st.session_state.run_search:
    st.session_state.run_search    = False
    st.session_state.cancel_search = False
    # is_searching ya fue seteado a True en el wizard antes del rerun
    empty_state_placeholder.empty()
    results_placeholder.empty()

    gemini_key        = st.session_state.gemini_key
    selected_model    = st.session_state.selected_model
    send_email        = st.session_state.send_email
    email_sender      = st.session_state.email_sender
    email_password    = st.session_state.email_password_raw.replace(" ", "")
    email_recipient   = st.session_state.email_recipient
    keywords          = list(st.session_state.keywords_list)
    min_score         = st.session_state.min_score
    max_results_limit = st.session_state.max_results_limit if st.session_state.use_max_results else 0
    candidate_profile = st.session_state.candidate_profile
    browser_profile_dir = st.session_state.browser_profile_dir

    os.environ["GEMINI_API_KEY"]  = gemini_key
    os.environ["EMAIL_SENDER"]    = email_sender
    os.environ["EMAIL_PASSWORD"]  = email_password
    os.environ["EMAIL_RECIPIENT"] = email_recipient

    st.session_state.result_page     = 0
    st.session_state.result_page_all = 0

    import config as cfg
    cfg.GEMINI_API_KEY    = gemini_key
    cfg.SEARCH_KEYWORDS   = keywords
    cfg.MIN_MATCH_SCORE   = min_score
    cfg.CANDIDATE_PROFILE = candidate_profile
    cfg.ONLY_REMOTE       = st.session_state.only_remote
    cfg.EMAIL_SENDER      = email_sender
    cfg.EMAIL_PASSWORD    = email_password
    cfg.EMAIL_RECIPIENT   = email_recipient

    import ai_engine
    ai_engine.MODEL = selected_model
    from google import genai as _genai
    ai_engine.client = _genai.Client(api_key=gemini_key)

    import scrapers as sc

    def render_workflow_step(step_number, step_title):
        with workflow_placeholder.container():
            with st.container(border=True):
                st.caption(_t("wf_step_label", n=step_number, title=step_title))
                status   = st.empty()
                notice   = st.empty()
                progress = st.empty()
                extra    = st.empty()
        return status, notice, progress, extra

    # ── STEP 1: Scraping ──────────────────────────────────────────────────────
    platform_status, platform_notice, progress_scrape, _ = render_workflow_step(1, _t("wf_step1_title"))
    progress_scrape.progress(0, text=_t("wf_starting"))

    all_jobs    = []
    seen_global = set()
    platforms_enabled = {
        "Remotive":       st.session_state.use_remotive,
        "Arbeitnow":      st.session_state.use_arbeitnow,
        "WeWorkRemotely": st.session_state.use_wwr,
        "Himalayas":      st.session_state.use_himalayas,
        "RemoteOK":       st.session_state.use_remoteok,
        "Jobicy":         st.session_state.use_jobicy,
        "GetOnBoard":     st.session_state.use_getonboard,
        "PuenteTalent":   st.session_state.use_puentetalent,
        "LatoJobs":       st.session_state.use_latojobs,
        "WorkingNomads":  st.session_state.use_workingnomads,
        "TheMuse":        st.session_state.use_themuse,
        "Remote.co":      st.session_state.use_remoteco,
        "Jobspresso":     st.session_state.use_jobspresso,
        "JustJoin.it":    st.session_state.use_justjoinit,
        "AuthenticJobs":  st.session_state.use_authenticjobs,
        # Portales con login — activos solo en entorno local
        "LinkedInBrowser":     False if IS_CLOUD else st.session_state.use_linkedin_browser,
        "BumeranBrowser":      False if IS_CLOUD else st.session_state.use_bumeran_browser,
        "ComputrabajoBrowser": False if IS_CLOUD else st.session_state.use_computrabajo_browser,
        "IndeedBrowser":       False if IS_CLOUD else st.session_state.use_indeed_browser,
    }
    enabled_list    = [p for p, v in platforms_enabled.items() if v]
    total_platforms = len(enabled_list)
    scrape_started  = time.monotonic()

    for idx, platform_name in enumerate(enabled_list):
        platform_status.info(_t("wf_searching", platform=platform_name))
        if max_results_limit > 0 and len(all_jobs) >= max_results_limit:
            break
        try:
            remaining = max_results_limit - len(all_jobs) if max_results_limit > 0 else 0
            if platform_name == "Remotive":
                jobs = sc.scrape_remotive(keywords, max_results=remaining)
            elif platform_name == "Arbeitnow":
                jobs = sc.scrape_arbeitnow(keywords, max_results=remaining)
            elif platform_name == "WeWorkRemotely":
                jobs = sc.scrape_weworkremotely(keywords, max_results=remaining)
            elif platform_name == "Himalayas":
                jobs = sc.scrape_himalayas(keywords, max_results=remaining)
            elif platform_name == "RemoteOK":
                jobs = sc.scrape_remoteok(keywords, max_results=remaining)
            elif platform_name == "Jobicy":
                jobs = sc.scrape_jobicy(keywords, max_results=remaining)
            elif platform_name == "GetOnBoard":
                jobs = sc.scrape_getonboard(keywords, max_results=remaining)
            elif platform_name == "PuenteTalent":
                jobs = sc.scrape_puente(keywords, max_results=remaining)
            elif platform_name == "LatoJobs":
                jobs = sc.scrape_latojobs(keywords, max_results=remaining)
            elif platform_name in ("LinkedInBrowser", "BumeranBrowser", "ComputrabajoBrowser", "IndeedBrowser"):
                import browser_scrapers as bsc
                jobs = bsc.scrape_browser_portal(
                    platform_name,
                    keywords,
                    profile_dir=browser_profile_dir,
                    max_results=remaining,
                )
            elif platform_name == "WorkingNomads":
                jobs = sc.scrape_workingnomads(keywords, max_results=remaining)
            elif platform_name == "TheMuse":
                jobs = sc.scrape_themuse(keywords, max_results=remaining)
            elif platform_name == "Remote.co":
                jobs = sc.scrape_remoteco(keywords, max_results=remaining)
            elif platform_name == "Jobspresso":
                jobs = sc.scrape_jobspresso(max_results=remaining)
            elif platform_name == "JustJoin.it":
                jobs = sc.scrape_justjoinit(keywords, max_results=remaining)
            elif platform_name == "AuthenticJobs":
                jobs = sc.scrape_authenticjobs(max_results=remaining)
            else:
                jobs = []
            for job in jobs:
                key = f"{job.title.lower()[:40]}|{job.company.lower()[:30]}"
                if key not in seen_global:
                    seen_global.add(key)
                    all_jobs.append(job)
                if max_results_limit > 0 and len(all_jobs) >= max_results_limit:
                    break
        except Exception as e:
            platform_notice.warning(_t("wf_err_platform", platform=platform_name, error=e))

        completed = idx + 1
        elapsed   = time.monotonic() - scrape_started
        rem_plat  = total_platforms - completed
        eta       = _t("wf_eta", time=format_duration((elapsed / completed) * rem_plat)) if rem_plat > 0 else ""
        progress_scrape.progress(completed / total_platforms, text=_t("wf_src_prog", done=completed, total=total_platforms, eta=eta))

        # ── Check cancelación entre plataformas ───────────────────────────────
        if st.session_state.cancel_search:
            platform_status.warning(_t("wf_stopped", n=completed, jobs=len(all_jobs)))
            break

    if not st.session_state.cancel_search:
        platform_status.success(_t("wf_found", jobs=len(all_jobs), time=format_duration(time.monotonic() - scrape_started)))
    progress_scrape.progress(1.0)

    # ── STEP 2: AI Scoring ────────────────────────────────────────────────────
    ai_status, ai_notice, progress_ai, live_results = render_workflow_step(2, _t("wf_step2_title"))

    scored_jobs    = []
    top_matches    = []
    quota_exceeded = False
    st.session_state.scored_jobs = []
    st.session_state.top_matches = []
    total_jobs     = len(all_jobs)

    if total_jobs == 0:
        ai_status.warning(_t("wf_no_jobs"))
        progress_ai.progress(1.0)
    else:
        progress_ai.progress(0, text=_t("wf_starting"))
        scoring_started = time.monotonic()

        for i, job in enumerate(all_jobs):
            ai_status.info(_t("wf_scoring", i=i+1, n=total_jobs, title=job.title[:50], company=job.company))
            data  = ai_engine.score_job(job)
            score = data.get("score", 0)
            if data.get("quota_exceeded", False):
                quota_exceeded = True
                ai_notice.error(_t("wf_quota", i=i, n=total_jobs))
                break

            from ai_engine import ScoredJob
            sj = ScoredJob(
                job=job, score=score,
                match_reasons=data.get("match_reasons", []),
                missing_skills=data.get("missing_skills", []),
                cover_letter=None,
                summary=data.get("summary", ""),
            )
            scored_jobs.append(sj)

            top5 = sorted(scored_jobs, key=lambda x: x.score, reverse=True)[:5]
            with live_results.container():
                st.markdown(f'<div style="font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--t3);margin-bottom:6px;" data-i18n="wf_best_label">{_t("wf_best_label")}</div>', unsafe_allow_html=True)
                for t in top5:
                    sc = "jh-score-hi" if t.score >= 80 else "jh-score-md" if t.score >= 60 else "jh-score-lo"
                    import html as _h
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid var(--b1);">'
                        f'<span class="jh-score {sc}">{t.score}/100</span>'
                        f'<span style="font-size:13px;color:var(--t1);font-weight:500;">{_h.escape(t.job.title[:45])}</span>'
                        f'<span style="font-size:12px;color:var(--t3);">@ {_h.escape(t.job.company[:25])}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            completed = i + 1
            elapsed   = time.monotonic() - scoring_started
            rem_jobs  = total_jobs - completed
            eta       = _t("wf_eta", time=format_duration((elapsed / completed) * rem_jobs)) if rem_jobs > 0 else ""
            progress_ai.progress(completed / total_jobs, text=_t("wf_ai_prog", done=completed, total=total_jobs, eta=eta))
            time.sleep(0.1)

        scored_jobs.sort(key=lambda x: x.score, reverse=True)
        top_matches = [j for j in scored_jobs if j.score >= min_score]
        st.session_state.scored_jobs = scored_jobs
        st.session_state.top_matches = top_matches
        st.session_state.min_score_last = min_score
        if not quota_exceeded:
            ai_status.success(_t("wf_scored", top=len(top_matches), total=len(scored_jobs), time=format_duration(time.monotonic() - scoring_started)))
        progress_ai.progress(1.0)

    # ── STEP 3: Cover Letters ─────────────────────────────────────────────────
    if top_matches:
        cl_status, _, progress_cl, _ = render_workflow_step(3, _t("wf_step3_title"))
        progress_cl.progress(0, text=_t("wf_starting"))
        cover_started = time.monotonic()
        total_letters = len(top_matches)

        for i, sj in enumerate(top_matches):
            cl_status.info(_t("wf_letter", i=i+1, n=total_letters, title=sj.job.title))
            sj.cover_letter = ai_engine.generate_cover_letter(sj.job, {"match_reasons": sj.match_reasons})
            completed = i + 1
            elapsed   = time.monotonic() - cover_started
            rem_let   = total_letters - completed
            eta       = _t("wf_eta", time=format_duration((elapsed / completed) * rem_let)) if rem_let > 0 else ""
            progress_cl.progress(completed / total_letters, text=_t("wf_let_prog", done=completed, total=total_letters, eta=eta))

        _letter_word = _t("wf_letter_1") if total_letters == 1 else _t("wf_letter_n")
        cl_status.success(f"✅ {total_letters} {_letter_word} — {format_duration(time.monotonic() - cover_started)}")
        progress_cl.progress(1.0)

    # ── STEP 4: Email ─────────────────────────────────────────────────────────
    if send_email and top_matches and email_sender and email_password:
        email_status, _, _, _ = render_workflow_step(4, _t("wf_step4_title"))
        try:
            from notifier import send_digest
            cfg.EMAIL_SENDER    = email_sender
            cfg.EMAIL_PASSWORD  = email_password
            cfg.EMAIL_RECIPIENT = email_recipient
            cfg.EMAIL_SENDER    = email_sender
            cfg.EMAIL_PASSWORD  = email_password
            cfg.EMAIL_RECIPIENT = email_recipient
            email_status.info(_t("wf_email_sending", recipient=email_recipient))
            send_digest(scored_jobs)
            email_status.success(_t("wf_email_sent", recipient=email_recipient))
        except Exception as e:
            email_status.error(_t("wf_email_error", error=e))

    workflow_placeholder.empty()

    # ── Guardar resultados ────────────────────────────────────────────────────
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    ts          = datetime.now().strftime("%Y%m%d_%H%M")
    result_file = results_dir / f"results_{ts}.json"
    data_out    = [
        {
            "score":            sj.score,
            "title":            sj.job.title,
            "company":          sj.job.company,
            "source":           sj.job.source,
            "url":              sj.job.url,
            "match_reasons":    sj.match_reasons,
            "summary":          sj.summary,
            "has_cover_letter": sj.cover_letter is not None,
        }
        for sj in scored_jobs
    ]
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(data_out, f, ensure_ascii=False, indent=2)

    st.session_state.search_done  = True
    st.session_state.is_searching = False
    st.session_state.cancel_search = False

# ── Renderizado de resultados ────────────────────────────────────────────────
if st.session_state.search_done and st.session_state.scored_jobs:
    _scored   = st.session_state.scored_jobs
    _top      = st.session_state.top_matches
    _minscore = st.session_state.min_score_last

    with results_placeholder.container():
        import html as _html

        exc = sum(1 for j in _scored if j.score >= 80)
        st.markdown(f"""
<div class="jh-metrics">
  <div class="jh-metric">
    <div class="jh-metric-val">{len(_scored)}</div>
    <div class="jh-metric-lbl" data-i18n="metric_analyzed">{_t("metric_analyzed")}</div>
  </div>
  <div class="jh-metric">
    <div class="jh-metric-val">{len(_top)}</div>
    <div class="jh-metric-lbl" data-i18n="metric_recommended">{_t("metric_recommended")}</div>
  </div>
  <div class="jh-metric">
    <div class="jh-metric-val">{_scored[0].score if _scored else "—"}<span style="font-size:1rem;font-weight:500;color:var(--t3)">/100</span></div>
    <div class="jh-metric-lbl" data-i18n="metric_best">{_t("metric_best")}</div>
  </div>
  <div class="jh-metric">
    <div class="jh-metric-val">{exc}</div>
    <div class="jh-metric-lbl" data-i18n="metric_excellent">{_t("metric_excellent")}</div>
  </div>
</div>
""", unsafe_allow_html=True)

        def _score_cls(s):
            return "jh-score-hi" if s >= 80 else "jh-score-md" if s >= 60 else "jh-score-lo"

        def _src_cls(source):
            return "src-" + source.replace(" ", "-").replace(".", "-")

        def render_job_card(sj, idx, section):
            score = sj.score
            sc    = _score_cls(score)
            src   = _src_cls(sj.job.source)

            badges = (
                f'<span class="jh-score {sc}">{score}/100</span> '
                f'<span class="jh-src {src}">{sj.job.source}</span>'
            )
            if getattr(sj.job, "remote", False):
                badges += f' <span class="jh-tag jh-tag-green" style="height:20px;font-size:11px;" data-i18n="remote_tag">{_t("remote_tag")}</span>'
            if getattr(sj.job, "location", "") and not getattr(sj.job, "remote", False):
                loc = _html.escape(sj.job.location[:30])
                badges += f' <span class="jh-tag jh-tag-gray" style="height:20px;font-size:11px;">{loc}</span>'

            label = f"{score}/100 — {sj.job.title} @ {sj.job.company}"
            with st.expander(label, expanded=(idx == 0)):
                hcol, lcol = st.columns([4, 1])
                with hcol:
                    st.markdown(
                        f'<div class="jh-job-badges">{badges}</div>'
                        f'<div class="jh-job-title">{_html.escape(sj.job.title)}</div>'
                        f'<div class="jh-job-co">{_html.escape(sj.job.company)}</div>',
                        unsafe_allow_html=True,
                    )
                with lcol:
                    if sj.job.url:
                        st.link_button(_t("offer_link"), sj.job.url, use_container_width=True)

                if sj.summary:
                    st.markdown(
                        f'<div class="jh-job-summary">{_html.escape(sj.summary)}</div>',
                        unsafe_allow_html=True,
                    )

                st.markdown('<div style="height:.6rem;"></div>', unsafe_allow_html=True)

                r1, r2 = st.columns(2)
                with r1:
                    st.markdown(f'<div class="jh-col-lbl" data-i18n="why_fits">{_t("why_fits")}</div>', unsafe_allow_html=True)
                    if sj.match_reasons:
                        for reason in sj.match_reasons:
                            st.markdown(f'<div class="jh-reason">{_html.escape(reason)}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<span style="font-size:13px;color:var(--t3)" data-i18n="no_reasons">{_t("no_reasons")}</span>', unsafe_allow_html=True)
                with r2:
                    st.markdown(f'<div class="jh-col-lbl" data-i18n="what_missing">{_t("what_missing")}</div>', unsafe_allow_html=True)
                    if sj.missing_skills:
                        for skill in sj.missing_skills:
                            st.markdown(f'<div class="jh-reason jh-skill">{_html.escape(skill)}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<span style="font-size:13px;color:var(--t3)" data-i18n="no_missing">{_t("no_missing")}</span>', unsafe_allow_html=True)

                if sj.cover_letter:
                    st.markdown('<div style="height:.5rem;"></div>', unsafe_allow_html=True)
                    with st.expander(_t("cover_letter_expander")):
                        st.markdown(
                            f'<div class="jh-letter">{_html.escape(sj.cover_letter)}</div>',
                            unsafe_allow_html=True,
                        )
                        st.download_button(
                            _t("btn_download_letter"),
                            data=sj.cover_letter,
                            file_name=f"cover_{sj.job.company.replace(' ','_')}_{sj.job.title[:20].replace(' ','_')}.txt",
                            mime="text/plain",
                            key=f"dl_{section}_{sj.job.id}_{idx}",
                        )

        PAGE_SIZE = 15
        _PAGE_KEYS = {"top": "result_page", "all": "result_page_all"}

        def render_paginated(job_list: list, section: str):
            if not job_list:
                return
            page_key = _PAGE_KEYS[section]
            total    = len(job_list)
            pages    = max(1, -(-total // PAGE_SIZE))
            page     = min(st.session_state[page_key], pages - 1)
            start    = page * PAGE_SIZE
            end      = min(start + PAGE_SIZE, total)

            st.caption(_t("showing_range", start=start + 1, end=end, total=total))
            for i, sj in enumerate(job_list[start:end]):
                render_job_card(sj, start + i, section)

            if pages > 1:
                p_left, p_info, p_right = st.columns([1, 2, 1])
                with p_left:
                    if st.button(_t("btn_prev"), disabled=(page == 0), key=f"prev_{section}", use_container_width=True):
                        st.session_state[page_key] = page - 1
                        st.rerun()
                with p_info:
                    st.markdown(
                        f'<div style="text-align:center;padding-top:6px;color:var(--t3);font-size:14px;">'
                        f'{_t("page_of", page=page + 1, pages=pages)}</div>',
                        unsafe_allow_html=True,
                    )
                with p_right:
                    if st.button(_t("btn_next"), disabled=(page >= pages - 1), key=f"next_{section}", use_container_width=True):
                        st.session_state[page_key] = page + 1
                        st.rerun()

        top_tab, all_tab = st.tabs([
            f"{_t('tab_recommended')}  {len(_top)}",
            f"{_t('tab_all')}  {len(_scored)}",
        ])
        with top_tab:
            if _top:
                render_paginated(_top, "top")
            else:
                st.info(_t("no_recommended", score=_minscore))
        with all_tab:
            st.caption(_t("all_tab_caption"))
            render_paginated(_scored, "all")

        _results_files = sorted(Path("results").glob("results_*.json"), reverse=True)
        if _results_files:
            _data_raw = _results_files[0].read_text(encoding="utf-8")
            st.download_button(
                _t("btn_download_json"),
                data=_data_raw,
                file_name=_results_files[0].name,
                mime="application/json",
            )
