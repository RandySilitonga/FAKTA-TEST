"""
FAKTA — Fact-Checking AI
Premium glassmorphism Streamlit UI.
"""

import os
import sys
import json
import time
import base64
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(dotenv_path=_env_path)
except ImportError:
    pass

import streamlit as st
import requests

# ============================================================
# Page Config
# ============================================================
st.set_page_config(
    page_title="FAKTA — Fact-Checking AI",
    page_icon="\U0001f50d",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# Global CSS — Premium Glassmorphism
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    /* === RESET === */
    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif !important; }
    html, body { margin: 0; padding: 0; }
    .stApp { background: transparent !important; }
    #root > div:first-child { background: transparent !important; }
    [data-testid="stAppViewContainer"] { background: transparent !important; }
    [data-testid="stAppViewContainer"] > div { background: transparent !important; }
    [data-testid="stHeader"] { background: transparent !important; }
    .element-container { background: transparent !important; }
    [data-testid="stVerticalBlock"] { gap: 0.5rem !important; }

    /* === DEEP BACKGROUND === */
    .bg-layer {
        position: fixed;
        top: 0; left: 0;
        width: 100vw; height: 100vh;
        z-index: -2;
        background: #060608;
        overflow: hidden;
    }

    /* === ANIMATED GRADIENT ORBS === */
    .glow-orb {
        position: absolute;
        border-radius: 50%;
        pointer-events: none;
        will-change: transform, opacity;
        filter: blur(60px);
    }
    .glow-orb--a {
        width: 600px; height: 600px;
        background: radial-gradient(circle, rgba(59, 130, 246, 0.18) 0%, transparent 65%);
        top: -10%; left: -5%;
        animation: drift-a 25s ease-in-out infinite alternate;
    }
    .glow-orb--b {
        width: 500px; height: 500px;
        background: radial-gradient(circle, rgba(139, 92, 246, 0.15) 0%, transparent 65%);
        top: 40%; right: -5%;
        animation: drift-b 30s ease-in-out infinite alternate-reverse;
    }
    .glow-orb--c {
        width: 400px; height: 400px;
        background: radial-gradient(circle, rgba(6, 182, 212, 0.12) 0%, transparent 65%);
        bottom: -5%; left: 30%;
        animation: drift-c 20s ease-in-out infinite alternate;
    }
    @keyframes drift-a {
        0%   { transform: translate(0, 0) scale(1); opacity: 0.7; }
        50%  { opacity: 1; }
        100% { transform: translate(100px, 80px) scale(1.1); opacity: 0.6; }
    }
    @keyframes drift-b {
        0%   { transform: translate(0, 0) scale(1); opacity: 0.5; }
        50%  { opacity: 0.9; }
        100% { transform: translate(-80px, 60px) scale(0.9); opacity: 0.7; }
    }
    @keyframes drift-c {
        0%   { transform: translate(0, 0) scale(0.9); opacity: 0.4; }
        50%  { opacity: 0.8; }
        100% { transform: translate(70px, -50px) scale(1.1); opacity: 0.5; }
    }

    /* === NOISE OVERLAY === */
    .noise-overlay {
        position: fixed;
        top: 0; left: 0;
        width: 100vw; height: 100vh;
        z-index: -1;
        pointer-events: none;
        opacity: 0.015;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3' /%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' /%3E%3C/svg%3E");
    }

    /* === GLASS CARD === */
    .glass-card {
        background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%);
        -webkit-backdrop-filter: blur(30px) saturate(180%);
        backdrop-filter: blur(30px) saturate(180%);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 20px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255,255,255,0.04);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .glass-card:hover {
        border-color: rgba(255, 255, 255, 0.1);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255,255,255,0.06);
    }

    /* === HERO TITLE === */
    .hero-title {
        font-size: 42px;
        font-weight: 800;
        letter-spacing: -0.04em;
        margin: 0;
        background: linear-gradient(135deg, #ffffff 0%, rgba(255,255,255,0.5) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1.1;
    }
    .hero-subtitle {
        color: rgba(255, 255, 255, 0.35);
        font-size: 14px;
        font-weight: 400;
        margin: 6px 0 0;
        letter-spacing: 0.01em;
    }

    /* === INPUTS === */
    .stTextInput > div > div,
    .stTextArea > div > div {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        border-radius: 14px !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    .stTextInput > div > div:focus-within,
    .stTextArea > div > div:focus-within {
        border-color: rgba(99, 102, 241, 0.3) !important;
        box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.08) !important;
        background: rgba(255, 255, 255, 0.05) !important;
    }
    .stTextInput input, .stTextArea textarea {
        color: rgba(255, 255, 255, 0.9) !important;
        font-size: 15px !important;
    }
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {
        color: rgba(255, 255, 255, 0.18) !important;
    }
    .stTextArea textarea { line-height: 1.6 !important; }

    /* === BUTTONS === */
    .stButton > button {
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        color: rgba(255, 255, 255, 0.7) !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        padding: 10px 24px !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: none !important;
    }
    .stButton > button:hover {
        background: rgba(255, 255, 255, 0.08) !important;
        border-color: rgba(255, 255, 255, 0.12) !important;
        color: rgba(255, 255, 255, 0.9) !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1 0%, #818cf8 100%) !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.25) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #818cf8 0%, #6366f1 100%) !important;
        box-shadow: 0 6px 28px rgba(99, 102, 241, 0.35) !important;
        transform: translateY(-1px);
    }

    /* === STAT CARD === */
    .stat-card {
        text-align: center;
        padding: 24px 12px;
        border-radius: 16px;
        background: linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%);
        border: 1px solid rgba(255, 255, 255, 0.05);
        -webkit-backdrop-filter: blur(20px);
        backdrop-filter: blur(20px);
        transition: all 0.3s ease;
    }
    .stat-card:hover {
        border-color: rgba(255, 255, 255, 0.08);
        background: linear-gradient(135deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.02) 100%);
    }
    .stat-card__value {
        font-size: 36px;
        font-weight: 800;
        letter-spacing: -0.04em;
        line-height: 1;
        margin: 0;
    }
    .stat-card__label {
        font-size: 10px;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.3);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-top: 10px;
    }

    /* === PROGRESS BAR === */
    .progress-bar {
        background: rgba(255, 255, 255, 0.04);
        border-radius: 999px;
        height: 6px;
        overflow: hidden;
        position: relative;
    }
    .progress-bar__fill {
        height: 100%;
        border-radius: 999px;
        transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    .progress-bar__fill::after {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        animation: shimmer 2s linear infinite;
    }
    @keyframes shimmer {
        0%   { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }
    .progress-label {
        font-size: 12px;
        font-weight: 500;
        color: rgba(255, 255, 255, 0.4);
        margin-top: 8px;
        display: flex;
        justify-content: space-between;
    }

    /* === VERDICT BANNER === */
    .verdict-banner {
        border-radius: 20px;
        padding: 32px 36px;
        position: relative;
        overflow: hidden;
        -webkit-backdrop-filter: blur(24px);
        backdrop-filter: blur(24px);
    }
    .verdict-banner::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
    }
    .verdict-banner--hoax {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.08) 0%, rgba(239, 68, 68, 0.02) 100%);
        border: 1px solid rgba(239, 68, 68, 0.15);
    }
    .verdict-banner--valid {
        background: linear-gradient(135deg, rgba(34, 197, 94, 0.08) 0%, rgba(34, 197, 94, 0.02) 100%);
        border: 1px solid rgba(34, 197, 94, 0.15);
    }
    .verdict-banner--nei {
        background: linear-gradient(135deg, rgba(234, 179, 8, 0.08) 0%, rgba(234, 179, 8, 0.02) 100%);
        border: 1px solid rgba(234, 179, 8, 0.15);
    }
    .verdict-banner--unknown {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.04) 0%, rgba(255, 255, 255, 0.01) 100%);
        border: 1px solid rgba(255, 255, 255, 0.06);
    }
    .verdict-title {
        font-size: 24px;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin: 0 0 8px;
    }
    .verdict-title--hoax { color: #f87171; }
    .verdict-title--valid { color: #4ade80; }
    .verdict-title--nei { color: #facc15; }
    .verdict-title--unknown { color: rgba(255,255,255,0.6); }
    .verdict-summary {
        color: rgba(255, 255, 255, 0.4);
        font-size: 14px;
        line-height: 1.6;
        margin: 0;
    }

    /* === BADGE === */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 8px;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        border: 1px solid;
    }
    .badge--hoax  { background: rgba(239, 68, 68, 0.1); color: #f87171; border-color: rgba(239, 68, 68, 0.15); }
    .badge--valid { background: rgba(34, 197, 94, 0.08); color: #4ade80; border-color: rgba(34, 197, 94, 0.12); }
    .badge--nei   { background: rgba(234, 179, 8, 0.08); color: #facc15; border-color: rgba(234, 179, 8, 0.12); }
    .badge--info  { background: rgba(255, 255, 255, 0.03); color: rgba(255, 255, 255, 0.4); border-color: rgba(255, 255, 255, 0.06); }

    /* === SIDEBAR === */
    [data-testid="stSidebar"] {
        background: rgba(8, 8, 12, 0.9) !important;
        -webkit-backdrop-filter: blur(30px) saturate(180%) !important;
        backdrop-filter: blur(30px) saturate(180%) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.04) !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
        color: rgba(255, 255, 255, 0.7) !important;
    }

    /* === EXPANDERS === */
    div[data-testid="stExpander"] {
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 14px !important;
        overflow: hidden !important;
        background: rgba(255, 255, 255, 0.02) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        backdrop-filter: blur(20px) !important;
        transition: all 0.25s ease !important;
    }
    div[data-testid="stExpander"]:hover {
        border-color: rgba(255, 255, 255, 0.08) !important;
    }
    div[data-testid="stExpander"] > summary {
        background: transparent !important;
        color: rgba(255, 255, 255, 0.6) !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        padding: 14px 18px !important;
    }
    div[data-testid="stExpander"] > summary:hover {
        background: rgba(255, 255, 255, 0.02) !important;
    }
    div[data-testid="stExpander"] > div {
        background: transparent !important;
        padding: 0 18px 14px !important;
    }

    /* === SECTION HEADING === */
    .section-heading {
        font-size: 12px;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.3);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin: 28px 0 12px;
    }

    /* === DIVIDER === */
    .stDivider {
        border-color: rgba(255, 255, 255, 0.04) !important;
    }

    /* === ALERTS === */
    .stAlert {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        border-radius: 12px !important;
    }

    /* === RADIO === */
    .stRadio > label { color: rgba(255, 255, 255, 0.4) !important; font-size: 13px !important; }

    /* === HIDE BRANDING === */
    #MainMenu { visibility: hidden !important; }
    footer { visibility: hidden !important; }

    /* === SCROLLBAR === */
    ::-webkit-scrollbar { width: 5px !important; }
    ::-webkit-scrollbar-track { background: transparent !important; }
    ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.06) !important; border-radius: 3px !important; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.1) !important; }

    /* === SPINNER === */
    .stSpinner > div {
        border-color: rgba(255, 255, 255, 0.1) !important;
        border-top-color: rgba(99, 102, 241, 0.6) !important;
    }

    /* === JSON === */
    .stJson {
        background: rgba(0, 0, 0, 0.2) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255,255,255,0.04) !important;
    }

    /* === HISTORY ROW === */
    .history-row {
        padding: 10px 14px;
        margin: 6px 0;
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.03);
        border-radius: 10px;
        font-size: 12px;
        color: rgba(255, 255, 255, 0.5);
        transition: all 0.2s ease;
    }
    .history-row:hover {
        background: rgba(255, 255, 255, 0.04);
        border-color: rgba(255, 255, 255, 0.06);
    }

    /* === EXPORT LINK === */
    .export-link {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 10px 18px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        color: rgba(255, 255, 255, 0.5) !important;
        text-decoration: none !important;
        font-size: 13px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .export-link:hover {
        background: rgba(255, 255, 255, 0.06);
        color: rgba(255, 255, 255, 0.8) !important;
        border-color: rgba(255, 255, 255, 0.1);
    }

    /* === FOOTER === */
    .footer {
        color: rgba(255, 255, 255, 0.12);
        font-size: 11px;
        text-align: center;
        padding: 32px 0 16px;
    }

    /* === FADE-IN ANIMATION === */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(12px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .fade-in { animation: fadeInUp 0.5s cubic-bezier(0.4, 0, 0.2, 1); }

    /* === PIPELINE INDICATOR === */
    .pipeline-step {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 6px 0;
        font-size: 12px;
        color: rgba(255, 255, 255, 0.4);
    }
    .pipeline-dot {
        width: 6px; height: 6px;
        border-radius: 50%;
        background: rgba(99, 102, 241, 0.4);
        flex-shrink: 0;
    }

    /* === CLAIM DETAIL === */
    .claim-header {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        flex-wrap: wrap;
        margin-bottom: 16px;
    }
    .claim-text {
        color: rgba(255, 255, 255, 0.7);
        font-size: 14px;
        line-height: 1.55;
        margin: 0 0 12px;
    }
    .signal-label {
        font-size: 10px;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.25);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 6px;
    }
    .signal-value {
        font-size: 20px;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# Background Layers
# ============================================================
st.markdown("""
<div class="bg-layer">
    <div class="glow-orb glow-orb--a"></div>
    <div class="glow-orb glow-orb--b"></div>
    <div class="glow-orb glow-orb--c"></div>
</div>
<div class="noise-overlay"></div>
""", unsafe_allow_html=True)


# ============================================================
# Helpers
# ============================================================

API_URL = os.environ.get("FAKTA_API_URL", "http://localhost:8000")


def check_article(text: str, title: str = "") -> dict | None:
    payload = {"text": text, "title": title}
    try:
        response = requests.post(f"{API_URL}/check", json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error("Tidak bisa terhubung ke API. Pastikan server berjalan.")
        return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None


def submit_feedback(claim, system_verdict, human_verdict, is_correct, notes=""):
    payload = {
        "claim": claim,
        "system_verdict": system_verdict,
        "human_verdict": human_verdict,
        "is_correct": is_correct,
        "notes": notes,
    }
    try:
        return requests.post(f"{API_URL}/feedback", json=payload, timeout=10).status_code == 200
    except Exception:
        return False


def get_stats() -> dict | None:
    try:
        r = requests.get(f"{API_URL}/stats", timeout=5)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def verdict_variant(v: str) -> str:
    v_lower = v.lower()
    if "tidak" in v_lower and "hoax" in v_lower and "cukup" not in v_lower and "dapat" not in v_lower:
        return "valid"
    elif "cukup" in v_lower or "dapat" in v_lower:
        return "nei"
    elif "hoax" in v_lower:
        return "hoax"
    return "unknown"


def badge_cls(v: str) -> str:
    return f"badge--{verdict_variant(v)}"


def progress_bar(value: float, color: str = "rgba(255,255,255,0.3)", label: str = "") -> str:
    pct = min(value * 100, 100)
    return f"""
    <div class="progress-bar">
        <div class="progress-bar__fill" style="width:{pct}%;background:{color};"></div>
    </div>
    <div class="progress-label">
        <span>{label}</span>
        <span>{value:.0%}</span>
    </div>
    """


def export_link(result: dict) -> str:
    j = json.dumps(result, indent=2, ensure_ascii=False)
    b64 = base64.b64encode(j.encode()).decode()
    fn = f"fakta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return f'<a class="export-link" href="data:application/json;base64,{b64}" download="{fn}">⬇ Export JSON</a>'


# ============================================================
# Session State
# ============================================================
if "history" not in st.session_state:
    st.session_state.history = []
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "example_text" not in st.session_state:
    st.session_state.example_text = ""

# ============================================================
# Sidebar
# ============================================================
with st.sidebar:
    st.markdown("""
    <div style="padding: 8px 0 16px;">
        <h3 style="font-size:18px;font-weight:700;color:rgba(255,255,255,0.9);margin:0;letter-spacing:-0.02em;">FAKTA</h3>
        <p style="color:rgba(255,255,255,0.25);font-size:12px;margin:2px 0 0;">Fact-Checking AI</p>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    # Connection status
    try:
        r = requests.get(f"{API_URL}/", timeout=3)
        if r.status_code == 200:
            st.markdown("""
            <div style="display:flex;align-items:center;gap:8px;padding:8px 12px;background:rgba(34,197,94,0.06);border:1px solid rgba(34,197,94,0.12);border-radius:10px;">
                <div style="width:8px;height:8px;border-radius:50%;background:#4ade80;box-shadow:0 0 8px #4ade80;"></div>
                <span style="color:rgba(255,255,255,0.6);font-size:12px;font-weight:500;">API Connected</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="display:flex;align-items:center;gap:8px;padding:8px 12px;background:rgba(234,179,8,0.06);border:1px solid rgba(234,179,8,0.12);border-radius:10px;">
                <div style="width:8px;height:8px;border-radius:50%;background:#facc15;"></div>
                <span style="color:rgba(255,255,255,0.6);font-size:12px;font-weight:500;">Unresponsive</span>
            </div>
            """, unsafe_allow_html=True)
    except:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;padding:8px 12px;background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.12);border-radius:10px;">
            <div style="width:8px;height:8px;border-radius:50%;background:#f87171;"></div>
            <span style="color:rgba(255,255,255,0.6);font-size:12px;font-weight:500;">Disconnected</span>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    with st.expander("System Statistics"):
        s = get_stats()
        if s:
            if s.get("pipeline_initialized"):
                st.success("Pipeline active")
            else:
                st.warning("Pipeline not initialized")
            c = s.get("cache_stats", {})
            if c:
                st.json(c)
        else:
            st.info("Unavailable")

    st.divider()

    with st.expander("History"):
        if st.session_state.history:
            for ts, snippet, v, _ in reversed(st.session_state.history[-10:]):
                badge = badge_cls(v)
                short = snippet[:40] + ("..." if len(snippet) > 40 else "")
                st.markdown(
                    f'<div class="history-row">'
                    f'<span class="badge {badge}" style="margin-bottom:6px;">{v}</span><br>'
                    f'<span style="color:rgba(255,255,255,0.5);">{short}</span><br>'
                    f'<span style="color:rgba(255,255,255,0.15);font-size:10px;">{ts}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No history yet.")

    st.divider()

    st.markdown("""
    <div style="padding: 8px 0;">
        <p style="font-size:12px;font-weight:600;color:rgba(255,255,255,0.3);text-transform:uppercase;letter-spacing:0.1em;margin:0 0 10px;">Evidence Sources</p>
        <div class="pipeline-step"><div class="pipeline-dot"></div>Google Fact Check API</div>
        <div class="pipeline-step"><div class="pipeline-dot"></div>TurnBackHoax / MAFINDO</div>
        <div class="pipeline-step"><div class="pipeline-dot"></div>Official sources (BPOM, BMKG)</div>
        <div class="pipeline-step"><div class="pipeline-dot"></div>Wikipedia (fallback)</div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# Main Content
# ============================================================

# --- Hero ---
st.markdown("""
<div class="fade-in" style="padding: 40px 0 28px;">
    <h1 class="hero-title">FAKTA</h1>
    <p class="hero-subtitle">Hybrid LSTM + LLM + Evidence — Indonesian Hoax Detection</p>
</div>
""", unsafe_allow_html=True)

# --- Input Card ---
st.markdown('<div class="glass-card fade-in" style="padding: 28px 32px; margin-bottom: 8px;">', unsafe_allow_html=True)

mode = st.radio("Input Mode", ["Text", "URL"], horizontal=True, label_visibility="collapsed")

with st.form("check_form", clear_on_submit=False):
    if mode == "Text":
        title_input = st.text_input("Title", placeholder="Optional article title...")
        text_input = st.text_area(
            "Article Text",
            value=st.session_state.get("example_text", ""),
            placeholder="Paste the article or post text here...",
            height=160,
            label_visibility="collapsed",
        )
    else:
        url_val = st.text_input("Article URL", placeholder="https://example.com/article")
        st.caption("URL content will be fetched and analyzed.")
        title_input = ""
        text_input = url_val

    b1, b2, _ = st.columns([1, 1, 4])
    with b1:
        submitted = st.form_submit_button("Check", use_container_width=True, type="primary")
    with b2:
        clear_btn = st.form_submit_button("Reset", use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)

if clear_btn:
    st.session_state.last_result = None
    st.session_state.example_text = ""
    st.rerun()

# ============================================================
# Process
# ============================================================
if submitted:
    check_text = text_input.strip()
    if not check_text:
        st.warning("Masukkan teks atau URL untuk diperiksa.")
        st.stop()

    with st.spinner("Analyzing..."):
        result = check_article(check_text, title_input)

    if not result:
        st.stop()

    st.session_state.last_result = result

    ts = datetime.now().strftime("%H:%M")
    snippet = title_input or check_text
    st.session_state.history.append((ts, snippet, result["verdict"], result))

    v = verdict_variant(result["verdict"])
    color_map = {"hoax": "#f87171", "valid": "#4ade80", "nei": "#facc15", "unknown": "rgba(255,255,255,0.5)"}
    v_color = color_map[v]

    # --- Verdict Banner ---
    st.markdown(f"""
    <div class="verdict-banner verdict-banner--{v} fade-in" style="margin-top: 20px;">
        <p class="verdict-title verdict-title--{v}">{result["verdict"]}</p>
        <p class="verdict-summary">{result.get("summary", "")}</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Metrics ---
    st.markdown('<p class="section-heading">Overview</p>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div class="stat-card fade-in">'
            f'<p class="stat-card__value" style="color:{v_color};">{result["confidence"]:.0%}</p>'
            f'<p class="stat-card__label">Confidence</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c2:
        hs = result["avg_hoax_score"]
        hs_c = "#f87171" if hs > 0.6 else ("#4ade80" if hs < 0.3 else "#facc15")
        st.markdown(
            f'<div class="stat-card fade-in">'
            f'<p class="stat-card__value" style="color:{hs_c};">{hs:.2f}</p>'
            f'<p class="stat-card__label">Hoax Score</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="stat-card fade-in">'
            f'<p class="stat-card__value" style="color:rgba(255,255,255,0.5);">{result.get("processing_time_ms", 0):.0f}</p>'
            f'<p class="stat-card__label">ms</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # --- Signal Bars ---
    st.markdown('<p class="section-heading">Analysis Signals</p>', unsafe_allow_html=True)
    g1, g2 = st.columns(2)
    with g1:
        conf = result["confidence"]
        gc = v_color if conf > 0.5 else "rgba(255,255,255,0.2)"
        st.markdown(progress_bar(conf, gc, "Confidence"), unsafe_allow_html=True)
    with g2:
        hs = result["avg_hoax_score"]
        hc = "#f87171" if hs > 0.6 else ("#4ade80" if hs < 0.3 else "#facc15")
        st.markdown(progress_bar(hs, hc, "Hoax Score"), unsafe_allow_html=True)

    # --- Claims ---
    if result.get("claims"):
        st.markdown('<p class="section-heading">Claim Breakdown</p>', unsafe_allow_html=True)

        for i, claim in enumerate(result["claims"], 1):
            c_badge = badge_cls(claim["verdict"])
            claim_type = claim.get("claim_type", "").capitalize()
            short_text = claim['claim_text'][:80] + ("..." if len(claim['claim_text']) > 80 else "")

            with st.expander(f"Claim {i}: {short_text}"):
                # Badges
                st.markdown(
                    f'<div class="claim-header">'
                    f'<span class="badge {c_badge}">{claim["verdict"]}</span>'
                    f'<span class="badge badge--info">{claim_type}</span>'
                    f'<span class="badge badge--info">{claim["mode"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                # Claim text
                st.markdown(f'<p class="claim-text">{claim["claim_text"]}</p>', unsafe_allow_html=True)

                # Signal row
                s1, s2, s3 = st.columns(3)
                with s1:
                    lh = claim.get("lstm_hoax_proba", 0)
                    lc = "#f87171" if lh > 0.5 else "#4ade80"
                    st.markdown(f"""
                    <div>
                        <p class="signal-label">LSTM</p>
                        <p class="signal-value" style="color:{lc};">{lh:.0%}</p>
                    </div>
                    {progress_bar(lh, lc, "Hoax Probability")}
                    """, unsafe_allow_html=True)
                with s2:
                    lj = claim.get("llm_confidence", 0)
                    st.markdown(f"""
                    <div>
                        <p class="signal-label">LLM Judge</p>
                        <p class="signal-value" style="color:#a78bfa;">{lj:.0%}</p>
                    </div>
                    <p style="font-size:12px;color:rgba(255,255,255,0.4);margin:4px 0 8px;">{claim.get("llm_verdict", "")}</p>
                    {progress_bar(lj, "#a78bfa", "Confidence")}
                    """, unsafe_allow_html=True)
                with s3:
                    sources = claim.get("evidence_sources", [])
                    st.markdown(f"""
                    <div>
                        <p class="signal-label">Evidence</p>
                        <p class="signal-value" style="color:rgba(255,255,255,0.5);">{len(sources)}</p>
                    </div>
                    <p style="font-size:11px;color:rgba(255,255,255,0.3);margin:4px 0 8px;line-height:1.5;">{", ".join(sources) if sources else "None found"}</p>
                    """, unsafe_allow_html=True)

                # Fusion
                st.markdown("---")
                fc = claim.get("confidence", 0)
                st.markdown(f"""
                <p class="signal-label">Fusion Result</p>
                {progress_bar(fc, v_color, "Confidence")}
                <p style="font-size:13px;color:rgba(255,255,255,0.35);margin:12px 0 0;line-height:1.6;">{claim.get("reasoning", "")}</p>
                """, unsafe_allow_html=True)

    # --- Claim Stats ---
    if result.get("claim_stats"):
        cs = result["claim_stats"]
        st.markdown('<p class="section-heading">Claim Summary</p>', unsafe_allow_html=True)

        total = cs.get("total_claims", 0)
        hoax = cs.get("hoax_claims", 0)
        valid = cs.get("valid_claims", 0)
        nei = cs.get("nei_claims", 0) or cs.get("uncertain_claims", 0)

        s1, s2, s3, s4 = st.columns(4)
        with s1:
            st.markdown(f'<div class="stat-card"><p class="stat-card__value" style="color:rgba(255,255,255,0.6);">{total}</p><p class="stat-card__label">Total</p></div>', unsafe_allow_html=True)
        with s2:
            st.markdown(f'<div class="stat-card"><p class="stat-card__value" style="color:#f87171;">{hoax}</p><p class="stat-card__label">Hoax</p></div>', unsafe_allow_html=True)
        with s3:
            st.markdown(f'<div class="stat-card"><p class="stat-card__value" style="color:#4ade80;">{valid}</p><p class="stat-card__label">Valid</p></div>', unsafe_allow_html=True)
        with s4:
            st.markdown(f'<div class="stat-card"><p class="stat-card__value" style="color:#facc15;">{nei}</p><p class="stat-card__label">Insufficient Evidence</p></div>', unsafe_allow_html=True)

    # --- Export & Raw ---
    st.markdown("---")
    st.markdown(export_link(result), unsafe_allow_html=True)

    with st.expander("Raw JSON"):
        st.json(result)

    # --- Feedback ---
    st.markdown('<p class="section-heading">Feedback</p>', unsafe_allow_html=True)
    st.caption("Help us improve accuracy by providing your assessment.")

    if result.get("claims"):
        opts = [f"Claim {i+1}: {c['claim_text'][:50]}{'...' if len(c['claim_text']) > 50 else ''}" for i, c in enumerate(result["claims"])]
        idx = st.selectbox("Select Claim", range(len(opts)), format_func=lambda i: opts[i])
        sel = result["claims"][idx]

        f1, f2 = st.columns([3, 2])
        with f1:
            hv = st.radio("Your verdict", ["Hoax", "Valid", "Insufficient Evidence"], horizontal=True)
        with f2:
            notes = st.text_input("Notes (optional)")

        if st.button("Submit Feedback", use_container_width=True, type="primary"):
            ok = submit_feedback(sel["claim_text"], sel["verdict"], hv, hv == sel["verdict"], notes)
            if ok:
                st.success("Feedback submitted. Terima kasih!")
            else:
                st.warning("API unavailable, but feedback noted locally.")

else:
    # --- Examples ---
    st.markdown("---")
    st.markdown('<p class="section-heading">Try an Example</p>', unsafe_allow_html=True)

    examples = [
        ("Hoax Example", "VIRAL!!! Matcha menyebabkan gagal ginjal dan sudah banyak korban meninggal!! Sebarkan sebelum dihapus!! Obat ini disembunyikan oleh pemerintah!!"),
        ("Valid Example", "BMKG mencatat gempa magnitudo 5.2 di Maluku pada tanggal 15 Januari 2025. Gempa tidak berpotensi tsunami. Warga dihimbau tetap tenang."),
        ("Uncertain Example", "Kabar beredar bahwa harga BBM akan naik bulan depan. Pemerintah belum memberikan konfirmasi resmi mengenai hal ini."),
    ]

    cols = st.columns(3)
    for col, (label, txt) in zip(cols, examples):
        with col:
            if st.button(label, use_container_width=True):
                st.session_state.example_text = txt
                st.rerun()

# Footer
st.markdown('<p class="footer">FAKTA v2.0 — Hybrid LSTM + LLM + Evidence</p>', unsafe_allow_html=True)
