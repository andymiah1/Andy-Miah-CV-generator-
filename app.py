"""
app.py — Andy Miah CV Generator
Clean UI: dropdown only, visual design with custom CSS
"""

import copy
import json
import os
import re
import tempfile

import streamlit as st

from generator.builder import build_cv, build_teaching_cv

st.set_page_config(
    page_title="Andy Miah — CV Generator",
    page_icon="📄",
    layout="centered",
)

# ── Custom CSS & visual design ────────────────────────────────────────────────
st.markdown("""
<style>
/* Import Google Font */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

/* Full-page gradient background */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0d1b2a 0%, #1a2e44 40%, #0d3348 70%, #0a1628 100%);
    font-family: 'Inter', sans-serif;
}

/* Hide default header */
[data-testid="stHeader"] {
    background: transparent;
}

/* Main content card */
[data-testid="stMainBlockContainer"] {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 2rem 2.5rem;
    backdrop-filter: blur(12px);
    margin-top: 2rem;
    margin-bottom: 2rem;
}

/* Hero title */
.hero-title {
    font-size: 2.8rem;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.02em;
    line-height: 1.1;
    margin-bottom: 0.3rem;
}

.hero-subtitle {
    font-size: 1rem;
    color: rgba(255,255,255,0.55);
    font-weight: 300;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.2rem;
}

.hero-institution {
    font-size: 1rem;
    color: #4dd0e1;
    font-weight: 400;
    margin-bottom: 2rem;
}

/* Divider */
.hero-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(77,208,225,0.4), transparent);
    margin: 1.5rem 0;
}

/* Label */
.select-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: rgba(255,255,255,0.5);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 0.5rem;
}

/* Selectbox styling */
[data-testid="stSelectbox"] > div > div {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 10px !important;
    color: white !important;
}

[data-testid="stSelectbox"] label {
    color: rgba(255,255,255,0.6) !important;
    font-size: 0.8rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
}

/* Generate button */
[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #006d77, #00a896) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.75rem 2.5rem !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.03em !important;
    width: 100% !important;
    margin-top: 1rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 20px rgba(0,168,150,0.3) !important;
}

[data-testid="stButton"] > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 24px rgba(0,168,150,0.45) !important;
}

/* Download button */
[data-testid="stDownloadButton"] > button {
    background: linear-gradient(135deg, #1a6b3c, #22a45d) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.75rem 2rem !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    width: 100% !important;
    margin-top: 0.5rem !important;
    box-shadow: 0 4px 20px rgba(34,164,93,0.3) !important;
}

/* Success message */
[data-testid="stAlert"] {
    background: rgba(34,164,93,0.15) !important;
    border: 1px solid rgba(34,164,93,0.3) !important;
    border-radius: 10px !important;
    color: #a8f0c6 !important;
}

/* Info box */
.info-box {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-top: 1rem;
    color: rgba(255,255,255,0.6);
    font-size: 0.85rem;
    line-height: 1.5;
}

/* Tag chips */
.tag-chip {
    display: inline-block;
    background: rgba(77,208,225,0.15);
    border: 1px solid rgba(77,208,225,0.3);
    color: #4dd0e1;
    border-radius: 20px;
    padding: 0.15rem 0.6rem;
    font-size: 0.7rem;
    margin: 0.15rem;
    font-weight: 500;
}

/* Footer */
.footer {
    text-align: center;
    color: rgba(255,255,255,0.25);
    font-size: 0.75rem;
    margin-top: 2rem;
    padding-top: 1rem;
    border-top: 1px solid rgba(255,255,255,0.06);
}

/* Spinner */
[data-testid="stSpinner"] {
    color: #4dd0e1 !important;
}

/* Floating particles (decorative) */
.particle {
    position: fixed;
    border-radius: 50%;
    opacity: 0.06;
    pointer-events: none;
}
</style>

<!-- Video background -->
<video id="bg-video" autoplay muted loop playsinline
  style="position:fixed;top:0;left:0;width:100%;height:100%;
         object-fit:cover;z-index:-1;opacity:0.18;pointer-events:none;">
  <source src="https://raw.githubusercontent.com/andymiah1/Andy-Miah-CV-generator-/main/2024.03.15-MetaHumanCompressed.mp4" type="video/mp4">
</video>

<!-- Decorative background shapes -->
<div style="position:fixed;top:-80px;right:-80px;width:400px;height:400px;
    border-radius:50%;background:radial-gradient(circle, rgba(77,208,225,0.15), transparent 70%);
    pointer-events:none;z-index:0;"></div>
<div style="position:fixed;bottom:-100px;left:-100px;width:500px;height:500px;
    border-radius:50%;background:radial-gradient(circle, rgba(0,109,119,0.12), transparent 70%);
    pointer-events:none;z-index:0;"></div>
<div style="position:fixed;top:40%;left:-60px;width:250px;height:250px;
    border-radius:50%;background:radial-gradient(circle, rgba(100,150,255,0.08), transparent 70%);
    pointer-events:none;z-index:0;"></div>
""", unsafe_allow_html=True)

# ── Data ──────────────────────────────────────────────────────────────────────
EXPERTISE_AREAS = {
    "":                       "— Select an expertise area —",
    "drones":                 "Drones",
    "esports":                "Esports & Gaming",
    "olympic-games":          "Olympic Games",
    "bioethics-enhancement":  "Bioethics & Human Enhancement",
    "ai-ethics":              "AI Ethics",
    "science-communication":  "Science Communication",
    "digital-health":         "Digital Health",
    "metaverse":              "Metaverse & Virtual Reality",
    "bioart":                 "BioArt",
    "future-sport":           "Future Sport",
    "creative-industries":    "Creative Industries",
    "teaching-cv":            "📋 Teaching CV",
}


@st.cache_data
def load_portfolio() -> dict:
    path = os.path.join(os.path.dirname(__file__), "portfolio.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def tags_from_focus(focus: str, portfolio: dict) -> list[str]:
    focus_areas = portfolio["focus_areas"]
    if focus in focus_areas:
        return focus_areas[focus]
    return sorted(set(t for ts in focus_areas.values() for t in ts))


# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown('''
<div class="hero-subtitle">Curriculum Vitae Generator</div>
<div class="hero-title">Professor Andy Miah</div>
<div class="hero-institution">Chair in Science Communication & Future Media · University of Salford</div>
<div class="hero-divider"></div>
''', unsafe_allow_html=True)

st.markdown('''
<p style="color:rgba(255,255,255,0.8);font-size:1rem;line-height:1.75;margin-bottom:0.75rem;font-style:italic;">
“People often ask me ‘what do you do?’ and I tell them ‘It’s complicated’. I have always worked across disciplines and so my portfolio is incredibly diverse. So, based on what you want to discover about me, take your pick.”
</p>
<p style="color:rgba(255,255,255,0.35);font-size:0.8rem;margin-bottom:1.5rem;">
Select an expertise area below to generate a tailored PDF CV.
</p>
''', unsafe_allow_html=True)

# ── Portfolio ─────────────────────────────────────────────────────────────────
portfolio = load_portfolio()

# ── Selector ──────────────────────────────────────────────────────────────────
selected = st.selectbox(
    "Expertise area",
    options=list(EXPERTISE_AREAS.keys()),
    format_func=lambda k: EXPERTISE_AREAS[k],
    index=0,
)

# Show matched tags as chips when something is selected
if selected:
    active_tags = tags_from_focus(selected, portfolio)
    chips_html = " ".join(
        f'<span class="tag-chip">{t}</span>'
        for t in active_tags[:12]
    )
    st.markdown(
        f'<div style="margin:0.75rem 0 0.25rem;">{chips_html}</div>',
        unsafe_allow_html=True
    )

# ── Generate ──────────────────────────────────────────────────────────────────
generate = st.button("📄 Generate CV", type="primary", disabled=not selected)

if generate and selected:
    with st.spinner("Building your CV..."):
        try:
            active_tags = tags_from_focus(selected, portfolio)
            enriched = copy.deepcopy(portfolio)

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp_path = tmp.name

            if selected == "teaching-cv":
                build_teaching_cv(portfolio=enriched, output_path=tmp_path)
            else:
                build_cv(
                    portfolio=enriched,
                    active_tags=active_tags,
                    focus_label=selected,
                    output_path=tmp_path,
                )

            with open(tmp_path, "rb") as f:
                pdf_bytes = f.read()
            os.unlink(tmp_path)

            safe = re.sub(r"[^a-z0-9]+", "_", selected.lower()).strip("_")
            filename = f"AndyMiah_CV_{safe}.pdf"

            st.success("CV ready.")
            st.download_button(
                label="⬇️  Download PDF",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                type="primary",
            )

        except Exception as e:
            st.error(f"Something went wrong: {e}")
            st.markdown("Please try again or contact Andy at [andymiah.net](https://andymiah.net)")

elif not selected:
    st.markdown('''
    <div class="info-box">
    Choose an expertise area from the dropdown above. Each option generates
    a different CV, foregrounding the publications, keynotes, grants, and
    profile most relevant to that area.
    </div>
    ''', unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown('''
<div class="footer">
    andymiah.net &nbsp;·&nbsp; University of Salford &nbsp;·&nbsp;
    Built with <a href="https://streamlit.io" style="color:rgba(255,255,255,0.35);">Streamlit</a>
</div>
''', unsafe_allow_html=True)
