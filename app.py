"""
app.py — Streamlit web app for generating tailored PDF CVs.
"""

import io
import json
import os
import tempfile

import streamlit as st

from generator.scorer import resolve_tags
from generator.builder import build_cv

st.set_page_config(
    page_title="Andy Miah — CV Generator",
    page_icon="📄",
    layout="centered",
)

@st.cache_data
def load_portfolio() -> dict:
    path = os.path.join(os.path.dirname(__file__), "portfolio.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

portfolio = load_portfolio()
focus_areas = portfolio["focus_areas"]

FOCUS_LABELS = {
    "esports":               "Esports, Gaming & Digital Sport",
    "creative-manchester":   "Creative Industries & Platform Leadership",
    "science-communication": "Science Communication & Public Engagement",
    "ai-ethics":             "AI Ethics & Emerging Technologies",
    "digital-health":        "Digital Health & Wellbeing",
    "olympic-studies":       "Olympic Studies & Sport Governance",
    "bioethics":             "Bioethics & Human Enhancement",
    "platform-leadership":   "Interdisciplinary Platform Leadership",
}

st.markdown("## Professor Andy Miah — CV Generator")
st.markdown(
    "Generate a tailored PDF CV focused on a specific research area or role type. "
    "Select a focus below and click **Generate CV** to download."
)
st.divider()

focus_key = st.selectbox(
    "Select a focus area",
    options=list(FOCUS_LABELS.keys()),
    format_func=lambda k: FOCUS_LABELS[k],
    index=0,
)

active_tags = resolve_tags(focus_key, focus_areas)
with st.expander("What this CV will emphasise"):
    st.markdown(
        "Content tagged with any of the following will be prioritised:\n\n" +
        "  ".join([f"`{t}`" for t in active_tags])
    )

st.divider()

col1, col2 = st.columns([1, 3])
with col1:
    generate = st.button("📄 Generate CV", type="primary", use_container_width=True)

if generate:
    with st.spinner("Building your CV..."):
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp_path = tmp.name

            build_cv(
                portfolio=portfolio,
                active_tags=active_tags,
                focus_label=focus_key,
                output_path=tmp_path,
            )

            with open(tmp_path, "rb") as f:
                pdf_bytes = f.read()

            os.unlink(tmp_path)

            filename = f"AndyMiah_CV_{FOCUS_LABELS[focus_key].replace(' ', '_').replace('&', 'and')}.pdf"

            st.success("CV generated successfully.")
            st.download_button(
                label="⬇️ Download PDF",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                type="primary",
                use_container_width=False,
            )

        except Exception as e:
            st.error(f"Something went wrong: {e}")
            st.markdown("Please try again or contact Andy directly at andymiah.net")

st.divider()
st.markdown(
    "<small>andymiah.net · University of Salford · "
    "Built with [Streamlit](https://streamlit.io)</small>",
    unsafe_allow_html=True,
)
