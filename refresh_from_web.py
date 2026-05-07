#!/usr/bin/env python3
"""
refresh_from_web.py — Fetches andymiah.net and merges new items into portfolio.json.

Fetches:
  - /upcoming        → new keynotes (upcoming and recent)
  - /published/articles  → new journal articles and book chapters
  - /published/books     → new books
  - /published/book-chapters → new chapters
  - /blog            → recent blog posts (as media/event entries)

New items are added to portfolio.json with "needs_tagging": true so you
can review and tag them before generating a CV.

Usage:
    python refresh_from_web.py              # fetch all sources
    python refresh_from_web.py --dry-run    # show what would be added without writing
    python refresh_from_web.py --source upcoming
    python refresh_from_web.py --source publications
    python refresh_from_web.py --source blog
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from typing import Any

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: Missing dependencies. Run:  pip install requests beautifulsoup4")
    sys.exit(1)

PORTFOLIO_PATH = os.path.join(os.path.dirname(__file__), "portfolio.json")
BASE_URL = "https://andymiah.net"

SOURCES = {
    "upcoming":     f"{BASE_URL}/upcoming",
    "articles":     f"{BASE_URL}/published/articles",
    "books":        f"{BASE_URL}/published/books",
    "chapters":     f"{BASE_URL}/published/book-chapters",
    "journalism":   f"{BASE_URL}/published/focus/journalism",
    "blog":         f"{BASE_URL}/blog",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; cv-generator/1.0; +https://andymiah.net)"
    )
}


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def fetch(url: str) -> BeautifulSoup | None:
    """Fetch a URL and return a BeautifulSoup object, or None on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as e:
        print(f"  ⚠  Could not fetch {url}: {e}")
        return None


# ── Extraction helpers ────────────────────────────────────────────────────────

def clean(text: str) -> str:
    """Strip whitespace and normalise unicode quotes."""
    return " ".join(text.split()).replace("\u2019", "'").replace("\u2018", "'")


def existing_texts(items: list[dict]) -> set[str]:
    """Return a set of lowercased text/citation strings for dedup checking."""
    texts = set()
    for item in items:
        for key in ("text", "citation", "title"):
            if key in item:
                texts.add(item[key].lower()[:80])
    return texts


def make_stub(text: str, source_url: str, kind: str) -> dict:
    """Create a new untagged portfolio item stub."""
    return {
        "text": text,
        "tags": [],
        "needs_tagging": True,
        "source": source_url,
        "fetched": datetime.today().strftime("%Y-%m-%d"),
        "_kind": kind,
    }


def make_pub_stub(citation: str, source_url: str, kind: str) -> dict:
    return {
        "citation": citation,
        "tags": [],
        "needs_tagging": True,
        "source": source_url,
        "fetched": datetime.today().strftime("%Y-%m-%d"),
        "_kind": kind,
    }


# ── Page-specific parsers ─────────────────────────────────────────────────────

def parse_upcoming(soup: BeautifulSoup) -> list[dict]:
    """
    Extract upcoming talks from /upcoming.
    They appear as h4 elements like:
      **2026.07.06 [LONDON]** AI Leadership in the Workplace, Science Council.
    """
    items = []
    for h4 in soup.find_all("h4"):
        text = clean(h4.get_text())
        if not text:
            continue
        # Must look like a dated talk entry
        if re.match(r"20\d\d\.\d\d\.\d\d", text):
            items.append(make_stub(text, SOURCES["upcoming"], "keynote"))
    return items


def parse_blog(soup: BeautifulSoup) -> list[dict]:
    """
    Extract recent blog post titles from /blog.
    These are typically links inside article/h2 elements.
    """
    items = []
    seen = set()
    for tag in soup.find_all(["h2", "h3", "h1"]):
        a = tag.find("a")
        if not a:
            continue
        title = clean(a.get_text())
        href = a.get("href", "")
        if not title or title.lower() in seen or len(title) < 5:
            continue
        if "andymiah.net/blog" in href or "/blog/" in href:
            seen.add(title.lower())
            items.append({
                "text": title,
                "url": href,
                "tags": [],
                "needs_tagging": True,
                "source": SOURCES["blog"],
                "fetched": datetime.today().strftime("%Y-%m-%d"),
                "_kind": "blog_post",
            })
    return items[:20]  # cap at 20 most recent


def parse_publications(soup: BeautifulSoup, source_url: str, kind: str) -> list[dict]:
    """
    Extract publication citations from /published/* pages.
    Squarespace renders these as paragraphs, sometimes under year headings.
    We look for paragraphs that start with 'Miah' or contain a year pattern.
    """
    items = []
    # Collect all paragraph and list-item text
    for tag in soup.find_all(["p", "li"]):
        text = clean(tag.get_text())
        if len(text) < 30:
            continue
        # Must look like a citation — starts with Miah or contains a 4-digit year
        if text.startswith("Miah") or re.search(r"\(\d{4}\)", text):
            items.append(make_pub_stub(text, source_url, kind))
    return items


# ── Dedup and merge ───────────────────────────────────────────────────────────

def merge_into(portfolio: dict, new_items: list[dict], section: str,
               subsection: str | None = None) -> tuple[int, int]:
    """
    Merge new_items into portfolio[section] (or portfolio[section][subsection]).
    Returns (added, skipped).
    """
    if subsection:
        target: list = portfolio[section][subsection]
    else:
        target: list = portfolio[section]

    existing = existing_texts(target)
    added = skipped = 0

    for item in new_items:
        key = item.get("text", item.get("citation", "")).lower()[:80]
        if key and key in existing:
            skipped += 1
            continue
        target.append(item)
        existing.add(key)
        added += 1

    return added, skipped


# ── Main ──────────────────────────────────────────────────────────────────────

def load_portfolio() -> dict:
    with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_portfolio(portfolio: dict) -> None:
    with open(PORTFOLIO_PATH, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=2, ensure_ascii=False)


def print_new_items(items: list[dict], label: str) -> None:
    if not items:
        return
    print(f"\n  {label}:")
    for item in items:
        text = item.get("text") or item.get("citation", "")
        print(f"    + {text[:100]}")


def run_refresh(sources: list[str], dry_run: bool) -> None:
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Refreshing portfolio from andymiah.net...\n")
    portfolio = load_portfolio()
    total_added = 0

    # ── Upcoming talks ────────────────────────────────────────────────────────
    if "upcoming" in sources or "all" in sources:
        print("→ Fetching /upcoming...")
        soup = fetch(SOURCES["upcoming"])
        if soup:
            new_items = parse_upcoming(soup)
            print_new_items(new_items, "Upcoming talks found")
            if not dry_run:
                added, skipped = merge_into(portfolio, new_items, "keynotes")
                print(f"   Added: {added}  Skipped (already exists): {skipped}")
                total_added += added
        time.sleep(1)

    # ── Publications: articles ────────────────────────────────────────────────
    if "publications" in sources or "all" in sources:
        print("→ Fetching /published/articles...")
        soup = fetch(SOURCES["articles"])
        if soup:
            new_items = parse_publications(soup, SOURCES["articles"], "journal_article")
            print_new_items(new_items, "Articles found")
            if not dry_run:
                added, skipped = merge_into(portfolio, new_items,
                                            "publications", "journal_articles")
                print(f"   Added: {added}  Skipped: {skipped}")
                total_added += added
        time.sleep(1)

        print("→ Fetching /published/book-chapters...")
        soup = fetch(SOURCES["chapters"])
        if soup:
            new_items = parse_publications(soup, SOURCES["chapters"], "chapter")
            print_new_items(new_items, "Chapters found")
            if not dry_run:
                added, skipped = merge_into(portfolio, new_items,
                                            "publications", "chapters")
                print(f"   Added: {added}  Skipped: {skipped}")
                total_added += added
        time.sleep(1)

        print("→ Fetching /published/books...")
        soup = fetch(SOURCES["books"])
        if soup:
            new_items = parse_publications(soup, SOURCES["books"], "book")
            print_new_items(new_items, "Books found")
            if not dry_run:
                added, skipped = merge_into(portfolio, new_items,
                                            "publications", "books")
                print(f"   Added: {added}  Skipped: {skipped}")
                total_added += added
        time.sleep(1)

        print("→ Fetching /published/focus/journalism...")
        soup = fetch(SOURCES["journalism"])
        if soup:
            new_items = parse_publications(soup, SOURCES["journalism"], "journalism")
            print_new_items(new_items, "Journalism found")
            if not dry_run:
                added, skipped = merge_into(portfolio, new_items,
                                            "publications", "journalism")
                print(f"   Added: {added}  Skipped: {skipped}")
                total_added += added
        time.sleep(1)

    # ── Blog ──────────────────────────────────────────────────────────────────
    if "blog" in sources or "all" in sources:
        print("→ Fetching /blog...")
        soup = fetch(SOURCES["blog"])
        if soup:
            new_items = parse_blog(soup)
            print_new_items(new_items, "Blog posts found")
            if not dry_run:
                # Blog posts go into media highlights
                added, skipped = merge_into(portfolio, new_items,
                                            "media", "highlights")
                print(f"   Added: {added}  Skipped: {skipped}")
                total_added += added
        time.sleep(1)

    # ── Save & report ─────────────────────────────────────────────────────────
    if not dry_run:
        save_portfolio(portfolio)
        print(f"\n✓  portfolio.json updated — {total_added} new items added.")

        # Count items needing tags
        needs_tagging = count_needs_tagging(portfolio)
        if needs_tagging > 0:
            print(f"\n⚠  {needs_tagging} item(s) need tagging before they'll appear in CVs.")
            print("   Open portfolio.json, search for \"needs_tagging\": true,")
            print("   add appropriate tags, then remove the needs_tagging flag.\n")
        else:
            print("   All items are tagged. Run generate_cv.py to build a CV.\n")
    else:
        print("\n[DRY run complete — no changes written]\n")


def count_needs_tagging(portfolio: dict) -> int:
    count = 0

    def recurse(obj: Any) -> None:
        nonlocal count
        if isinstance(obj, list):
            for item in obj:
                recurse(item)
        elif isinstance(obj, dict):
            if obj.get("needs_tagging"):
                count += 1
            for v in obj.values():
                recurse(v)

    recurse(portfolio)
    return count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh portfolio.json from andymiah.net",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Sources:
  all           Fetch everything (default)
  upcoming      Upcoming and recent keynote talks
  publications  Articles, book chapters, books, journalism
  blog          Recent blog posts

Examples:
  python refresh_from_web.py
  python refresh_from_web.py --dry-run
  python refresh_from_web.py --source upcoming
  python refresh_from_web.py --source publications --dry-run
        """
    )
    parser.add_argument(
        "--source", "-s",
        choices=["all", "upcoming", "publications", "blog"],
        default="all",
        help="Which source to fetch (default: all)",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be added without modifying portfolio.json",
    )
    args = parser.parse_args()

    if not os.path.exists(PORTFOLIO_PATH):
        print(f"ERROR: portfolio.json not found at {PORTFOLIO_PATH}", file=sys.stderr)
        sys.exit(1)

    run_refresh(sources=[args.source], dry_run=args.dry_run)


if __name__ == "__main__":
    main()
