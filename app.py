"""
app.py — Streamlit web app for generating tailored PDF CVs.

- Free text query
- Live DuckDuckGo search of andymiah.net for relevant blog/page content
- Smart full-text search through portfolio.json as fallback
- Falls back gracefully at every step
"""

import copy
import json
import os
import re
import tempfile
import time

import requests
import streamlit as st
from bs4 import BeautifulSoup

from generator.scorer import resolve_tags
from generator.builder import build_cv

st.set_page_config(
    page_title="Andy Miah — CV Generator",
    page_icon="📄",
    layout="centered",
)

SITE = "andymiah.net"
DDG_URL = "https://html.duckduckgo.com/html/"
DDG_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-GB,en;q=0.9",
    "Referer": "https://duckduckgo.com/",
}


@st.cache_data
def load_portfolio() -> dict:
    path = os.path.join(os.path.dirname(__file__), "portfolio.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=1800)
def search_website(query: str, max_results: int = 8) -> list[dict]:
    """Search andymiah.net via DuckDuckGo HTML. Falls back to [] on failure."""
    try:
        time.sleep(0.5)
        r = requests.post(
            DDG_URL,
            data={"q": f"site:{SITE} {query}"},
            headers=DDG_HEADERS,
            timeout=12,
            allow_redirects=True,
        )
        if r.status_code != 200:
            return []

        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for result in soup.find_all("div", class_="result__body"):
            title_tag   = result.find("a", class_="result__a")
            snippet_tag = result.find("a", class_="result__snippet")
            url_tag     = result.find("a", class_="result__url")
            title   = title_tag.get_text(strip=True)   if title_tag   else ""
            snippet = snippet_tag.get_text(strip=True)  if snippet_tag else ""
            url     = url_tag.get_text(strip=True)      if url_tag     else ""
            if title and SITE in url:
                results.append({"title": title, "url": url, "snippet": snippet})
            if len(results) >= max_results:
                break
        return results
    except Exception:
        return []


def search_portfolio_text(portfolio: dict, query: str) -> list[str]:
    """Full-text search across all portfolio.json string values."""
    words = set(re.findall(r"[a-z]{4,}", query.lower()))
    if not words:
        return []
    matches = []
    seen: set[str] = set()

    def recurse(obj) -> None:
        if isinstance(obj, str) and len(obj) > 10:
            score = sum(1 for w in words if w in obj.lower())
            if score > 0:
                key = obj[:60].lower()
                if key not in seen:
                    seen.add(key)
                    snippet = obj[:120] + ("..." if len(obj) > 120 else "")
                    matches.append((score, snippet))
        elif isinstance(obj, list):
            for item in obj:
                recurse(item)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                if k not in ("tags", "needs_tagging", "added", "fetched", "source", "_kind"):
                    recurse(v)

    recurse(portfolio)
    matches.sort(key=lambda x: x[0], reverse=True)
    return [text for _, text in matches[:8]]


def tags_from_query(query: str, portfolio: dict) -> list[str]:
    """Convert free-text query into matching portfolio tags."""
    focus_areas = portfolio["focus_areas"]
    all_tags: set[str] = set()
    for tags in focus_areas.values():
        all_tags.update(tags)

    words = re.findall(r"[a-z0-9]+", query.lower())
    matched: set[str] = set()

    synonyms = {
        "game":     ["esports", "gaming", "gametech"],
        "games":    ["esports", "gaming", "gametech"],
        "sport":    ["esports", "digital-sport", "olympic-studies"],
        "olympic":  ["olympic-studies", "olympics", "mega-events"],
        "health":   ["digital-health", "health-wellbeing"],
        "ai":       ["ai-ethics", "ai", "emerging-tech"],
        "ethics":   ["ai-ethics", "bioethics", "ethics"],
        "creative": ["creative-industries", "createch", "arts-science"],
        "tech":     ["createch", "gametech", "emerging-tech", "ai-ethics"],
        "science":  ["science-communication", "scicomm"],
        "media":    ["science-communication", "media", "broadcast"],
        "civic":    ["civic", "manchester", "platform-leadership"],
        "platform": ["platform-leadership", "interdisciplinary"],
        "bio":      ["bioethics", "enhancement"],
        "gene":     ["gene-doping", "bioethics", "enhancement"],
        "digital":  ["digital-health", "digital-sport", "digital-futures"],
        "public":   ["science-communication", "public-engagement"],
        "engage":   ["public-engagement", "science-communication"],
        "metaverse":["metaverse", "esports", "gametech"],
        "innovat":  ["createch", "platform-leadership", "innovation"],
        "wellbeing":["health-wellbeing", "digital-health"],
        "manches":  ["manchester", "civic", "creative-industries"],
        "govern":   ["governance", "platform-leadership", "olympic-studies"],
        "policy":   ["governance", "science-communication", "ai-ethics"],
        "leader":   ["platform-leadership", "leadership", "interdisciplinary"],
        "inter":    ["interdisciplinary", "platform-leadership"],
        "robot":    ["ai-ethics", "emerging-tech"],
        "drone":    ["science-communication", "arts-science"],
        "nano":     ["bioethics", "ai-ethics", "science-communication"],
        "posthum":  ["bioethics", "enhancement"],
        "enhance":  ["enhancement", "bioethics", "gene-doping"],
        "wearable": ["wearables", "digital-health", "mhealth"],
        "festiv":   ["science-communication", "festival", "arts-science"],
        "olymp":    ["olympic-studies", "olympics", "esports"],
        "broad":    ["broadcast", "media", "science-communication"],
        "journal":  ["journalism", "media", "science-communication"],
        "sustain":  ["civic", "platform-leadership"],
        "cancer":   ["digital-health", "health-wellbeing"],
    }

    for word in words:
        for tag in all_tags:
            if word in tag.replace("-", " ").split() or word == tag.replace("-", ""):
                matched.add(tag)
        for key, tags in focus_areas.items():
            if word in key.replace("-", " ").split():
                matched.update(tags)
        for stem, tags in synonyms.items():
            if word.startswith(stem[:5]):
                matched.update(tags)

    if not matched:
        for tags in focus_areas.values():
            matched.update(tags)

    return sorted(matched)


# ── UI ────────────────────────────────────────────────────────────────────────

st.markdown("## Professor Andy Miah — CV Generator")
st.markdown(
    "Enter a role, topic, or interest area and click **Generate CV** to download "
    "a tailored PDF drawing from Andy's full portfolio — including relevant content "
    "from his website."
)
st.divider()

portfolio = load_portfolio()

query = st.text_input(
    "What is the CV for?",
    placeholder="e.g.  esports governance,  AI ethics,  creative industries leadership,  science communication...",
    help="Type any keywords — role type, subject area, sector, or specific topic",
)

if query.strip():
    active_tags = tags_from_query(query, portfolio)

    col_a, col_b = st.columns(2)

    with col_a:
        with st.expander(f"Portfolio areas matched ({len(active_tags)} tags)"):
            st.markdown("  ".join([f"`{t}`" for t in sorted(active_tags)]))

    web_results: list[dict] = []
    portfolio_matches: list[str] = []

    with col_b:
        with st.expander("Content from andymiah.net"):
            with st.spinner("Searching website..."):
                web_results = search_website(query)
            if web_results:
                for item in web_results:
                    st.markdown(f"**{item['title']}**")
                    if item["snippet"]:
                        st.caption(item["snippet"])
                    if item["url"]:
                        st.caption(f"[{item['url']}](https://{item['url']})")
                    st.divider()
            else:
                portfolio_matches = search_portfolio_text(portfolio, query)
                if portfolio_matches:
                    st.caption("Showing portfolio text matches:")
                    for m in portfolio_matches[:5]:
                        st.markdown(f"- {m}")
                else:
                    st.caption("No additional content found for this query.")

    st.divider()

    generate = st.button("📄 Generate CV", type="primary")

    if generate:
        with st.spinner("Building your tailored CV..."):
            try:
                enriched = copy.deepcopy(portfolio)

                # Inject relevant web results as media entries
                if web_results:
                    existing = {
                        k.get("text", "").lower()[:60]
                        for k in enriched.get("media", {}).get("highlights", [])
                    }
                    for item in web_results:
                        key = item["title"].lower()[:60]
                        if key not in existing:
                            enriched["media"]["highlights"].append({
                                "text": f"{item['title']} — {item['url']}",
                                "tags": active_tags[:3],
                                "needs_tagging": False,
                            })
                            existing.add(key)

                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp_path = tmp.name

                build_cv(
                    portfolio=enriched,
                    active_tags=active_tags,
                    focus_label=query,
                    output_path=tmp_path,
                )

                with open(tmp_path, "rb") as f:
                    pdf_bytes = f.read()
                os.unlink(tmp_path)

                safe_name = re.sub(r"[^a-z0-9]+", "_", query.lower()).strip("_")
                filename = f"AndyMiah_CV_{safe_name}.pdf"

                st.success("CV generated successfully.")
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

else:
    st.info("Enter a focus area above to get started.")

st.divider()
st.markdown(
    "<small>andymiah.net · University of Salford · "
    "Built with [Streamlit](https://streamlit.io)</small>",
    unsafe_allow_html=True,
)
