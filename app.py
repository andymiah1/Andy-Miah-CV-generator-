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
    "ai-ethics":             "AI Ethics & Emerging Techn
