import os
import html
import base64
from pathlib import Path
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components
from langchain_core.messages import HumanMessage
from main import app

st.set_page_config(
    page_title="VoyageAI",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Session state ─────────────────────────────────────────────────────────────
if "trip_query" not in st.session_state:
    st.session_state.trip_query = ""
if "plan_result" not in st.session_state:
    st.session_state.plan_result = None
if "thinking_steps" not in st.session_state:
    st.session_state.thinking_steps = set()

_assets = Path(__file__).parent / "assets"
_hero_b64 = base64.b64encode((_assets / "hero-bg.jpg").read_bytes()).decode()
HERO_SRC = f"data:image/jpeg;base64,{_hero_b64}"
_thailand_b64 = base64.b64encode((_assets / "thailand-maya-bay.jpg").read_bytes()).decode()
THAILAND_SRC = f"data:image/jpeg;base64,{_thailand_b64}"

DESTINATION_PROMPTS = {
    "Italy": "Plan a trip to Italy focusing on Rome, Florence, and Venice.",
    "Paris": "Plan a romantic trip to Paris, the City of Love.",
    "Switzerland": "Plan a scenic trip to Switzerland including Alps, lakes, and mountain towns.",
    "Bali": "Plan a relaxing Bali trip with beaches, temples, and local culture.",
    "Dubai": "Plan a luxury trip to Dubai with modern attractions and desert experiences.",
    "India": "Plan a cultural trip to India focusing on ancient temples, heritage sites, and local traditions.",
    "Thailand": "Plan a trip to Thailand with island lagoons, beaches, and coastal adventures.",
}

DESTINATIONS = [
    (
        "Italy",
        "Rome • Florence • Venice",
        "https://images.unsplash.com/photo-1523906834658-6e24ef2386f9?w=600&q=80",
    ),
    (
        "Paris",
        "City of Love",
        "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=600&q=80",
    ),
    (
        "Switzerland",
        "Alps • Lakes • Peaks",
        "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=600&q=80",
    ),
    (
        "Bali",
        "Beaches • Temples",
        "https://images.unsplash.com/photo-1537953773345-d172ccf13cf1?w=600&q=80",
    ),
    (
        "Dubai",
        "Luxury • Desert",
        "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=600&q=80",
    ),
    (
        "India",
        "Temples • Heritage",
        "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?w=600&q=80",
    ),
    (
        "Thailand",
        "Islands • Lagoons",
        THAILAND_SRC,
    ),
]

AGENT_META = {
    "flight_agent": "Flight Agent",
    "hotel_agent": "Hotel Agent",
    "itinerary_agent": "Itinerary Agent",
    "final_agent": "Final Agent",
}

THINKING_STEPS = [
    ("flight_agent", "Searching best flights"),
    ("hotel_agent", "Finding top hotels"),
    ("itinerary_agent", "Building day-wise itinerary"),
    ("final_agent", "Optimizing budget"),
]

def thinking_panel_html(completed: set[str], active: bool = False) -> str:
    items = []
    for key, label in THINKING_STEPS:
        done = key in completed
        cls = "done" if done else ("active" if active and not done else "")
        mark = "✓" if done else "○"
        items.append(
            f'<li class="think-item {cls}"><span class="think-mark">{mark}</span>{label}</li>'
        )
    status_title = "AI is thinking..." if active else (
        "Ready when you are" if not completed else "Plan ready"
    )
    pulse = "pulse" if active else ""
    return f"""
    <div class="think-panel">
      <div class="think-header">
        <span class="think-status"><span class="think-dot {pulse}"></span></span>
        <span>{status_title}</span>
      </div>
      <ul class="think-list">{"".join(items)}</ul>
      <div class="mini-flight">
        <svg viewBox="0 0 280 90" xmlns="http://www.w3.org/2000/svg" class="mini-svg">
          <defs>
            <linearGradient id="skyGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#EBD6D7"/>
              <stop offset="100%" stop-color="#F9EBD9"/>
            </linearGradient>
          </defs>
          <rect width="280" height="90" rx="12" fill="url(#skyGrad)"/>
          <path d="M0 70 Q70 55 140 65 T280 50 L280 90 L0 90 Z" fill="#439093" opacity="0.35"/>
          <path d="M40 70 L55 45 L70 70 Z" fill="#439093" opacity="0.55"/>
          <path d="M180 75 L200 40 L220 75 Z" fill="#439093" opacity="0.55"/>
          <circle cx="230" cy="28" r="8" fill="#F09B93" opacity="0.85"/>
          <path class="dotted-path" d="M20 55 Q90 20 160 40 T260 25"
                fill="none" stroke="rgba(67,144,147,0.55)" stroke-width="1.5"
                stroke-dasharray="3 5"/>
          <g class="plane-mini">
            <path d="M0 4 L14 -2 L4 6 L2 12 Z" fill="#439093"/>
          </g>
        </svg>
      </div>
    </div>
    """


st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

:root {
  --coral: #F09B93;
  --rose: #EBD6D7;
  --cream: #F9EBD9;
  --butter: #E9DD8A;
  --teal: #439093;
  --ink: #1A3A3C;
  --bg: #F9EBD9;
  --panel: #FFFFFF;
  --glass: rgba(255, 255, 255, 0.78);
  --border: rgba(67, 144, 147, 0.22);
  --text: #1A3A3C;
  --muted: #6B7F80;
  --accent: #439093;
  --accent-2: #F09B93;
  --grad: linear-gradient(135deg, #F09B93 0%, #E9DD8A 48%, #439093 100%);
}

html, body, .stApp {
  font-family: 'Plus Jakarta Sans', sans-serif;
  background: var(--bg) !important;
  color: var(--text);
}
.stApp {
  background: radial-gradient(ellipse at 20% 0%, #EBD6D7 0%, #F9EBD9 48%, #F4E6D0 100%) !important;
}
.block-container {
  padding-top: 0 !important;
  padding-bottom: 0 !important;
  padding-left: 0 !important;
  padding-right: 0 !important;
  margin-bottom: 0 !important;
  max-width: 100% !important;
}
.stMain, [data-testid="stAppViewContainer"],
[data-testid="stMain"],
section.main {
  margin-bottom: 0 !important;
  padding-bottom: 0 !important;
}
.stMainBlockContainer,
[data-testid="stMainBlockContainer"] {
  padding-bottom: 0 !important;
  margin-bottom: 0 !important;
}
/* No flex gaps between hero and the rest of the page */
.stMainBlockContainer > [data-testid="stVerticalBlock"],
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {
  gap: 0 !important;
  row-gap: 0 !important;
}
/* Drop empty style-block flex item so the 1rem vertical gap isn't above the hero */
.stMainBlockContainer > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:first-child {
  display: none !important;
}
/* Keep scroll-binder iframe out of layout (height=0 still reserved space) */
[data-testid="stElementContainer"]:has(iframe[height="0"]),
[data-testid="stElementContainer"]:has(iframe[height="0"]) iframe {
  height: 0 !important;
  min-height: 0 !important;
  max-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  border: none !important;
  overflow: hidden !important;
  position: absolute !important;
  opacity: 0 !important;
  pointer-events: none !important;
}
#MainMenu,
footer,
[data-testid="stBottomBlockContainer"],
[data-testid="stBottom"] {
  display: none !important;
  visibility: hidden !important;
  height: 0 !important;
  min-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
}

/* Remove Streamlit chrome entirely (Deploy, toolbar, status) */
header[data-testid="stHeader"],
.stAppDeployButton,
.stDeployButton,
[data-testid="stAppDeployButton"],
[data-testid="stToolbar"],
[data-testid="stToolbarActions"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
div[data-testid="stToolbar"] {
  display: none !important;
  visibility: hidden !important;
  height: 0 !important;
  min-height: 0 !important;
  pointer-events: none !important;
}

/* Hide sidebar entirely */
section[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapseButton"] {
  display: none !important;
  visibility: hidden !important;
  width: 0 !important;
  min-width: 0 !important;
}

/* Hero — full viewport (dvh covers mobile/browser chrome better than vh) */
.hero-wrapper {
  position: relative;
  width: 100%;
  min-height: 100vh;
  min-height: 100dvh;
  height: 100vh;
  height: 100dvh;
  overflow: hidden;
  margin: 0 !important;
  padding: 0 !important;
  border: none;
  border-radius: 0;
  display: flex;
  align-items: center;
}
[data-testid="stElementContainer"]:has(.hero-wrapper),
[data-testid="stElementContainer"]:has(.hero-wrapper) [data-testid="stMarkdownContainer"],
[data-testid="stElementContainer"]:has(.hero-wrapper) .stMarkdown {
  margin: 0 !important;
  padding: 0 !important;
  max-width: 100% !important;
}
.hero-bg {
  position: absolute !important; inset: 0 !important;
  width: 100% !important; height: 100% !important;
  max-width: none !important; max-height: none !important;
  object-fit: cover !important;
  object-position: center 40% !important;
  display: block !important;
  filter: brightness(1) saturate(1.04) contrast(1.06);
}
.hero-overlay {
  position: absolute; inset: 0;
  background: linear-gradient(105deg,
    rgba(249,235,217,0.18) 0%,
    rgba(235,214,215,0.05) 48%,
    rgba(67,144,147,0.08) 100%);
}
.hero-content {
  position: relative; z-index: 2;
  padding: clamp(1.75rem, 4vw, 2.85rem) clamp(1.75rem, 4.5vw, 3.25rem);
  max-width: min(720px, calc(100% - 2.5rem));
  margin: clamp(1.25rem, 5vw, 4rem);
  height: auto;
  display: flex; flex-direction: column; justify-content: center;
  border-radius: 28px;
  background: rgba(255, 250, 245, 0.42);
  backdrop-filter: blur(6px) saturate(1.15);
  -webkit-backdrop-filter: blur(12px) saturate(1.15);
  border: 1px solid rgba(255, 255, 255, 0.55);
  box-shadow:
    0 12px 40px rgba(26, 58, 60, 0.14),
    inset 0 1px 0 rgba(255, 255, 255, 0.55);
}
.hero-brand {
  font-size: clamp(2.8rem, 7vw, 4.6rem);
  font-weight: 800;
  letter-spacing: -0.03em;
  line-height: 1;
  color: #1A3A3C;
  margin: 0 0 1rem;
}
.hero-brand .brand-ai {
  background: var(--grad);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
}
.hero-title {
  font-size: clamp(1.55rem, 3.2vw, 2.35rem); font-weight: 700; color: #1A3A3C;
  margin: 0 0 0.85rem; line-height: 1.2;
}
.hero-title .grad {
  background: var(--grad);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
}
.hero-sub {
  color: #3D5557; font-size: 1.05rem; max-width: 540px;
  line-height: 1.55; margin-bottom: 1.75rem;
}
.hero-cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  padding: 0.95rem 1.75rem;
  border-radius: 14px;
  border: none;
  cursor: pointer;
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 1.05rem;
  font-weight: 700;
  color: #fff !important;
  text-decoration: none !important;
  background: linear-gradient(135deg, #439093 0%, #3a7d80 55%, #F09B93 100%);
  box-shadow: 0 0 28px rgba(67,144,147,0.22), 0 4px 16px rgba(67,144,147,0.15);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.hero-cta:hover {
  transform: translateY(-1px);
  box-shadow: 0 0 40px rgba(67,144,147,0.35);
  color: #fff !important;
}

/* Shared side rails — carousel + chat/Ready share the same left/right edges */
div[class*="st-key-below_fold"] {
  padding: 2rem 0 0 !important;
  margin-left: 16px !important;
  margin-right: 16px !important;
  margin-bottom: 0 !important;
  width: calc(100% - 32px) !important;
  max-width: calc(100% - 32px) !important;
  box-sizing: border-box !important;
}

@keyframes fly-path {
  0%   { offset-distance: 0%; }
  100% { offset-distance: 100%; }
}

/* Section heads */
.sec-head {
  display: flex; align-items: center; justify-content: space-between;
  margin: 0.5rem 0 0.9rem;
}
.sec-head span {
  font-size: 1.2rem; font-weight: 700; color: #1A3A3C;
}

/* Destination carousel styles are inside the component iframe */

#plan-chat {
  scroll-margin-top: 1.25rem;
}

/* Default secondary buttons */
div[data-testid="stButton"] > button {
  background: #FFFFFF !important;
  border: 1px solid rgba(67, 144, 147, 0.35) !important;
  color: #1A3A3C !important;
  border-radius: 10px !important;
  padding: 0.45rem 0.6rem !important;
  font-size: 0.82rem !important;
  font-weight: 600 !important;
  box-shadow: none !important;
  width: 100% !important;
}
div[data-testid="stButton"] > button:hover {
  border-color: rgba(67, 144, 147, 0.7) !important;
  color: #1A3A3C !important;
  background: #EBD6D7 !important;
}

/* Hidden bridge buttons for destination carousel clicks */
div[class*="st-key-dest_"] {
  position: absolute !important;
  width: 1px !important;
  height: 1px !important;
  overflow: hidden !important;
  opacity: 0 !important;
  pointer-events: none !important;
  margin: 0 !important;
  padding: 0 !important;
}

/* Primary generate button */
div[data-testid="stButton"] > button[kind="primary"],
button[data-testid="baseButton-primary"] {
  background: linear-gradient(135deg, #439093 0%, #3a7d80 55%, #F09B93 100%) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 14px !important;
  padding: 0.9rem 1.5rem !important;
  font-size: 1.05rem !important;
  font-weight: 700 !important;
  box-shadow: 0 0 28px rgba(67,144,147,0.22), 0 4px 16px rgba(67,144,147,0.15) !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover,
button[data-testid="baseButton-primary"]:hover {
  box-shadow: 0 0 40px rgba(67,144,147,0.35) !important;
  transform: translateY(-1px) !important;
  background: linear-gradient(135deg, #4ea0a3 0%, #439093 55%, #f3aea7 100%) !important;
}

/* Glass input panel */
.glass-panel {
  background: var(--glass);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 1.25rem 1.35rem;
  margin-bottom: 0.5rem;
}
.input-label {
  color: #439093; font-size: 0.85rem; font-weight: 700;
  letter-spacing: 0.04em; margin-bottom: 0.35rem;
}

.stTextArea textarea {
  background: #FFFFFF !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  color: #1A3A3C !important;
  font-size: 0.95rem !important;
  resize: none !important;
  min-height: 120px !important;
  padding: 1rem 1.2rem !important;
}
.stTextArea textarea:focus {
  border-color: rgba(67,144,147,0.7) !important;
  box-shadow: 0 0 0 2px rgba(67,144,147,0.18) !important;
}
.stTextArea textarea::placeholder { color: #8A9A9B !important; }

input[type="text"], .stTextInput input {
  background: #FFFFFF !important;
  border: 1px solid rgba(67, 144, 147, 0.28) !important;
  border-radius: 10px !important;
  color: #1A3A3C !important;
}
input[type="text"]:focus, .stTextInput input:focus {
  border-color: rgba(67,144,147,0.7) !important;
  box-shadow: 0 0 0 2px rgba(67,144,147,0.18) !important;
}
.stTextInput label, .stTextArea label {
  color: #439093 !important;
  font-size: 0.82rem !important;
  font-weight: 600 !important;
}

/* Thinking panel */
.think-panel {
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 1.1rem 1.15rem;
  height: 100%;
}
.think-header {
  display: flex; align-items: center; gap: 0.55rem;
  font-weight: 700; color: #1A3A3C; margin-bottom: 0.85rem;
}
.think-header .think-status {
  width: 18px; height: 18px;
  display: inline-flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.think-dot {
  width: 10px; height: 10px; border-radius: 50%;
  background: var(--teal); display: inline-block;
}
.think-dot.pulse {
  animation: pulse-dot 1.4s ease-in-out infinite;
  background: var(--coral);
  box-shadow: 0 0 0 0 rgba(240,155,147,0.55);
}
@keyframes pulse-dot {
  0% { box-shadow: 0 0 0 0 rgba(240,155,147,0.55); }
  70% { box-shadow: 0 0 0 8px rgba(240,155,147,0); }
  100% { box-shadow: 0 0 0 0 rgba(240,155,147,0); }
}
.think-list { list-style: none; padding: 0; margin: 0 0 0.9rem; }
.think-item {
  display: flex; align-items: center; gap: 0.55rem;
  color: #6B7F80; font-size: 0.88rem; padding: 0.35rem 0;
}
.think-item.done { color: #1A3A3C; }
.think-item.done .think-mark {
  background: linear-gradient(135deg, #F09B93, #439093);
  color: #fff; border-radius: 50%;
  width: 18px; height: 18px; font-size: 0.65rem;
  display: inline-flex; align-items: center; justify-content: center;
}
.think-mark {
  width: 18px; height: 18px; display: inline-flex;
  align-items: center; justify-content: center;
  font-size: 0.75rem; color: #8A9A9B;
}
.mini-flight { margin-top: 0.25rem; }
.mini-svg { width: 100%; height: auto; border-radius: 12px; }
.plane-mini {
  offset-path: path('M20 55 Q90 20 160 40 T260 25');
  offset-rotate: auto;
  animation: fly-path 5.5s linear infinite;
}

/* Trip result cards */
.final-card {
  background: linear-gradient(160deg, #FFFFFF 0%, #EBD6D7 100%);
  border: 1px solid var(--border);
  border-left: 4px solid var(--teal);
  border-radius: 14px;
  padding: 1.6rem;
  line-height: 1.75;
  color: #1A3A3C;
  font-size: 0.95rem;
  white-space: pre-wrap;
  margin-bottom: 1.5rem;
}
.metric-row { display: flex; margin: 1rem 0; }
.metric-box {
  flex: 1; background: rgba(255, 255, 255, 0.9);
  border: 1px solid var(--border); border-radius: 12px;
  padding: 0.9rem 1rem; text-align: center;
}
.metric-val { font-size: 1.6rem; font-weight: 700; color: var(--coral); line-height: 1.2; }
.metric-box:last-child .metric-val { font-size: 1.15rem; color: var(--teal); }
.metric-lbl { font-size: 0.75rem; color: #6B7F80; margin-top: 0.15rem; text-transform: uppercase; letter-spacing: 0.06em; }
.save-bar {
  background: rgba(255, 255, 255, 0.9); border: 1px solid var(--border);
  border-radius: 10px; padding: 0.85rem 1.2rem;
  color: #3D5557; font-size: 0.88rem;
}
.save-bar code { color: var(--teal); background: #F9EBD9; padding: 0.1em 0.35em; border-radius: 4px; }

.stMarkdown p, .stMarkdown li, .stMarkdown td, .stMarkdown th { color: #1A3A3C !important; }
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #1A3A3C !important; }
.stAlert { background: #FFFFFF !important; border-radius: 10px !important; }
.stAlert p, .stAlert div { color: #1A3A3C !important; }

/* Agent status cards */
[data-testid="stStatusWidget"] {
  background: #FFFFFF !important;
  background-color: #FFFFFF !important;
  border: 1px solid rgba(67, 144, 147, 0.28) !important;
  border-radius: 12px !important;
  transition: background 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="stStatusWidget"] > div:first-child,
[data-testid="stStatusWidget"] details,
[data-testid="stStatusWidget"] [data-testid="stExpanderDetails"],
[data-testid="stStatusWidget"] [data-testid="stVerticalBlock"] {
  background: #F9EBD9 !important;
  background-color: #F9EBD9 !important;
}
[data-testid="stStatusWidget"] summary,
[data-testid="stStatusWidget"] summary[class*="st-emotion"],
details summary[class*="st-emotion"],
summary[class*="st-emotion-cache"] {
  background: #EBD6D7 !important;
  background-color: #EBD6D7 !important;
  color: #1A3A3C !important;
  border-radius: 0.5rem 0.5rem 0 0 !important;
}
[data-testid="stStatusWidget"] summary *,
[data-testid="stStatusWidget"] summary[class*="st-emotion"] *,
summary[class*="st-emotion-cache"] * {
  color: #1A3A3C !important;
  background-color: transparent !important;
}
[data-testid="stStatusWidget"] [data-testid="stMarkdownContainer"],
[data-testid="stStatusWidget"] [data-testid="stMarkdownContainer"] p,
[data-testid="stStatusWidget"] [data-testid="stMarkdownContainer"] * {
  color: #1A3A3C !important;
  background-color: transparent !important;
}
[data-testid="stStatusWidget"]:hover {
  background: #EBD6D7 !important;
  background-color: #EBD6D7 !important;
  border-color: rgba(67, 144, 147, 0.55) !important;
  box-shadow: 0 4px 18px rgba(67, 144, 147, 0.14) !important;
}
[data-testid="stStatusWidget"]:hover > div:first-child,
[data-testid="stStatusWidget"]:hover details,
[data-testid="stStatusWidget"]:hover summary,
[data-testid="stStatusWidget"] summary:hover,
[data-testid="stStatusWidget"]:hover summary[class*="st-emotion"],
summary[class*="st-emotion-cache"]:hover {
  background: #EBD6D7 !important;
  background-color: #EBD6D7 !important;
  color: #1A3A3C !important;
}

div[data-testid="stDownloadButton"] > button {
  background: linear-gradient(135deg, #439093, #F09B93) !important;
  color: #fff !important;
  border: 1px solid rgba(67, 144, 147, 0.35) !important;
  border-radius: 12px !important;
  font-weight: 700 !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
<div class="hero-wrapper">
  <img class="hero-bg"
       src="{HERO_SRC}"
       alt="Phi Phi Island beach Thailand"/>
  <div class="hero-overlay"></div>
  <div class="hero-content">
    <div class="hero-brand">Voyage<span class="brand-ai">AI</span></div>
    <div class="hero-title">Your Dream Trip,<br/><span class="grad">Planned by AI</span></div>
    <div class="hero-sub">Tell us where you want to go — our multi-agent system finds flights, hotels, and a personalized itinerary for you.</div>
    <a class="hero-cta" id="ready-itinerary-cta" href="#plan-chat">Ready for itinerary</a>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# Smooth-scroll CTA (Streamlit markdown lives in parent; bind via iframe script)
components.html(
    """
    <script>
    (function () {
      const doc = window.parent.document;
      const bind = () => {
        const cta = doc.getElementById("ready-itinerary-cta");
        if (!cta || cta.dataset.bound === "1") return;
        cta.dataset.bound = "1";
        cta.addEventListener("click", function (e) {
          e.preventDefault();
          const target = doc.getElementById("plan-chat");
          if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
        });
      };
      bind();
      setTimeout(bind, 200);
      setTimeout(bind, 600);
    })();
    </script>
    """,
    height=0,
    width=0,
)

with st.container(key="below_fold"):

    # ── Popular Destinations (3 visible, continuous slow scroll) ──────────────────
    _slides = []
    for _name, _sub, _img in DESTINATIONS + DESTINATIONS:
        _slides.append(
            f'<div class="slide" data-name="{html.escape(_name)}">'
            f'<div class="card">'
            f'<img src="{html.escape(_img)}" alt="{html.escape(_name)}" loading="lazy"/>'
            f'<div class="label"><div class="name">{html.escape(_name)}</div>'
            f'<div class="sub">{html.escape(_sub)}</div></div>'
            f"</div></div>"
        )

    components.html(
        f""" 
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8"/>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@600;700&display=swap');
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      body {{
        margin: 0;
        font-family: 'Plus Jakarta Sans', sans-serif;
        background: transparent;
        overflow: hidden;
      }}
      .carousel {{
        width: 100%;
        overflow: hidden;
        border-radius: 16px;
        container-type: inline-size;
      }}
      .track {{
        display: flex;
        width: max-content;
        animation: dest-marquee 45s linear infinite;
      }}
      .carousel:hover .track {{ animation-play-state: paused; }}
      @keyframes dest-marquee {{
        from {{ transform: translateX(0); }}
        to {{ transform: translateX(-50%); }}
      }}
      .slide {{
        flex: 0 0 calc(100cqw / 3);
        width: calc(100cqw / 3);
        padding: 0 0.4rem;
        cursor: pointer;
      }}
      .card {{
        position: relative;
        height: 170px;
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid rgba(67, 144, 147, 0.22);
        box-shadow: 0 8px 24px rgba(67,144,147,0.12);
      }}
      .card img {{
        width: 100%;
        height: 100%;
        object-fit: cover;
        filter: brightness(0.82);
        display: block;
      }}
      .card:hover img {{ filter: brightness(0.72); }}
      .label {{
        position: absolute;
        left: 0; right: 0; bottom: 0;
        padding: 0.7rem 0.75rem;
        background: linear-gradient(transparent, rgba(26,58,60,0.72));
        color: #fff;
      }}
      .label .name {{ font-weight: 700; font-size: 0.95rem; }}
      .label .sub {{ font-size: 0.72rem; color: #F9EBD9; margin-top: 0.1rem; }}
    </style>
    </head>
    <body>
      <div class="carousel" id="carousel">
        <div class="track" id="track">{"".join(_slides)}</div>
      </div>
      <script>
      (function () {{
        const track = document.getElementById("track");
        track.addEventListener("click", function (e) {{
          const slide = e.target.closest(".slide");
          if (!slide) return;
          const name = slide.getAttribute("data-name");
          try {{
            const btn = window.parent.document.querySelector(
              'div[class*="st-key-dest_' + name + '"] button'
            );
            if (btn) btn.click();
          }} catch (err) {{}}
        }});
      }})();
      </script>
    </body>
    </html>
        """,
        height=200,
        scrolling=False,
    )

    # Bridge buttons — carousel clicks these in the parent document
    for name, _, _ in DESTINATIONS:
        if st.button(name, key=f"dest_{name}"):
            st.session_state.trip_query = DESTINATION_PROMPTS[name]
            st.session_state.scroll_to_chat = True
            st.rerun()

    st.markdown("<br/>", unsafe_allow_html=True)

    # ── Describe Your Trip + Thinking panel ───────────────────────────────────────
    st.markdown('<div id="plan-chat"></div>', unsafe_allow_html=True)

    if st.session_state.pop("scroll_to_chat", False):
        components.html(
            """
            <script>
            (function () {
              const target = window.parent.document.getElementById("plan-chat");
              if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
            })();
            </script>
            """,
            height=0,
            width=0,
        )

    left, right = st.columns([1.35, 1], gap="large")

    with left:
        user_query = st.text_area(
            "trip_description",
            key="trip_query",
            placeholder="e.g. Plan a 7-day trip to Japan including flights, hotels and sightseeing under ₹2 lakhs",
            height=130,
            label_visibility="collapsed",
        )
        generate = st.button(
            "Generate My Travel Plan  →",
            type="primary",
            use_container_width=True,
        )

    with right:
        think_slot = st.empty()
        think_slot.markdown(
            thinking_panel_html(st.session_state.thinking_steps, active=False),
            unsafe_allow_html=True,
        )

    thread_id = "1"

    # ── Agent pipeline + results ──────────────────────────────────────────────────
    if generate:
        if not (user_query or "").strip():
            st.warning("Please describe your trip first.")
        else:
            st.session_state.thinking_steps = set()
            think_slot.markdown(
                thinking_panel_html(set(), active=True),
                unsafe_allow_html=True,
            )
            config = {"configurable": {"thread_id": thread_id}}
            collected = {
                "flight_results": "",
                "hotel_results": "",
                "itinerary": "",
                "final_response": "",
                "llm_calls": 0,
            }

            st.markdown(
                "<div class='sec-head'><span>Agent Pipeline — Live</span></div>",
                unsafe_allow_html=True,
            )

            for chunk in app.stream(
                {
                    "messages": [HumanMessage(content=user_query)],
                    "user_query": user_query,
                    "flight_results": "",
                    "hotel_results": "",
                    "itinerary": "",
                    "llm_calls": 0,
                },
                config=config,
                stream_mode="updates",
            ):
                for node_name, state_update in chunk.items():
                    label = AGENT_META.get(node_name, node_name)
                    st.session_state.thinking_steps.add(node_name)
                    think_slot.markdown(
                        thinking_panel_html(st.session_state.thinking_steps, active=True),
                        unsafe_allow_html=True,
                    )

                    with st.status(label, state="complete", expanded=True):
                        if node_name == "flight_agent":
                            text = state_update.get("flight_results", "")
                            collected["flight_results"] = text
                            st.markdown(text or "_No flight data returned._")

                        elif node_name == "hotel_agent":
                            text = state_update.get("hotel_results", "")
                            collected["hotel_results"] = text
                            st.markdown(text or "_No hotel data returned._")

                        elif node_name == "itinerary_agent":
                            text = state_update.get("itinerary", "")
                            collected["itinerary"] = text
                            st.markdown(text or "_No itinerary generated._")

                        elif node_name == "final_agent":
                            msgs = state_update.get("messages", [])
                            text = msgs[-1].content if msgs else ""
                            collected["final_response"] = text
                            st.markdown(text or "_No final response._")

                        collected["llm_calls"] = state_update.get(
                            "llm_calls", collected["llm_calls"]
                        )

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"travel_plan_{timestamp}.md"
            save_dir = os.path.join(os.path.dirname(__file__), "travel_plans")
            os.makedirs(save_dir, exist_ok=True)

            file_content = f"""# Travel Plan
    **Query:** {user_query}
    **Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    ---

    ## Flight Information
    {collected['flight_results'] or 'N/A'}

    ---

    ## Hotel Information
    {collected['hotel_results'] or 'N/A'}

    ---

    ## Itinerary
    {collected['itinerary'] or 'N/A'}

    ---

    ## Final Travel Plan
    {collected['final_response'] or 'N/A'}

    ---
    *LLM Calls: {collected['llm_calls']}*
    """
            with open(os.path.join(save_dir, filename), "w", encoding="utf-8") as f:
                f.write(file_content)

            st.session_state.plan_result = {
                "collected": collected,
                "file_content": file_content,
                "filename": filename,
                "user_query": user_query,
            }
            think_slot.markdown(
                thinking_panel_html(st.session_state.thinking_steps, active=False),
                unsafe_allow_html=True,
            )

    # ── Plan results (only after a trip is generated) ─────────────────────────────
    plan = st.session_state.plan_result
    if plan:
        collected = plan["collected"]
        st.markdown(
            f"""
            <div class="metric-row">
              <div class="metric-box"><div class="metric-val">4</div><div class="metric-lbl">Agents Run</div></div>
              <div class="metric-box"><div class="metric-val">{collected['llm_calls']}</div><div class="metric-lbl">LLM Calls</div></div>
              <div class="metric-box"><div class="metric-val">Ready</div><div class="metric-lbl">Status</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if collected.get("final_response"):
            safe = html.escape(collected["final_response"]).replace("\n", "<br/>")
            st.markdown(f"<div class='final-card'>{safe}</div>", unsafe_allow_html=True)

        dl_col, info_col = st.columns([1, 3])
        with dl_col:
            st.download_button(
                "Download Plan",
                data=plan["file_content"],
                file_name=plan["filename"],
                mime="text/markdown",
                use_container_width=True,
                key="download_plan",
            )
        with info_col:
            st.markdown(
                f"<div class='save-bar'>Auto-saved → <code>travel_plans/{plan['filename']}</code></div>",
                unsafe_allow_html=True,
            )
