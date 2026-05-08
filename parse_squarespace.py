#!/usr/bin/env python3
"""
parse_squarespace.py — Parse a Squarespace WordPress XML export and merge
all blog posts and pages into portfolio.json.

Each post becomes a tagged entry. Categories from your site map directly
to portfolio tags. Full post text is used for tag inference.

Usage:
    python parse_squarespace.py Squarespace-Wordpress-Export.xml
    python parse_squarespace.py Squarespace-Wordpress-Export.xml --dry-run
    python parse_squarespace.py Squarespace-Wordpress-Export.xml --since 2020
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: beautifulsoup4 not installed. Run: pip install beautifulsoup4")
    sys.exit(1)

import xml.etree.ElementTree as ET

PORTFOLIO_PATH = os.path.join(os.path.dirname(__file__), "portfolio.json")

# ── Namespace map ─────────────────────────────────────────────────────────────
NS = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc":      "http://purl.org/dc/elements/1.1/",
    "wp":      "http://wordpress.org/export/1.2/",
    "excerpt": "http://wordpress.org/export/1.2/excerpt/",
}

# ── Category → tag mapping ────────────────────────────────────────────────────
# Maps your Squarespace blog categories to portfolio tags
CATEGORY_TAG_MAP: dict[str, list[str]] = {
    "Esports":              ["esports", "gaming", "digital-sport"],
    "Gaming":               ["esports", "gaming", "gametech"],
    "Digital Sport":        ["digital-sport", "esports", "olympic-studies"],
    "Olympic Games":        ["olympic-studies", "olympics", "mega-events"],
    "Olympics":             ["olympic-studies", "olympics"],
    "Sport":                ["digital-sport", "olympic-studies"],
    "Health":               ["digital-health", "health-wellbeing"],
    "Digital Health":       ["digital-health", "health-wellbeing"],
    "Wellbeing":            ["health-wellbeing", "digital-health"],
    "Bioethics":            ["bioethics", "enhancement"],
    "Enhancement":          ["enhancement", "bioethics", "gene-doping"],
    "Gene Doping":          ["gene-doping", "bioethics"],
    "Posthumanism":         ["bioethics", "enhancement", "emerging-tech"],
    "Transhumanism":        ["bioethics", "enhancement"],
    "AI":                   ["ai-ethics", "ai", "emerging-tech"],
    "Artificial Intelligence": ["ai-ethics", "ai", "emerging-tech"],
    "Ethics":               ["ai-ethics", "bioethics", "ethics"],
    "Science Communication":["science-communication", "scicomm", "public-engagement"],
    "SciComm":              ["science-communication", "scicomm"],
    "Public Engagement":    ["public-engagement", "science-communication"],
    "Media":                ["media", "broadcast", "science-communication"],
    "Creative Industries":  ["creative-industries", "createch"],
    "CreaTech":             ["createch", "creative-industries"],
    "Manchester":           ["manchester", "civic", "creative-manchester"],
    "Civic":                ["civic", "manchester", "platform-leadership"],
    "Metaverse":            ["metaverse", "esports", "gametech"],
    "Virtual Reality":      ["metaverse", "createch", "gametech"],
    "Drones":               ["science-communication", "arts-science", "emerging-tech"],
    "Digital":              ["ai-ethics", "emerging-tech", "science-communication"],
    "Innovation":           ["innovation", "createch", "platform-leadership"],
    "Leadership":           ["platform-leadership", "leadership"],
    "Research":             ["science-communication", "platform-leadership"],
    "Climate":              ["civic", "science-communication"],
    "Art":                  ["arts-science", "creative-industries"],
    "Culture":              ["arts-science", "creative-industries", "olympic-studies"],
    "Film":                 ["arts-science", "creative-industries"],
    "Music":                ["arts-science", "creative-industries"],
    "Speaking":             ["science-communication", "public-engagement"],
    "Doping":               ["gene-doping", "bioethics", "olympic-studies"],
    "Photography":          ["arts-science", "science-communication"],
    "Art and Design":       ["arts-science", "creative-industries"],
    "Journalism":           ["journalism", "media", "science-communication"],
    "Media Appearances":    ["media", "broadcast", "science-communication"],
    "Publications":         ["science-communication", "bioethics"],
    "Philosophy":           ["bioethics", "enhancement"],
    "digital culture":      ["ai-ethics", "emerging-tech", "science-communication"],
    "Human Enhancement":    ["enhancement", "bioethics", "gene-doping"],
    "BioArt":              ["bioethics", "arts-science", "enhancement"],
    "Personal - null":      [],
    "Uncategorized":        [],
}

# ── Keyword-based tag inference (fallback) ────────────────────────────────────
TAG_RULES: list[tuple[list[str], list[str]]] = [
    (["esport", "esports", "gaming", "gametech", "fortnite",
      "competitive gaming", "british esports", "global esports"],
     ["esports", "gaming", "digital-sport"]),
    (["olympic", "paralympic", "ioc", "olympism", "sport accord"],
     ["olympic-studies", "olympics"]),
    (["health", "nhs", "wellbeing", "wearable", "digital health",
      "patient", "clinical", "medicalization", "mhealth"],
     ["digital-health", "health-wellbeing"]),
    (["bioethic", "enhancement", "gene doping", "genetic", "posthuman",
      "transhuman", "doping", "cyborg", "biotechnology", "neuralink"],
     ["bioethics", "enhancement", "gene-doping"]),
    (["artificial intelligence", " ai ", "machine learning", "algorithm",
      "robot", "autonomous", "chatgpt", "generative ai", "llm"],
     ["ai-ethics", "ai", "emerging-tech"]),
    (["metaverse", "virtual reality", "vr ", "xr ", "augmented reality",
      "immersive", "phygital", "web3", "mixed reality"],
     ["metaverse", "esports", "createch"]),
    (["science communication", "scicomm", "public engagement", "famelab",
      "science festival", "cheltenham", "new scientist", "outreach"],
     ["science-communication", "public-engagement"]),
    (["manchester", "salford", "mediacity", "gmca", "greater manchester",
      "factory international", "contact theatre"],
     ["manchester", "civic", "creative-manchester"]),
    (["creative industries", "createch", "innovate uk", "accelerator",
      "startup", "entrepreneur", "knowledge exchange"],
     ["createch", "creative-industries", "innovation"]),
    (["drone", "uav", "quadcopter"],
     ["science-communication", "arts-science"]),
    (["social media", "twitter", "tiktok", "instagram", "digital media"],
     ["science-communication", "media"]),
    (["climate", "cop26", "sustainability", "environment", "ecology"],
     ["civic", "science-communication"]),
    (["olympic", "sport", "athlete", "doping", "wada", "anti-doping"],
     ["digital-sport", "olympic-studies"]),
    (["art", "bioart", "creative", "culture", "exhibition", "installation"],
     ["arts-science", "creative-industries"]),
    (["governance", "policy", "government", "parliament", "eu ", "un ",
      "united nations", "itu", "european commission"],
     ["governance", "platform-leadership"]),
]


def infer_tags_from_text(text: str) -> list[str]:
    text_lower = text.lower()
    matched: set[str] = set()
    for keywords, tags in TAG_RULES:
        if any(kw in text_lower for kw in keywords):
            matched.update(tags)
    return sorted(matched)


def html_to_text(html: str) -> str:
    """Strip HTML tags and return clean text."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return " ".join(soup.get_text(" ").split())


def clean(text: str) -> str:
    return " ".join((text or "").strip().split())


def key_for(item: dict) -> str:
    text = item.get("text") or item.get("citation") or item.get("title") or ""
    return re.sub(r'\s+', ' ', text.lower())[:80]


def merge_section(target: list, new_items: list) -> tuple[int, int]:
    existing = {key_for(i) for i in target}
    added = skipped = 0
    for item in new_items:
        k = key_for(item)
        if k and k not in existing:
            target.append(item)
            existing.add(k)
            added += 1
        else:
            skipped += 1
    return added, skipped


# ── Main parser ───────────────────────────────────────────────────────────────

def parse_xml(xml_path: str, since_year: int = 0) -> dict[str, list]:
    """
    Parse the Squarespace XML export.
    Returns dict of categorised items ready for merging.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    items = root.findall(".//item")

    results: dict[str, list] = {
        "blog_posts": [],   # → keynotes or media highlights
        "pages": [],        # → profile / ignore
    }

    for item in items:
        # Post type
        post_type = item.findtext(f"{{{NS['wp']}}}post_type", "")
        status = item.findtext(f"{{{NS['wp']}}}status", "")
        if status != "publish":
            continue
        if post_type == "attachment":
            continue

        # Core fields
        title = clean(item.findtext("title", ""))
        link = clean(item.findtext("link", ""))
        pub_date = item.findtext(f"{{{NS['wp']}}}post_date", "") or ""
        year = pub_date[:4] if pub_date else ""

        # Filter by year if requested
        if since_year and year and int(year) < since_year:
            continue

        # Full content
        content_html = item.findtext(f"{{{NS['content']}}}encoded", "") or ""
        content_text = html_to_text(content_html)

        # Categories
        categories = [
            clean(c.text)
            for c in item.findall("category")
            if c.text and c.get("domain", "category") == "category"
        ]
        # Also get uncategorised ones
        if not categories:
            categories = [clean(c.text) for c in item.findall("category") if c.text]

        # Build tags from categories first, then infer from text
        tags: set[str] = set()
        for cat in categories:
            mapped = CATEGORY_TAG_MAP.get(cat, [])
            tags.update(mapped)
            if not mapped:
                # Try partial match
                for key, mapped_tags in CATEGORY_TAG_MAP.items():
                    if cat.lower() in key.lower() or key.lower() in cat.lower():
                        tags.update(mapped_tags)

        # Supplement with text inference using title + first 300 chars of content
        inferred = infer_tags_from_text(title + " " + content_text[:300])
        tags.update(inferred)

        # Remove empty/noise tags
        tags.discard("")
        needs_tagging = len(tags) == 0

        entry = {
            "title": title,
            "url": link,
            "date": year,
            "categories": categories,
            "snippet": content_text[:200] + ("..." if len(content_text) > 200 else ""),
            "tags": sorted(tags),
            "needs_tagging": needs_tagging,
            "source": "squarespace_export",
            "added": datetime.today().strftime("%Y-%m-%d"),
        }

        if post_type == "post":
            results["blog_posts"].append(entry)
        elif post_type == "page":
            results["pages"].append(entry)

    return results


def build_portfolio_items(parsed: dict[str, list]) -> dict[str, list]:
    """
    Convert parsed XML entries into portfolio.json-compatible items.

    Blog posts become:
    - keynotes entries if they look like talk/event writeups
    - media highlights if they look like journalism/interviews
    - publications (journalism) if they reference an article
    - general web_content entries otherwise
    """
    keynote_keywords = [
        "keynote", "talk", "lecture", "presentation", "conference",
        "summit", "festival", "panel", "invited", "workshop", "webinar",
        "seminar", "spoke at", "speaking at", "gave a talk"
    ]
    pub_keywords = [
        "published", "paper", "article", "journal", "book", "chapter",
        "co-authored", "new paper", "new article", "forthcoming", "preprint"
    ]
    media_keywords = [
        "interview", "bbc", "guardian", "wired", "conversation",
        "times higher", "newspaper", "magazine", "podcast", "radio",
        "featured in", "quoted in", "media appearance"
    ]

    result: dict[str, list] = {
        "keynotes": [],
        "journalism": [],
        "media_highlights": [],
        "web_content": [],
    }

    for post in parsed["blog_posts"]:
        title_lower = post["title"].lower()
        snippet_lower = post["snippet"].lower()
        combined = title_lower + " " + snippet_lower

        # Classify
        if any(kw in combined for kw in keynote_keywords):
            result["keynotes"].append({
                "text": f"{post['title']} ({post['date']}) — {post['url']}",
                "tags": post["tags"],
                "needs_tagging": post["needs_tagging"],
                "source": "squarespace_export",
                "added": post["added"],
            })
        elif any(kw in combined for kw in pub_keywords):
            result["journalism"].append({
                "citation": f"Miah, A. ({post['date']}) {post['title']}. [Blog] {post['url']}",
                "tags": post["tags"],
                "needs_tagging": post["needs_tagging"],
                "source": "squarespace_export",
                "added": post["added"],
            })
        elif any(kw in combined for kw in media_keywords):
            result["media_highlights"].append({
                "text": f"{post['title']} ({post['date']}) — {post['url']}",
                "tags": post["tags"],
                "needs_tagging": post["needs_tagging"],
                "source": "squarespace_export",
                "added": post["added"],
            })
        else:
            # General content — goes into web_content for reference
            result["web_content"].append({
                "text": f"{post['title']} ({post['date']}) — {post['url']}",
                "snippet": post["snippet"],
                "tags": post["tags"],
                "needs_tagging": post["needs_tagging"],
                "source": "squarespace_export",
                "added": post["added"],
            })

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Parse Squarespace XML export and merge into portfolio.json",
        epilog="Example: python parse_squarespace.py Squarespace-Wordpress-Export.xml --since 2015"
    )
    parser.add_argument("xml_path", help="Path to the Squarespace XML export file")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Show what would be added without writing")
    parser.add_argument("--since", type=int, default=0,
                        help="Only import posts from this year onwards (e.g. --since 2018)")
    parser.add_argument("--stats", action="store_true",
                        help="Show category and year statistics only")
    args = parser.parse_args()

    if not os.path.exists(args.xml_path):
        print(f"ERROR: File not found: {args.xml_path}")
        sys.exit(1)

    print(f"\nParsing: {args.xml_path}")
    if args.since:
        print(f"Filtering: posts from {args.since} onwards only")

    parsed = parse_xml(args.xml_path, since_year=args.since)

    print(f"\nFound:")
    print(f"  Blog posts: {len(parsed['blog_posts'])}")
    print(f"  Pages:      {len(parsed['pages'])}")

    if args.stats:
        from collections import Counter
        cat_counts = Counter()
        year_counts = Counter()
        for p in parsed["blog_posts"]:
            for c in p["categories"]:
                cat_counts[c] += 1
            year_counts[p["date"]] += 1
        print("\nTop categories:")
        for cat, count in cat_counts.most_common(20):
            print(f"  {cat}: {count}")
        print("\nPosts by year:")
        for year in sorted(year_counts.keys()):
            print(f"  {year}: {year_counts[year]}")
        return

    # Convert to portfolio items
    portfolio_items = build_portfolio_items(parsed)

    print(f"\nClassified as:")
    for section, items in portfolio_items.items():
        print(f"  {section}: {len(items)}")

    if args.dry_run:
        print("\n[Dry run — no changes written]")
        print("\nSample keynote entries:")
        for k in portfolio_items["keynotes"][:5]:
            print(f"  [{', '.join(k['tags'][:3])}] {k['text'][:80]}")
        print("\nSample web content:")
        for k in portfolio_items["web_content"][:5]:
            print(f"  [{', '.join(k['tags'][:3])}] {k['text'][:80]}")
        return

    # Load portfolio
    if not os.path.exists(PORTFOLIO_PATH):
        print(f"ERROR: portfolio.json not found at {PORTFOLIO_PATH}")
        sys.exit(1)

    with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
        portfolio = json.load(f)

    # Ensure web_content section exists
    if "web_content" not in portfolio:
        portfolio["web_content"] = []

    # Merge
    total_added = 0
    counts = {}

    a, s = merge_section(portfolio["keynotes"], portfolio_items["keynotes"])
    counts["keynotes"] = (a, s)
    total_added += a

    a, s = merge_section(portfolio["publications"]["journalism"],
                         portfolio_items["journalism"])
    counts["journalism"] = (a, s)
    total_added += a

    a, s = merge_section(portfolio["media"]["highlights"],
                         portfolio_items["media_highlights"])
    counts["media_highlights"] = (a, s)
    total_added += a

    a, s = merge_section(portfolio["web_content"],
                         portfolio_items["web_content"])
    counts["web_content"] = (a, s)
    total_added += a

    # Save
    with open(PORTFOLIO_PATH, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=2, ensure_ascii=False)

    print("\nMerge complete:")
    for section, (a, s) in counts.items():
        print(f"  {section}: +{a} added, {s} skipped")
    print(f"\nTotal new items: {total_added}")

    # Count untagged
    untagged = sum(
        1 for section in [portfolio["keynotes"],
                          portfolio["publications"]["journalism"],
                          portfolio["media"]["highlights"],
                          portfolio["web_content"]]
        for item in section
        if item.get("needs_tagging")
    )
    if untagged:
        print(f"\n⚠  {untagged} items need tagging")
        print("   Run: python add_item.py --untagged")
    print()


if __name__ == "__main__":
    main()
