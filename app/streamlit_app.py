"""
FAKTA - Streamlit Demo UI
Interactive fact-checking interface.
"""

import os
import sys
import json
import time
from pathlib import Path

import streamlit as st
import requests

# Page config
st.set_page_config(
    page_title="FAKTA — Fact-Checking AI",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
.verdict-hoax { color: #dc3545; font-weight: bold; }
.verdict-valid { color: #28a745; font-weight: bold; }
.verdict-nei { color: #ffc107; font-weight: bold; }
.claim-card {
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 16px;
    margin: 8px 0;
    background: #f8f9fa;
}
</style>
""", unsafe_allow_html=True)

# API endpoint (set via env or default to localhost)
API_URL = os.environ.get("FAKTA_API_URL", "http://localhost:8000")


def check_article(text: str, title: str = "") -> dict:
    """Send text to FAKTA API for checking."""
    payload = {"text": text, "title": title}

    try:
        response = requests.post(f"{API_URL}/check", json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error("Tidak dapat terhubung ke API. Pastikan server berjalan.")
        return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None


def get_verdict_class(verdict: str) -> str:
    """Get CSS class for verdict."""
    if "Hoax" in verdict:
        return "verdict-hoax"
    elif "Tidak Hoax" in verdict:
        return "verdict-valid"
    else:
        return "verdict-nei"


def get_verdict_emoji(verdict: str) -> str:
    if "Hoax" in verdict and "Tidak" not in verdict:
        return "❌"
    elif "Tidak Hoax" in verdict:
        return "✅"
    else:
        return "⚠️"


# ============================================================
# Sidebar
# ============================================================

with st.sidebar:
    st.title("🔍 FAKTA")
    st.caption("Fact-Checking AI — Hybrid LSTM + LLM + Evidence")
    st.divider()

    st.markdown("### Cara Penggunaan")
    st.markdown("""
    1. Masukkan judul dan teks berita
    2. Klik **"Periksa"**
    3. Lihat hasil fact-checking
    """)

    st.divider()
    st.markdown("### Sumber Evidence")
    st.markdown("""
    - Google Fact Check API
    - TurnBackHoax / MAFINDO
    - Sumber resmi (BPOM, BMKG, dll)
    - Media kredibel
    - Wikipedia (fallback)
    """)

    st.divider()
    api_status = st.empty()
    try:
        r = requests.get(f"{API_URL}/", timeout=3)
        if r.status_code == 200:
            api_status.success("✅ API terhubung")
        else:
            api_status.warning("⚠️ API tidak responsif")
    except:
        api_status.error("❌ API tidak terhubung")


# ============================================================
# Main Content
# ============================================================

st.title("🔍 FAKTA — Fact-Checking AI")
st.caption("Sistem pendeteksi hoaks Bahasa Indonesia berbasis Hybrid LSTM + LLM + Evidence")

# Input form
with st.form("check_form"):
    title = st.text_input("Judul Berita (opsional)")
    text = st.text_area("Teks Berita", height=200, placeholder="Paste judul dan isi berita di sini...")

    col1, col2 = st.columns([1, 4])
    with col1:
        submitted = st.form_submit_button("🔍 Periksa", use_container_width=True)

# Process
if submitted and text.strip():
    with st.spinner("Memeriksa klaim..."):
        start = time.time()
        result = check_article(text.strip(), title)
        elapsed = time.time() - start

    if result:
        # Verdict header
        verdict_class = get_verdict_class(result["verdict"])
        emoji = get_verdict_emoji(result["verdict"])

        st.markdown(f"### {emoji} Verdict: <span class='{verdict_class}'>{result['verdict']}</span>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Confidence", f"{result['confidence']:.1%}")
        with col2:
            st.metric("Hoax Score", f"{result['avg_hoax_score']:.2f}")
        with col3:
            st.metric("Processing Time", f"{result.get('processing_time_ms', 0):.0f}ms")

        st.info(result["summary"])

        # Claim details
        if result.get("claims"):
            st.markdown("### Detail Klaim")

            for i, claim in enumerate(result["claims"], 1):
                with st.expander(f"Klaim {i}: {claim['claim_text'][:80]}..."):
                    c_emoji = get_verdict_emoji(claim["verdict"])
                    st.markdown(f"**Verdict:** {c_emoji} {claim['verdict']}")

                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("Confidence", f"{claim['confidence']:.1%}")
                        st.metric("LSTM Hoax", f"{claim['lstm_hoax_proba']:.2f}")
                    with col_b:
                        st.metric("LLM Verdict", claim['llm_verdict'])
                        st.metric("LLM Confidence", f"{claim['llm_confidence']:.2f}")

                    st.markdown(f"**Mode:** `{claim['mode']}`")
                    st.markdown(f"**Evidence Sources:** {', '.join(claim['evidence_sources']) or 'Tidak ada'}")
                    st.markdown(f"**Reasoning:** {claim['reasoning']}")

            # Claim stats
            if result.get("claim_stats"):
                stats = result["claim_stats"]
                st.markdown("### Statistik")
                st.json(stats)

# Examples
with st.expander("📝 Contoh Teks untuk Dicoba"):
    st.markdown("""
    **Contoh 1 — Hoax:**
    ```
    VIRAL!!! Matcha menyebabkan gagal ginjal dan sudah banyak korban meninggal!!
    Sebarkan sebelum dihapus!! Obat ini disembunyikan oleh pemerintah!!
    ```

    **Contoh 2 — Valid:**
    ```
    BMKG mencatat gempa magnitudo 5.2 di Maluku pada tanggal 15 Januari 2025.
    Gempa tidak berpotensi tsunami. Warga dihimbau tetap tenang.
    ```

    **Contoh 3 — Uncertain:**
    ```
    Kabar beredar bahwa harga BBM akan naik bulan depan.
    Pemerintah belum memberikan konfirmasi resmi mengenai hal ini.
    ```
    """)

# Footer
st.divider()
st.caption("FAKTA v2.0 — Hybrid LSTM + LLM + Evidence Fact-Checking System")
