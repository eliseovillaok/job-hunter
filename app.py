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

from browser_scrapers import default_profile_dir
import ai_engine
import candidate as cand
import matching
import normalize
from candidate import SENIORITY_LEVELS, CandidateProfile

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
    "selected_model":     ai_engine.DEFAULT_MODEL,
    "send_email":         False,
    "email_sender":       "",
    "email_password_raw": "",
    "email_recipient":    "",
    "keywords_list":      [],
    "kw_options":         [],
    "min_score":          65,
    # Preferencias (filtros duros). Vacío = cualquiera.
    "pref_modalities":    [],
    "pref_locations":     "",
    "pref_languages":     [],
    "eval_limit":         matching.DEFAULT_TOP_N,   # ofertas que evalúa el LLM
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
    "browser_profile_dir":       default_profile_dir(),
    "use_workingnomads":  True,
    "use_themuse":        True,
    "use_remoteco":       True,
    "use_jobspresso":     True,
    "use_justjoinit":     False,
    "use_authenticjobs":  True,
    "result_page":        0,
    "result_page_all":    0,
    "profile":            None,   # CandidateProfile.to_dict()
    "funnel":             None,   # resumen de la última búsqueda (transparencia)
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

# ─── Preferencias visuales: query params → session_state (solo al iniciar) ───
# La URL (?lang=en&theme=dark) conserva las preferencias al recargar o compartir.
if "_prefs_loaded" not in st.session_state:
    st.session_state._prefs_loaded = True
    _qp = st.query_params
    _lv = _qp.get("lang")
    if _lv not in ("es", "en"):
        # Sin preferencia explícita: idioma del navegador (inglés o español).
        _locale = (getattr(st.context, "locale", None) or "es").lower()
        _lv = "en" if _locale.startswith("en") else "es"
    st.session_state.lang = _lv
    st.session_state.dark_mode = (_qp.get("theme") == "dark")

# ─── Traducciones / Translations ─────────────────────────────────────────────
TRANSLATIONS: dict[str, dict[str, str]] = {
    "es": {
        # Fase 1 — perfil, preferencias, matching
        "val_no_profile":      "Completá tu perfil (analizá tu CV o escribilo en el paso 4).",
        "prof_title":          "**👤 Tu perfil, según tu CV**",
        "prof_caption":        "Revisalo y corregí lo que haga falta: la IA evalúa las ofertas contra esto. Lo que tu CV no dice queda como no especificado.",
        "prof_summary":        "Resumen",
        "prof_roles":          "Roles",
        "prof_roles_help":     "Roles que aparecen en tu CV. Podés agregar o quitar.",
        "prof_seniority":      "Seniority",
        "prof_years":          "Años de experiencia",
        "prof_years_help":     "Vacío = tu CV no lo especifica.",
        "prof_location":       "Ubicación",
        "prof_languages":      "Idiomas",
        "prof_languages_help": "Formato: Idioma (nivel). Ej: Inglés (intermedio)",
        "prof_skills":         "Habilidades y conocimientos",
        "prof_unknown":        "No especificado en el CV",
        "prof_added_by_user":  "Agregado por vos",
        "prof_evidence":       "Ver en qué parte del CV se basa cada dato",
        "prof_preview":        "Ver el perfil tal como lo lee la IA",
        "prof_notes":          "¿Algo más que la IA deba tener en cuenta? (opcional)",
        "step4_caption_structured": "Tu perfil viene del CV (lo podés editar en el paso 2). Acá podés sumar aclaraciones.",
        "sen_intern":          "Pasante / Trainee",
        "sen_junior":          "Junior",
        "sen_mid":             "Semi senior",
        "sen_senior":          "Senior",
        "sen_lead":            "Lead / Jefatura",
        "sen_unknown":         "No especificado",
        "pref_caption":        "Filtros: las ofertas que no cumplan no se evalúan. Si un dato no se puede detectar en la oferta, la oferta no se descarta.",
        "pref_any":            "Cualquiera",
        "pref_modality":       "Modalidad",
        "pref_modality_help":  "Vacío = cualquiera.",
        "pref_locations":      "Ubicaciones aceptadas (presencial o híbrido)",
        "pref_locations_ph":   "Ej: Buenos Aires, Córdoba",
        "pref_locations_help": "Separadas por coma. No afecta a las ofertas remotas. Vacío = cualquiera.",
        "pref_languages":      "Idioma de las ofertas",
        "pref_languages_help": "Vacío = cualquiera. Se sugiere según los idiomas de tu CV.",
        "mod_remote":          "Remoto",
        "mod_hybrid":          "Híbrido",
        "mod_onsite":          "Presencial",
        "lang_es":             "Español",
        "lang_en":             "Inglés",
        "lang_pt":             "Portugués",
        "lang_de":             "Alemán",
        "lang_fr":             "Francés",
        "eval_limit_label":    "Ofertas a evaluar con IA",
        "eval_limit_help":     "Se evalúan las más parecidas a tu perfil. Más ofertas = más tiempo y más cuota de Gemini.",
        "wf_preparing":        "Quitando duplicados, aplicando tus filtros y eligiendo las {n} ofertas más parecidas a tu perfil…",
        "wf_evaluating":       "Evaluando con IA: {done}/{total}",
        "wf_rechecking":       "Revisando en detalle las mejores: {done}/{total}",
        "wf_quota_stop":       "Se agotó la cuota de Gemini: algunas ofertas quedaron sin evaluar.",
        "wf_all_filtered":     "Ninguna oferta pasó tus filtros. Probá ampliar modalidad, idioma o ubicación.",
        "wf_emb_failed":       "No se pudo usar el pre-ranking semántico: se evaluaron las primeras {n} ofertas.",
        "funnel":              "Encontradas {found} · duplicadas {dups} · descartadas por tus filtros {filtered} (modalidad {mod}, idioma {lang}, ubicación {loc}) · fuera del top {n}: {out} · evaluadas {evaluated}",
        "factors_title":       "Desglose del puntaje",
        "factors_note":        "El puntaje final lo calcula el sistema con pesos fijos a partir de estos factores. Es una estimación de la IA, no una medición.",
        "f_skills":            "Habilidades",
        "f_seniority":         "Seniority",
        "f_role":              "Rol",
        "f_language":          "Idioma",
        "f_location":          "Ubicación",
        "f_weight":            "peso {w}%",
        "f_job":               "Oferta:",
        "f_cv":                "Tu CV:",
        # Fase 0
        "showing_range":       "Mostrando {start}–{end} de {total}",
        "cv_error":            "No se pudo analizar el CV: {error}",
        "not_evaluated":       "No evaluada",
        "uneval_note":         "{n} ofertas no pudieron evaluarse (error de la IA o cuota agotada). Aparecen al final, sin puntaje.",
        "btn_gen_letter":      "✍️ Generar carta de presentación",
        "letter_generating":   "Generando carta…",
        "letter_error":        "No se pudo generar la carta: {error}",
        "wf_email_title":      "Enviar resumen por email",
        "lang_label":          "Idioma",
        "theme_label":         "Tema",
        "wf_auth_error":       "La API key de Gemini no es válida o no tiene permisos. Revisala en la configuración.",
        "none_evaluated":      "No se pudo evaluar ninguna oferta. Revisá tu API key y tu cuota de Gemini.",
        "wiz_close_help":      "Cierra el formulario sin ejecutar la búsqueda.",
        "help_gemini_steps":   "1. Ir a [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)\n2. Iniciar sesión con Google → **Create API Key**\n3. Copiar la clave — es gratis, no requiere tarjeta.",
        "help_gmail_steps":    "1. Ir a [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)\n2. Tener la verificación en 2 pasos **activada**\n3. Crear la app `Job Hunter` → copiar los 16 caracteres",
        "ph_email_sender":     "tu@gmail.com",
        "ph_email_recip":      "destino@gmail.com",
        # Hero — estado inicial
        "hero_eyebrow_search":  "Búsqueda de empleo con IA",
        "hero_title_search":    "Encontrá el trabajo que realmente encaja.",
        "hero_sub_search":      "Subí tu CV: Job Hunter busca ofertas en {n} portales, las puntúa contra tu perfil real y te explica por qué encaja cada una.",
        "hero_note_search":     "Tu CV y tu API key se usan solo durante esta sesión, para buscar y evaluar ofertas con Google Gemini. No se guardan.",
        "hero_tag_scoring":     "Scoring con IA",
        "hero_tag_multi":       "Múltiples portales",
        "hero_tag_letters":     "Cartas a pedido",
        "hero_tag_local":       "Sin inflar tu perfil",
        "hero_stat_sources":    "portales disponibles",
        "hero_stat_score":      "score por oferta",
        "hero_stat_ai":         "lo único que necesitás",
        "hero_stat_time":       "idiomas",
        # Hero — resultados
        "hero_eyebrow_results": "Panel de resultados",
        "hero_title_results":   "Tus oportunidades, priorizadas.",
        "hero_sub_results":     "La IA evaluó cada oferta contra tu perfil. Las recomendadas están en la pestaña de abajo, ordenadas por score.",
        "hero_note_results":    "Resultados listos. Generá cartas solo para las ofertas que te interesen.",
        "hero_tag_done":        "Búsqueda completada",
        "hero_stat_analyzed":   "analizadas",
        "hero_stat_rec":        "recomendadas",
        "hero_stat_best":       "mejor score",
        "hero_stat_threshold":  "umbral",
        # Empty state
        "empty_label":  "Cómo funciona",
        "empty_title":  "Un flujo de 4 pasos, sin ruido visual.",
        "empty_copy":   "Subís tu CV, lanzás la búsqueda y recibís ofertas ordenadas por relevancia, con el porqué de cada puntaje.",
        "feat1_title":  "Descubrí",
        "feat1_desc":   "Remotive, Get on Board, Himalayas, LatoJobs, WeWorkRemotely y 10+ fuentes más en una sola búsqueda.",
        "feat2_title":  "Priorizá",
        "feat2_desc":   "La IA puntúa cada oferta del 0 al 100 comparando el job description con tu perfil real. Sin inflado de seniority.",
        "feat3_title":  "Redactá",
        "feat3_desc":   "Pedí una carta de presentación para la oferta que elijas, en el idioma del aviso y basada solo en tu CV.",
        "feat4_title":  "Actuá",
        "feat4_desc":   "Descargá las cartas, exportá los resultados como JSON o recibí un resumen por email.",
        # Botones de acción
        "searching_notice": "La búsqueda está en curso — podés detenerla en cualquier momento.",
        "btn_stop":          "Detener",
        "btn_stop_config":   "Detener & Configurar",
        "btn_new_search":    "Nueva búsqueda",
        "btn_config_search": "Configurar búsqueda",
        "search_time_hint":  "La duración depende de cuántos portales y ofertas incluyas. Podés detener la búsqueda en cualquier momento.",
        # Resultados
        "tab_recommended":       "Recomendadas",
        "tab_all":               "Todas",
        "metric_analyzed":       "Analizadas",
        "metric_recommended":    "Recomendadas",
        "metric_best":           "Mejor score",
        "metric_excellent":      "Excelentes 80+",
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
        "btn_back":        "← Atrás",
        "toast_cv_ok":     "✅ {n} keywords extraídas. Revisalas en el paso siguiente.",
        "toast_cv_err":    "No se pudo analizar el CV. Continuá y completá los datos a mano.",
        # Paso 3
        "step3_header":        "**🔍 Keywords de búsqueda**",
        "step3_kw_ph":         "Tus keywords — × para quitar",
        "step3_add_ph":        "Agregar keyword...",
        "step3_add_btn":       "+ Agregar",
        "step3_params":        "**⚙️ Parámetros**",
        "step3_score_label":   "Puntaje mínimo para 'Recomendadas'",
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
        "toast_no_kw":         "Agregá al menos una keyword.",
        "toast_no_src":        "Seleccioná al menos una fuente.",
        # Paso 4
        "step4_header":    "**👤 Tu perfil profesional**",
        "step4_caption":   "La IA usa este texto para evaluar qué tan bien encaja cada oferta con vos.",
        "step4_ph":        "Rol buscado, experiencia, formación, habilidades, idiomas...",
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
        "wf_starting":     "Iniciando...",
        "wf_searching":    "Buscando en **{platform}**...",
        "wf_stopped":      "⏹️ Búsqueda detenida por el usuario tras {n} fuente(s) — {jobs} ofertas encontradas hasta ahora.",
        "wf_found":        "✅ **{jobs} ofertas únicas** encontradas — {time}",
        "wf_no_jobs":      "No se encontraron ofertas para analizar.",
        "wf_scored":       "✅ **{top} recomendadas** de {total} analizadas — {time}",
        "wf_email_send":   "Enviando resumen a {recipient}...",
        "wf_email_ok":     "✅ Resumen enviado a **{recipient}**.",
        "wf_email_err":    "No se pudo enviar el email: {error}",
        "wf_src_prog":     "{done}/{total} fuentes{eta}",
        "wf_ai_prog":      "{done}/{total} analizadas{eta}",
        "wf_eta":          "  ·  ~{time} restantes",
        "wf_err_platform": "⚠️ Error en {platform}: {error}",
    },
    "en": {
        # Phase 1 — profile, preferences, matching
        "val_no_profile":      "Complete your profile (analyze your CV or write it in step 4).",
        "prof_title":          "**👤 Your profile, according to your CV**",
        "prof_caption":        "Review it and fix anything that's off: the AI evaluates listings against this. Anything your CV doesn't state stays as not specified.",
        "prof_summary":        "Summary",
        "prof_roles":          "Roles",
        "prof_roles_help":     "Roles found in your CV. You can add or remove them.",
        "prof_seniority":      "Seniority",
        "prof_years":          "Years of experience",
        "prof_years_help":     "Empty = your CV doesn't state it.",
        "prof_location":       "Location",
        "prof_languages":      "Languages",
        "prof_languages_help": "Format: Language (level). E.g. English (intermediate)",
        "prof_skills":         "Skills and knowledge",
        "prof_unknown":        "Not specified in the CV",
        "prof_added_by_user":  "Added by you",
        "prof_evidence":       "See which part of your CV supports each item",
        "prof_preview":        "See the profile as the AI reads it",
        "prof_notes":          "Anything else the AI should consider? (optional)",
        "step4_caption_structured": "Your profile comes from your CV (you can edit it in step 2). Add any clarifications here.",
        "sen_intern":          "Intern / Trainee",
        "sen_junior":          "Junior",
        "sen_mid":             "Mid-level",
        "sen_senior":          "Senior",
        "sen_lead":            "Lead / Management",
        "sen_unknown":         "Not specified",
        "pref_caption":        "Filters: listings that don't match are not evaluated. If a listing's data can't be detected, it is not discarded.",
        "pref_any":            "Any",
        "pref_modality":       "Work mode",
        "pref_modality_help":  "Empty = any.",
        "pref_locations":      "Accepted locations (on-site or hybrid)",
        "pref_locations_ph":   "E.g. Buenos Aires, Córdoba",
        "pref_locations_help": "Comma-separated. Doesn't affect remote listings. Empty = any.",
        "pref_languages":      "Listing language",
        "pref_languages_help": "Empty = any. Suggested from the languages in your CV.",
        "mod_remote":          "Remote",
        "mod_hybrid":          "Hybrid",
        "mod_onsite":          "On-site",
        "lang_es":             "Spanish",
        "lang_en":             "English",
        "lang_pt":             "Portuguese",
        "lang_de":             "German",
        "lang_fr":             "French",
        "eval_limit_label":    "Listings to evaluate with AI",
        "eval_limit_help":     "The ones most similar to your profile are evaluated. More listings = more time and more Gemini quota.",
        "wf_preparing":        "Removing duplicates, applying your filters and picking the {n} listings most similar to your profile…",
        "wf_evaluating":       "Evaluating with AI: {done}/{total}",
        "wf_rechecking":       "Reviewing the best ones in detail: {done}/{total}",
        "wf_quota_stop":       "Gemini quota exhausted: some listings were not evaluated.",
        "wf_all_filtered":     "No listing passed your filters. Try widening work mode, language or location.",
        "wf_emb_failed":       "Semantic pre-ranking was unavailable: the first {n} listings were evaluated.",
        "funnel":              "Found {found} · duplicates {dups} · excluded by your filters {filtered} (work mode {mod}, language {lang}, location {loc}) · outside the top {n}: {out} · evaluated {evaluated}",
        "factors_title":       "Score breakdown",
        "factors_note":        "The final score is computed by the system with fixed weights from these factors. It is an AI estimate, not a measurement.",
        "f_skills":            "Skills",
        "f_seniority":         "Seniority",
        "f_role":              "Role",
        "f_language":          "Language",
        "f_location":          "Location",
        "f_weight":            "weight {w}%",
        "f_job":               "Listing:",
        "f_cv":                "Your CV:",
        # Phase 0
        "showing_range":       "Showing {start}–{end} of {total}",
        "cv_error":            "Could not analyze the CV: {error}",
        "not_evaluated":       "Not evaluated",
        "uneval_note":         "{n} listings could not be evaluated (AI error or quota exhausted). They are listed last, without a score.",
        "btn_gen_letter":      "✍️ Generate cover letter",
        "letter_generating":   "Generating letter…",
        "letter_error":        "Could not generate the letter: {error}",
        "wf_email_title":      "Send summary by email",
        "lang_label":          "Language",
        "theme_label":         "Theme",
        "wf_auth_error":       "The Gemini API key is invalid or lacks permissions. Check it in the settings.",
        "none_evaluated":      "No listing could be evaluated. Check your Gemini API key and quota.",
        "wiz_close_help":      "Closes the form without running the search.",
        "help_gemini_steps":   "1. Go to [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)\n2. Sign in with Google → **Create API Key**\n3. Copy the key — it is free, no card required.",
        "help_gmail_steps":    "1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)\n2. Make sure 2-Step Verification is **on**\n3. Create the `Job Hunter` app → copy the 16 characters",
        "ph_email_sender":     "you@gmail.com",
        "ph_email_recip":      "recipient@gmail.com",
        # Hero — initial state
        "hero_eyebrow_search":  "AI-Powered Job Search",
        "hero_title_search":    "Find the job that truly fits.",
        "hero_sub_search":      "Upload your CV: Job Hunter searches {n} portals, scores every listing against your real profile, and explains why each one fits.",
        "hero_note_search":     "Your CV and API key are used only during this session, to search and evaluate listings with Google Gemini. They are not stored.",
        "hero_tag_scoring":     "AI Scoring",
        "hero_tag_multi":       "Multi-source",
        "hero_tag_letters":     "On-demand letters",
        "hero_tag_local":       "No profile inflation",
        "hero_stat_sources":    "available portals",
        "hero_stat_score":      "score per listing",
        "hero_stat_ai":         "all you need",
        "hero_stat_time":       "languages",
        # Hero — results
        "hero_eyebrow_results": "Results Dashboard",
        "hero_title_results":   "Your opportunities, prioritized.",
        "hero_sub_results":     "The AI evaluated each listing against your profile. Recommended ones are in the tab below, sorted by score.",
        "hero_note_results":    "Results ready. Generate letters only for the listings you care about.",
        "hero_tag_done":        "Search completed",
        "hero_stat_analyzed":   "analyzed",
        "hero_stat_rec":        "recommended",
        "hero_stat_best":       "best score",
        "hero_stat_threshold":  "threshold",
        # Empty state
        "empty_label":  "How it works",
        "empty_title":  "A 4-step flow, no visual noise.",
        "empty_copy":   "Upload your CV, launch the search, and get listings sorted by relevance, with the reasoning behind every score.",
        "feat1_title":  "Discover",
        "feat1_desc":   "Remotive, Get on Board, Himalayas, LatoJobs, WeWorkRemotely and 10+ more sources in a single search.",
        "feat2_title":  "Prioritize",
        "feat2_desc":   "The AI scores each listing from 0 to 100, comparing the job description with your real profile. No seniority inflation.",
        "feat3_title":  "Write",
        "feat3_desc":   "Request a cover letter for the listing you choose, in the language of the ad and based only on your CV.",
        "feat4_title":  "Act",
        "feat4_desc":   "Download your letters, export results as JSON, or get a summary by email.",
        # Action buttons
        "searching_notice": "Search in progress — you can stop it at any time.",
        "btn_stop":          "Stop",
        "btn_stop_config":   "Stop & Configure",
        "btn_new_search":    "New search",
        "btn_config_search": "Configure search",
        "search_time_hint":  "Duration depends on how many portals and listings you include. You can stop the search at any time.",
        # Results
        "tab_recommended":       "Recommended",
        "tab_all":               "All",
        "metric_analyzed":       "Analyzed",
        "metric_recommended":    "Recommended",
        "metric_best":           "Best score",
        "metric_excellent":      "Excellent 80+",
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
        "btn_back":        "← Back",
        "toast_cv_ok":     "✅ {n} keywords extracted. Review them in the next step.",
        "toast_cv_err":    "Could not analyze the CV. Continue and fill in data manually.",
        # Step 3
        "step3_header":        "**🔍 Search keywords**",
        "step3_kw_ph":         "Your keywords — × to remove",
        "step3_add_ph":        "Add keyword...",
        "step3_add_btn":       "+ Add",
        "step3_params":        "**⚙️ Parameters**",
        "step3_score_label":   "Minimum score for 'Recommended'",
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
        "toast_no_kw":         "Add at least one keyword.",
        "toast_no_src":        "Select at least one source.",
        # Step 4
        "step4_header":    "**👤 Your professional profile**",
        "step4_caption":   "The AI uses this text to evaluate how well each listing fits you.",
        "step4_ph":        "Target role, experience, education, skills, languages...",
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
        "wf_starting":     "Starting...",
        "wf_searching":    "Searching **{platform}**...",
        "wf_stopped":      "⏹️ Search stopped after {n} source(s) — {jobs} listings found so far.",
        "wf_found":        "✅ **{jobs} unique listings** found — {time}",
        "wf_no_jobs":      "No listings found to analyze.",
        "wf_scored":       "✅ **{top} recommended** of {total} analyzed — {time}",
        "wf_email_send":   "Sending summary to {recipient}...",
        "wf_email_ok":     "✅ Summary sent to **{recipient}**.",
        "wf_email_err":    "Could not send email: {error}",
        "wf_src_prog":     "{done}/{total} sources{eta}",
        "wf_ai_prog":      "{done}/{total} analyzed{eta}",
        "wf_eta":          "  ·  ~{time} remaining",
        "wf_err_platform": "⚠️ Error on {platform}: {error}",
    },
}


def _t(key: str, **kw) -> str:
    """Devuelve el texto en el idioma activo, interpolando kwargs si los hay."""
    lang = st.session_state.get("lang", "es")
    d    = TRANSLATIONS.get(lang, TRANSLATIONS["es"])
    txt  = d.get(key, TRANSLATIONS["es"].get(key, key))
    return txt.format(**kw) if kw else txt


# ─── Toolbar: tema e idioma ───────────────────────────────────────────────────
# Todo del lado del servidor: cambiar idioma o tema hace un rerun, no recarga
# la página, así que la sesión (API key, CV analizado, resultados) se conserva.
def _on_lang_change():
    st.session_state.lang = st.session_state._lang_widget
    st.query_params["lang"] = st.session_state.lang


def _on_theme_change():
    st.session_state.dark_mode = (st.session_state._theme_widget == "dark")
    st.query_params["theme"] = st.session_state._theme_widget


st.session_state._lang_widget  = st.session_state.lang
st.session_state._theme_widget = "dark" if st.session_state.dark_mode else "light"

st.markdown("""
<style>
.st-key-jh_toolbar {
  position: fixed; top: 60px; right: 7.5rem; z-index: 100000;
  width: auto !important;
}
</style>
""", unsafe_allow_html=True)

with st.container(key="jh_toolbar", horizontal=True, width="content"):
    st.segmented_control(
        _t("theme_label"), ["light", "dark"], required=True,
        format_func={"light": "☀️", "dark": "🌙"}.get,
        key="_theme_widget", on_change=_on_theme_change, label_visibility="collapsed",
    )
    st.segmented_control(
        _t("lang_label"), ["es", "en"], required=True,
        format_func=str.upper,
        key="_lang_widget", on_change=_on_lang_change, label_visibility="collapsed",
    )

# El CSS del modo oscuro cuelga de html[data-theme]. El iframe se vuelve a
# ejecutar solo cuando cambia su contenido, o sea, cuando cambia el tema.
_theme = "dark" if st.session_state.dark_mode else "light"
components.html(
    f"<script>window.parent.document.documentElement.setAttribute('data-theme','{_theme}');</script>",
    height=0,
)


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
    if (_get_profile() or CandidateProfile()).is_empty():
        errors.append(_t("val_no_profile"))
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


# ─── Perfil del candidato (estructurado) ──────────────────────────────────────
JOB_LANG_CODES = ["es", "en", "pt", "de", "fr"]
_LANG_NAME_HINTS = {
    "es": ("espa", "castellano", "spanish"),
    "en": ("ingl", "english"),
    "pt": ("portug",),
    "de": ("alem", "german", "deutsch"),
    "fr": ("franc", "french"),
}


def _get_profile() -> CandidateProfile | None:
    d = st.session_state.get("profile")
    return CandidateProfile.from_dict(d) if d else None


def _set_profile(p: CandidateProfile) -> None:
    st.session_state.profile = p.to_dict()


def _job_lang_codes(p: CandidateProfile) -> list[str]:
    """Idiomas de oferta aceptables según el CV (sugerencia que el usuario puede cambiar)."""
    names = [normalize.strip_accents(l.language.lower()) for l in p.languages]
    return [code for code, hints in _LANG_NAME_HINTS.items()
            if p.cv_language == code or any(h in n for n in names for h in hints)]


def _analyze_cv(uploaded_file) -> CandidateProfile | None:
    try:
        contents = cand.cv_contents(uploaded_file.getvalue(), uploaded_file.type)
        return cand.extract_profile(contents, api_key=st.session_state.gemini_key,
                                    model=st.session_state.selected_model)
    except Exception as e:
        st.error(_t("cv_error", error=e))
        return None


def _lang_label(l) -> str:
    return f"{l.language} ({l.level})" if l.level and l.level != cand.UNKNOWN else l.language


def _parse_lang_label(label: str) -> cand.Language:
    import re as _re
    m = _re.match(r"^(.*?)\s*\((.*)\)\s*$", label)
    return cand.Language(language=m.group(1).strip(), level=m.group(2).strip()) if m else cand.Language(label.strip())


def _uniq(items) -> list[str]:
    """Sin duplicados (multiselect falla con opciones repetidas), respetando el orden."""
    return list(dict.fromkeys(i for i in items if i))


def _render_profile_editor(p: CandidateProfile) -> CandidateProfile:
    """Perfil extraído del CV, editable. Lo que la IA no encontró queda como 'no especificado'."""
    st.markdown(_t("prof_title"))
    st.caption(_t("prof_caption"))
    p.summary = st.text_area(_t("prof_summary"), value=p.summary, height=90)
    c1, c2 = st.columns(2)
    with c1:
        p.target_roles = st.multiselect(_t("prof_roles"), options=_uniq(p.target_roles), default=_uniq(p.target_roles),
                                        accept_new_options=True, help=_t("prof_roles_help"))
        p.seniority = st.selectbox(_t("prof_seniority"), SENIORITY_LEVELS,
                                   index=SENIORITY_LEVELS.index(p.seniority),
                                   format_func=lambda s: _t(f"sen_{s}"))
        p.years_experience = st.number_input(_t("prof_years"), value=p.years_experience, min_value=0.0,
                                             max_value=60.0, step=0.5, help=_t("prof_years_help"))
    with c2:
        loc = st.text_input(_t("prof_location"), value="" if p.location == cand.UNKNOWN else p.location,
                            placeholder=_t("prof_unknown"))
        p.location = loc.strip() or cand.UNKNOWN
        lang_labels = _uniq(_lang_label(l) for l in p.languages)
        chosen = st.multiselect(_t("prof_languages"), options=lang_labels, default=lang_labels,
                                accept_new_options=True, help=_t("prof_languages_help"))
        p.languages = [_parse_lang_label(x) for x in chosen]
    skill_names = _uniq(s.name for s in p.skills)
    kept = st.multiselect(_t("prof_skills"), options=skill_names, default=skill_names, accept_new_options=True)
    by_name = {s.name: s for s in p.skills}
    p.skills = [by_name.get(n) or cand.Skill(name=n, evidence=_t("prof_added_by_user")) for n in kept]

    with st.expander(_t("prof_evidence")):
        none = _t("prof_unknown")
        st.caption(f"{_t('prof_seniority')}: {p.seniority_evidence or none}")
        st.caption(f"{_t('prof_years')}: {p.years_evidence or none}")
        for s in p.skills:
            st.caption(f"{s.name}: {s.evidence or none}")
    return p


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
            help=_t("wiz_close_help"),
        ):
            st.session_state.show_dialog = False
            st.rerun()

    _render_stepper(step)

    # ── Paso 1: Credenciales ──────────────────────────────────────────────
    if step == 1:
        with st.container(border=True):
            st.markdown(_t("step1_header"))
            with st.expander(_t("step1_gemini_help"), icon="❓"):
                st.markdown(_t("help_gemini_steps"))
            st.session_state.gemini_key = st.text_input(
                _t("step1_key_label"),
                value=st.session_state.gemini_key,
                type="password",
                placeholder="AIzaXXXXXXXXXXXXXXXXX",
            )
            _models = ai_engine.AVAILABLE_MODELS
            if st.session_state.selected_model not in _models:
                st.session_state.selected_model = ai_engine.DEFAULT_MODEL
            _idx = _models.index(st.session_state.selected_model)
            st.session_state.selected_model = st.selectbox(_t("step1_model_label"), _models, index=_idx)

        with st.container(border=True):
            st.checkbox(_t("step1_email_chk"), key="send_email")
            if st.session_state.send_email:
                with st.expander(_t("step1_email_help"), icon="❓"):
                    st.markdown(_t("help_gmail_steps"))
                c1, c2 = st.columns(2)
                with c1:
                    st.session_state.email_sender = st.text_input(
                        _t("step1_gmail_label"),
                        value=st.session_state.email_sender,
                        placeholder=_t("ph_email_sender"),
                    )
                with c2:
                    st.session_state.email_recipient = st.text_input(
                        _t("step1_recip_label"),
                        value=st.session_state.email_recipient,
                        placeholder=_t("ph_email_recip"),
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
                        extracted = _analyze_cv(uploaded_file)
                    if extracted:
                        _set_profile(extracted)
                        kws = extracted.all_search_terms()
                        if kws:
                            st.session_state.keywords_list = kws
                            st.session_state["kw_options"] = list(kws)
                            st.session_state["kw_tags"] = list(kws)
                        st.session_state.pref_languages = _job_lang_codes(extracted)
                        st.session_state.cv_analyzed = True
                        st.toast(_t("toast_cv_ok", n=len(kws)), icon="✅")
                    else:
                        st.toast(_t("toast_cv_err"), icon="⚠️")

        _p = _get_profile()
        if st.session_state.cv_analyzed and _p:
            with st.container(border=True):
                _set_profile(_render_profile_editor(_p))

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
            st.caption(_t("pref_caption"))
            st.session_state.pref_modalities = st.multiselect(
                _t("pref_modality"), list(matching.MODALITIES),
                default=st.session_state.pref_modalities,
                format_func=lambda m: _t(f"mod_{m}"),
                placeholder=_t("pref_any"), help=_t("pref_modality_help"),
            )
            st.session_state.pref_locations = st.text_input(
                _t("pref_locations"), value=st.session_state.pref_locations,
                placeholder=_t("pref_locations_ph"), help=_t("pref_locations_help"),
            )
            st.session_state.pref_languages = st.multiselect(
                _t("pref_languages"), JOB_LANG_CODES,
                default=[c for c in st.session_state.pref_languages if c in JOB_LANG_CODES],
                format_func=lambda c: _t(f"lang_{c}"),
                placeholder=_t("pref_any"), help=_t("pref_languages_help"),
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

            st.caption(_t("step3_latam"))
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

            st.session_state.eval_limit = st.slider(
                _t("eval_limit_label"), min_value=10, max_value=200, step=10,
                value=st.session_state.eval_limit, help=_t("eval_limit_help"),
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
            _p = _get_profile() or CandidateProfile()
            _structured = bool(_p.summary or _p.target_roles or _p.skills or _p.experiences)
            if _structured:
                st.caption(_t("step4_caption_structured"))
                with st.expander(_t("prof_preview")):
                    st.text(_p.to_prompt())
                _p.notes = st.text_area(_t("prof_notes"), value=_p.notes, height=110)
            else:
                st.caption(_t("step4_caption"))
                _p.notes = st.text_area(
                    "perfil", value=_p.notes, height=195,
                    label_visibility="collapsed", placeholder=_t("step4_ph"),
                )
            _set_profile(_p)

        if _p.is_empty():
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
# Portales realmente disponibles en este entorno (sin Playwright no hay portales con login).
N_PORTALS = sum(
    1 for k in _defaults
    if k.startswith("use_") and (not IS_CLOUD or not k.endswith("_browser"))
)

def _render_hero():
    if st.session_state.search_done and st.session_state.scored_jobs:
        _s   = st.session_state.scored_jobs
        _top = st.session_state.top_matches
        _ev  = [j for j in _s if j.evaluated]
        best = _ev[0].score if _ev else "—"
        stat_html = (
            f'<div class="jh-stat-grid">'
            f'<div class="jh-stat"><strong>{len(_ev)}</strong><span>{_t("hero_stat_analyzed")}</span></div>'
            f'<div class="jh-stat"><strong>{len(_top)}</strong><span>{_t("hero_stat_rec")}</span></div>'
            f'<div class="jh-stat"><strong>{best}/100</strong><span>{_t("hero_stat_best")}</span></div>'
            f'<div class="jh-stat"><strong>{st.session_state.min_score_last}</strong><span>{_t("hero_stat_threshold")}</span></div>'
            f'</div>'
        )
        note_key    = "hero_note_results"
        eyebrow_key = "hero_eyebrow_results"
        title_key   = "hero_title_results"
        sub_key     = "hero_sub_results"
        tag_key     = "hero_tag_done"
        note    = _t(note_key);    eyebrow = _t(eyebrow_key)
        title   = _t(title_key);  sub     = _t(sub_key)
        tags    = f'<span class="jh-tag jh-tag-blue">{_t(tag_key)}</span>'
    else:
        stat_html = (
            f'<div class="jh-stat-grid">'
            f'<div class="jh-stat"><strong>{N_PORTALS}</strong><span>{_t("hero_stat_sources")}</span></div>'
            f'<div class="jh-stat"><strong>0–100</strong><span>{_t("hero_stat_score")}</span></div>'
            f'<div class="jh-stat"><strong>CV</strong><span>{_t("hero_stat_ai")}</span></div>'
            f'<div class="jh-stat"><strong>ES · EN</strong><span>{_t("hero_stat_time")}</span></div>'
            f'</div>'
        )
        note_key    = "hero_note_search"
        eyebrow_key = "hero_eyebrow_search"
        title_key   = "hero_title_search"
        sub_key     = "hero_sub_search"
        note    = _t(note_key);    eyebrow = _t(eyebrow_key)
        title   = _t(title_key);  sub     = _t(sub_key, n=N_PORTALS)
        tags    = (
            f'<span class="jh-tag jh-tag-blue"  >{_t("hero_tag_scoring")}</span>'
            f'<span class="jh-tag jh-tag-violet">{_t("hero_tag_multi")}</span>'
            f'<span class="jh-tag jh-tag-green" >{_t("hero_tag_letters")}</span>'
            f'<span class="jh-tag jh-tag-gray"  >{_t("hero_tag_local")}</span>'
        )

    st.markdown(f"""
<div class="jh-hero">
  <div class="jh-hero-copy">
    <span class="jh-eyebrow">{eyebrow}</span>
    <h1 class="jh-hero-title">{title}</h1>
    <p class="jh-hero-sub">{sub}</p>
    <div class="jh-tags">{tags}</div>
  </div>
  <aside class="jh-panel">
    {stat_html}
    <p class="jh-panel-note">{note}</p>
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
  <span class="jh-label">{_t("empty_label")}</span>
  <h2 class="jh-title">{_t("empty_title")}</h2>
  <p class="jh-copy">{_t("empty_copy")}</p>
</div>
<div class="jh-features">
  <div class="jh-feature">
    <span class="jh-f-icon">01</span>
    <div class="jh-f-title">{_t("feat1_title")}</div>
    <p class="jh-f-desc">{_t("feat1_desc")}</p>
  </div>
  <div class="jh-feature">
    <span class="jh-f-icon">02</span>
    <div class="jh-f-title">{_t("feat2_title")}</div>
    <p class="jh-f-desc">{_t("feat2_desc")}</p>
  </div>
  <div class="jh-feature">
    <span class="jh-f-icon">03</span>
    <div class="jh-f-title">{_t("feat3_title")}</div>
    <p class="jh-f-desc">{_t("feat3_desc")}</p>
  </div>
  <div class="jh-feature">
    <span class="jh-f-icon">04</span>
    <div class="jh-f-title">{_t("feat4_title")}</div>
    <p class="jh-f-desc">{_t("feat4_desc")}</p>
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
            f'>{_t("searching_notice")}</p>',
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
                f'>{_t("search_time_hint")}</p>',
                unsafe_allow_html=True,
            )

if not st.session_state.run_search and not st.session_state.search_done:
    render_empty_state()

# ─── Ejecución de la búsqueda ─────────────────────────────────────────────────
SCRAPE_PER_PORTAL = 40
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
    eval_limit        = st.session_state.eval_limit
    profile           = _get_profile() or CandidateProfile()
    prefs = matching.SearchPreferences(
        modalities=set(st.session_state.pref_modalities),
        locations=[l.strip() for l in st.session_state.pref_locations.split(",") if l.strip()],
        job_languages=list(st.session_state.pref_languages),
    )
    browser_profile_dir = st.session_state.browser_profile_dir

    st.session_state.result_page     = 0
    st.session_state.result_page_all = 0

    # API key, perfil, preferencias y credenciales viajan por parámetro: el proceso es
    # compartido entre usuarios y nada de esto puede quedar en variables de módulo.
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
    # Tope por portal: acota la duración del scraping. El filtrado fino lo hace matching.py.
    per_portal      = SCRAPE_PER_PORTAL

    for idx, platform_name in enumerate(enabled_list):
        platform_status.info(_t("wf_searching", platform=platform_name))
        try:
            remaining = per_portal
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

    # ── STEP 2: Matching (filtros → pre-ranking → evaluación por factores) ────
    ai_status, ai_notice, progress_ai, _ = render_workflow_step(2, _t("wf_step2_title"))

    scored_jobs    = []
    top_matches    = []
    st.session_state.run_notice  = None
    st.session_state.scored_jobs = []
    st.session_state.top_matches = []
    st.session_state.funnel      = None

    if not all_jobs:
        st.session_state.run_notice = ("wf_no_jobs", {})
        ai_status.warning(_t("wf_no_jobs"))
        progress_ai.progress(1.0)
    else:
        scoring_started = time.monotonic()
        ai_status.info(_t("wf_preparing", n=eval_limit))
        progress_ai.progress(0, text=_t("wf_starting"))

        def _on_progress(stage, done, total):
            elapsed = time.monotonic() - scoring_started
            remaining = (elapsed / done) * (total - done) if done else 0
            eta = _t("wf_eta", time=format_duration(remaining)) if done < total else ""
            ai_status.info(_t("wf_rechecking" if stage == "recheck" else "wf_evaluating", done=done, total=total))
            progress_ai.progress(done / total, text=_t("wf_ai_prog", done=done, total=total, eta=eta))

        result = matching.match_jobs(
            all_jobs, profile, prefs,
            api_key=gemini_key, model=selected_model, lang=st.session_state.lang,
            top_n=eval_limit, on_progress=_on_progress,
        )
        scored_jobs = result.scored
        top_matches = ai_engine.recommended(scored_jobs, min_score)
        st.session_state.scored_jobs    = scored_jobs
        st.session_state.top_matches    = top_matches
        st.session_state.min_score_last = min_score
        st.session_state.funnel = {
            "found": result.total_found,
            "dups": result.duplicates_removed,
            "excluded": result.excluded,
            "out": result.pre_ranked_out,
            "evaluated": sum(1 for j in scored_jobs if j.evaluated),
            "top_n": eval_limit,
            "emb_failed": result.embeddings_failed,
        }
        if result.stop_reason == "auth":
            st.session_state.run_notice = ("wf_auth_error", {})
        elif result.stop_reason == "quota":
            st.session_state.run_notice = ("wf_quota_stop", {})
        elif not scored_jobs:
            st.session_state.run_notice = ("wf_all_filtered", {})

        if st.session_state.run_notice:
            ai_notice.error(_t(st.session_state.run_notice[0], **st.session_state.run_notice[1]))
        else:
            ai_status.success(_t("wf_scored", top=len(top_matches), total=len(scored_jobs),
                                 time=format_duration(time.monotonic() - scoring_started)))
        progress_ai.progress(1.0)

    # ── STEP 3: Email ─────────────────────────────────────────────────────────
    if send_email and top_matches and email_sender and email_password:
        email_status, _, _, _ = render_workflow_step(3, _t("wf_email_title"))
        try:
            from notifier import send_digest
            email_status.info(_t("wf_email_send", recipient=email_recipient))
            send_digest(
                scored_jobs,
                sender=email_sender, password=email_password,
                recipient=email_recipient, min_score=min_score,
            )
            email_status.success(_t("wf_email_ok", recipient=email_recipient))
        except Exception as e:
            email_status.error(_t("wf_email_err", error=e))

    workflow_placeholder.empty()

    st.session_state.search_done  = True
    st.session_state.is_searching = False
    st.session_state.cancel_search = False
    st.rerun()

# ── Renderizado de resultados ────────────────────────────────────────────────
if st.session_state.search_done and not st.session_state.scored_jobs and st.session_state.get("run_notice"):
    with results_placeholder.container():
        st.warning(_t(st.session_state.run_notice[0], **st.session_state.run_notice[1]))

if st.session_state.search_done and st.session_state.scored_jobs:
    _scored   = st.session_state.scored_jobs
    _top      = st.session_state.top_matches
    _minscore = st.session_state.min_score_last

    with results_placeholder.container():
        import html as _html
        import ai_engine

        _evaluated = [j for j in _scored if j.evaluated]
        _n_uneval  = len(_scored) - len(_evaluated)
        if st.session_state.get("run_notice"):
            st.warning(_t(st.session_state.run_notice[0], **st.session_state.run_notice[1]))
        exc = sum(1 for j in _evaluated if j.score >= 80)
        st.markdown(f"""
<div class="jh-metrics">
  <div class="jh-metric">
    <div class="jh-metric-val">{len(_evaluated)}</div>
    <div class="jh-metric-lbl">{_t("metric_analyzed")}</div>
  </div>
  <div class="jh-metric">
    <div class="jh-metric-val">{len(_top)}</div>
    <div class="jh-metric-lbl">{_t("metric_recommended")}</div>
  </div>
  <div class="jh-metric">
    <div class="jh-metric-val">{_evaluated[0].score if _evaluated else "—"}<span style="font-size:1rem;font-weight:500;color:var(--t3)">/100</span></div>
    <div class="jh-metric-lbl">{_t("metric_best")}</div>
  </div>
  <div class="jh-metric">
    <div class="jh-metric-val">{exc}</div>
    <div class="jh-metric-lbl">{_t("metric_excellent")}</div>
  </div>
</div>
""", unsafe_allow_html=True)

        _f = st.session_state.get("funnel")
        if _f:
            _ex = _f["excluded"]
            st.caption(_t("funnel", found=_f["found"], dups=_f["dups"], filtered=sum(_ex.values()),
                          mod=_ex.get("modality", 0), lang=_ex.get("language", 0), loc=_ex.get("location", 0),
                          out=_f["out"], n=_f["top_n"], evaluated=_f["evaluated"]))
            if _f.get("emb_failed"):
                st.caption(_t("wf_emb_failed", n=_f["top_n"]))

        def _score_cls(s):
            return "jh-score-hi" if s >= 80 else "jh-score-md" if s >= 60 else "jh-score-lo"

        def _src_cls(source):
            return "src-" + source.replace(" ", "-").replace(".", "-")

        def _generate_letter(sj):
            with st.spinner(_t("letter_generating")):
                try:
                    sj.cover_letter = ai_engine.generate_cover_letter(
                        sj.job, sj.match_reasons, (_get_profile() or CandidateProfile()).to_prompt(),
                        api_key=st.session_state.gemini_key, model=st.session_state.selected_model,
                    )
                except Exception as e:
                    st.error(_t("letter_error", error=e))

        def render_job_card(sj, idx, section):
            score = sj.score
            src   = _src_cls(sj.job.source)

            if sj.evaluated:
                score_badge = f'<span class="jh-score {_score_cls(score)}">{score}/100</span>'
                label = f"{score}/100 — {sj.job.title} @ {sj.job.company}"
            else:
                score_badge = f'<span class="jh-score jh-score-lo">{_t("not_evaluated")}</span>'
                label = f"{_t('not_evaluated')} — {sj.job.title} @ {sj.job.company}"
            badges = (
                f'{score_badge} '
                f'<span class="jh-src {src}">{_html.escape(sj.job.source)}</span>'
            )
            _tag = '<span class="jh-tag {cls}" style="height:20px;font-size:11px;">{txt}</span>'
            if sj.job.modality in matching.MODALITIES:
                badges += " " + _tag.format(cls="jh-tag-green", txt=_t(f"mod_{sj.job.modality}"))
            if sj.job.location and sj.job.modality != "remote":
                badges += " " + _tag.format(cls="jh-tag-gray", txt=_html.escape(sj.job.location[:30]))
            if sj.job.seniority in SENIORITY_LEVELS and sj.job.seniority != cand.UNKNOWN:
                badges += " " + _tag.format(cls="jh-tag-gray", txt=_t(f"sen_{sj.job.seniority}"))

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

                if not sj.evaluated:
                    return

                r1, r2 = st.columns(2)
                with r1:
                    st.markdown(f'<div class="jh-col-lbl">{_t("why_fits")}</div>', unsafe_allow_html=True)
                    if sj.match_reasons:
                        for reason in sj.match_reasons:
                            st.markdown(f'<div class="jh-reason">{_html.escape(reason)}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<span style="font-size:13px;color:var(--t3)">{_t("no_reasons")}</span>', unsafe_allow_html=True)
                with r2:
                    st.markdown(f'<div class="jh-col-lbl">{_t("what_missing")}</div>', unsafe_allow_html=True)
                    if sj.missing_skills:
                        for skill in sj.missing_skills:
                            st.markdown(f'<div class="jh-reason jh-skill">{_html.escape(skill)}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<span style="font-size:13px;color:var(--t3)">{_t("no_missing")}</span>', unsafe_allow_html=True)

                if sj.factors:
                    with st.expander(_t("factors_title")):
                        for fname in matching.FACTORS:
                            fs = sj.factors[fname]
                            weight = int(matching.WEIGHTS[fname] * 100)
                            st.markdown(f"**{_t('f_' + fname)}** · {fs.score}/100 · {_t('f_weight', w=weight)}")
                            st.progress(fs.score / 100)
                            if fs.evidence_job:
                                st.caption(f"{_t('f_job')} {fs.evidence_job}")
                            if fs.evidence_cv:
                                st.caption(f"{_t('f_cv')} {fs.evidence_cv}")
                        st.caption(_t("factors_note"))

                if sj.evaluated and not sj.cover_letter:
                    if st.button(_t("btn_gen_letter"), key=f"gen_{section}_{sj.job.id}_{idx}"):
                        _generate_letter(sj)

                if sj.cover_letter:
                    st.markdown('<div style="height:.5rem;"></div>', unsafe_allow_html=True)
                    with st.expander(_t("cover_letter_expander"), expanded=True):
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
                st.info(_t("no_recommended", score=_minscore) if _evaluated else _t("none_evaluated"))
        with all_tab:
            st.caption(_t("all_tab_caption"))
            if _n_uneval:
                st.caption(_t("uneval_note", n=_n_uneval))
            render_paginated(_scored, "all")

        # Exportación desde la sesión del usuario (nunca desde disco compartido).
        _export = [
            {
                "score":          sj.score if sj.evaluated else None,
                "evaluated":      sj.evaluated,
                "title":          sj.job.title,
                "company":        sj.job.company,
                "source":         sj.job.source,
                "url":            sj.job.url,
                "location":       sj.job.location,
                "remote":         sj.job.remote,
                "match_reasons":  sj.match_reasons,
                "missing_skills": sj.missing_skills,
                "summary":        sj.summary,
                "factors":        {k: vars(v) for k, v in sj.factors.items()} if sj.factors else None,
                "detected":       {"language": sj.job.language, "seniority": sj.job.seniority,
                                   "modality": sj.job.modality},
                "cover_letter":   sj.cover_letter,
            }
            for sj in _scored
        ]
        st.download_button(
            _t("btn_download_json"),
            data=json.dumps(_export, ensure_ascii=False, indent=2),
            file_name=f"job_hunter_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
        )
