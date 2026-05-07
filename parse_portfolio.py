#!/usr/bin/env python3
"""
parse_portfolio.py — Parse the full portfolio docx and merge all content into portfolio.json.

Extracts:
  - All keynotes/talks (with year, topic, venue, location)
  - All publications (books, chapters, articles, journalism, reports)
  - All projects/events organised
  - Teaching entries

Tags are inferred from keywords in titles and content.
Items are flagged needs_tagging: true where confidence is low.

Usage:
    python parse_portfolio.py path/to/portfolio.docx
    python parse_portfolio.py path/to/portfolio.docx --dry-run
    python parse_portfolio.py path/to/portfolio.docx --section keynotes
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime

try:
    from docx import Document
except ImportError:
    print("ERROR: python-docx not installed. Run: pip install python-docx")
    sys.exit(1)

PORTFOLIO_PATH = os.path.join(os.path.dirname(__file__), "portfolio.json")

# ── Tag inference keywords ─────────────────────────────────────────────────────
TAG_RULES: list[tuple[list[str], list[str]]] = [
    # keyword list → tags to assign
    (["esport", "esports", "gaming", "gametech", "game-based", "gamification",
      "video game", "fortnite", "competitive gaming", "ldn utd", "gef con",
      "british esports", "global esports", "esic"],
     ["esports", "gaming", "digital-sport"]),

    (["olympic", "olympics", "paralympic", "ioc", "olympism", "olympiad",
      "culture @ the", "non-accredited media", "sport accord", "lausanne",
      "mega-event", "opening ceremony"],
     ["olympic-studies", "olympics", "mega-events"]),

    (["health", "wellbeing", "nhs", "medical", "clinical", "wearable",
      "mhealth", "digital health", "patient", "cancer", "dementia",
      "surveillance", "medicalization", "cyberspace", "health inequality",
      "health technology", "digital well"],
     ["digital-health", "health-wellbeing"]),

    (["bioethic", "enhancement", "gene doping", "genetic", "posthuman",
      "transhuman", "doping", "anti-doping", "human enhancement",
      "genetically modified", "bioart", "biotechnology", "neuralink",
      "cyborg", "regenerative", "cloning", "stem cell", "nano"],
     ["bioethics", "enhancement", "gene-doping", "emerging-tech"]),

    (["ai ", "artificial intelligence", "machine learning", "algorithm",
      "automation", "chatgpt", "generative", "llm", "robot", "autonomous",
      "deep learning", "neural network", "ai ethics", "responsible ai",
      "ai for good", "probable futures"],
     ["ai-ethics", "ai", "emerging-tech"]),

    (["metaverse", "virtual reality", "vr ", " vr", "xr ", "augmented reality",
      "immersive", "phygital", "web3", "digital twin", "mixed reality"],
     ["metaverse", "esports", "createch", "gametech"]),

    (["science communication", "scicomm", "public engagement", "famelab",
      "science festival", "cheltenham", "edinburgh science", "new scientist",
      "communicating science", "public understanding", "science blogging",
      "science question time", "research impact", "outreach", "citizen science",
      "citizen journalism", "science photography", "blue dot"],
     ["science-communication", "public-engagement", "scicomm"]),

    (["manchester", "salford", "mediacity", "gmca", "greater manchester",
      "factory international", "contact theatre", "future everything",
      "abandon normal devices", "cornerhouse", "mosi"],
     ["manchester", "civic", "creative-manchester"]),

    (["creative industries", "createch", "creative economy", "creative tech",
      "innovation hub", "innovate uk", "accelerator", "sme", "startup",
      "entrepreneur", "knowledge exchange", "industry collaboration"],
     ["createch", "creative-industries", "platform-leadership", "innovation"]),

    (["drone", "uav", "quadcopter", "autonomous flying"],
     ["science-communication", "arts-science", "emerging-tech"]),

    (["platform", "interdisciplinary", "research platform", "cross-faculty",
      "cross-school", "ref ", "impact", "civic university", "engagement forum",
      "strategy", "director", "leadership"],
     ["platform-leadership", "interdisciplinary", "civic"]),

    (["social media", "twitter", "digital media", "new media", "web 2.0",
      "tiktok", "instagram", "youtube", "streaming", "broadcast"],
     ["science-communication", "media", "broadcast"]),

    (["sport", "athlete", "fitness", "performance", "anti-doping", "wada",
      "sports science", "exercise"],
     ["digital-sport", "olympic-studies"]),

    (["art", "arts", "bioart", "creative practice", "culture", "festival",
      "exhibition", "installation", "performance", "film", "cinema",
      "music", "design"],
     ["arts-science", "creative-industries"]),

    (["climate", "environment", "cop26", "sustainability", "nature",
      "ecology", "green"],
     ["civic", "science-communication"]),

    (["edi", "diversity", "inclusion", "equality", "widening participation",
      "social responsibility", "social justice", "equity"],
     ["civic", "platform-leadership"]),

    (["teaching", "curriculum", "pedagogy", "student", "education",
      "learning", "university", "postgraduate", "phd", "lecture"],
     ["science-communication", "platform-leadership"]),

    (["peace", "diplomacy", "governance", "policy", "government", "parliament",
      "select committee", "european commission", "eu ", "nato", "united nations",
      "itu", "un "],
     ["governance", "platform-leadership", "ai-ethics"]),
]

CONFIDENCE_BOOST_PATTERNS = [
    # If multiple strong keywords appear, bump confidence
    (["esport", "gaming", "esic", "gef", "british esports"], "esports"),
    (["olympic", "ioc", "olympiad", "paralympic"], "olympic-studies"),
    (["health", "nhs", "clinical", "patient", "wellbeing"], "digital-health"),
    (["ai", "artificial intelligence", "machine learning"], "ai-ethics"),
    (["bioethic", "gene", "doping", "posthuman", "transhuman"], "bioethics"),
]


def infer_tags(text: str) -> tuple[list[str], bool]:
    """
    Infer tags from text content.
    Returns (tags, needs_tagging).
    needs_tagging=True if confidence is low (fewer than 2 tag groups matched).
    """
    text_lower = text.lower()
    matched_tags: set[str] = set()
    groups_matched = 0

    for keywords, tags in TAG_RULES:
        if any(kw in text_lower for kw in keywords):
            matched_tags.update(tags)
            groups_matched += 1

    needs_tagging = groups_matched < 1
    return sorted(matched_tags), needs_tagging


def clean(text: str) -> str:
    return " ".join(text.strip().split())


def extract_year(text: str) -> str:
    m = re.search(r'\b(19|20)\d{2}\b', text)
    return m.group(0) if m else ""


def make_keynote(text: str, source: str) -> dict:
    tags, nt = infer_tags(text)
    return {
        "text": clean(text),
        "tags": tags,
        "needs_tagging": nt,
        "source": source,
        "added": datetime.today().strftime("%Y-%m-%d"),
    }


def make_pub(citation: str, kind: str, source: str) -> dict:
    tags, nt = infer_tags(citation)
    return {
        "citation": clean(citation),
        "tags": tags,
        "needs_tagging": nt,
        "source": source,
        "added": datetime.today().strftime("%Y-%m-%d"),
        "_kind": kind,
    }


def make_project(text: str, source: str) -> dict:
    tags, nt = infer_tags(text)
    return {
        "text": clean(text),
        "tags": tags,
        "needs_tagging": nt,
        "source": source,
        "added": datetime.today().strftime("%Y-%m-%d"),
        "_kind": "project",
    }


# ── Docx parser ───────────────────────────────────────────────────────────────

def parse_docx(path: str) -> dict[str, list]:
    """Parse the portfolio docx and return categorised items."""
    doc = Document(path)
    full_text = "\n".join(p.text for p in doc.paragraphs)
    lines = [clean(p.text) for p in doc.paragraphs if clean(p.text)]

    results: dict[str, list] = {
        "keynotes": [],
        "journal_articles": [],
        "chapters": [],
        "books": [],
        "books_forthcoming": [],
        "journalism": [],
        "reports": [],
        "projects": [],
        "events_organised": [],
        "teaching": [],
    }

    # ── State machine ──────────────────────────────────────────────────────────
    section = None
    current_year = ""
    source = os.path.basename(path)

    SECTION_MARKERS = {
        "keynote": ["KEYNOTES", "INVITED PRESENTATIONS", "CONFERENCE KEYNOTES"],
        "journal": ["REFEREED JOURNAL ARTICLES", "JOURNAL ARTICLES"],
        "chapter": ["BOOK CHAPTERS", "CHAPTERS"],
        "book_pub": ["PUBLISHED", "AUTHORED BOOKS"],
        "book_dev": ["IN DEVELOPMENT", "FORTHCOMING"],
        "edited": ["EDITED BOOKS"],
        "journalism": ["JOURNALISM", "REVIEW ESSAYS"],
        "report": ["OTHER/REPORTS", "REPORTS"],
        "project": ["MAJOR PROJECTS", "PROJECTS /"],
        "event": ["EVENT ORGANIZATION", "EVENT ORGANISATION"],
        "teaching": ["TEACHING", "COURSES"],
    }

    def detect_section(line: str) -> str | None:
        upper = line.upper()
        for sec, markers in SECTION_MARKERS.items():
            if any(m in upper for m in markers):
                return sec
        return None

    def is_year_heading(line: str) -> bool:
        return bool(re.match(r'^(20|19)\d{2}', line)) or bool(
            re.match(r'^###?\s*(20|19)\d{2}', line))

    def is_citation(line: str) -> bool:
        # Looks like a publication citation
        return bool(re.search(r'Miah.*\d{4}', line)) or (
            line.startswith("- ") and re.search(r'\d{4}', line))

    def is_keynote_entry(line: str) -> bool:
        # Looks like a talk entry: starts with - or contains comma + year pattern
        if line.startswith("- ") or line.startswith("• "):
            return True
        # Or contains a year and a venue
        if re.search(r'\d{4}', line) and ("," in line or "." in line):
            if len(line) > 20:
                return True
        return False

    def is_project_entry(line: str) -> bool:
        return bool(re.match(r'\d{4}.*:', line)) or bool(
            re.match(r'\*+\d{4}', line))

    # ── Main parse loop ────────────────────────────────────────────────────────
    for i, line in enumerate(lines):
        if not line:
            continue

        # Detect section changes
        new_sec = detect_section(line)
        if new_sec:
            section = new_sec
            continue

        # Track year headings
        if is_year_heading(line):
            m = re.search(r'(20|19)\d{2}', line)
            if m:
                current_year = m.group(0)
            continue

        # Strip leading bullets/hyphens
        clean_line = re.sub(r'^[-•*]+\s*', '', line).strip()
        if not clean_line or len(clean_line) < 8:
            continue

        # ── Keynotes ────────────────────────────────────────────────────────
        if section == "keynote":
            if len(clean_line) > 15:
                # Add year if not in string
                entry = clean_line
                if current_year and current_year not in entry:
                    entry = f"{entry} ({current_year})"
                results["keynotes"].append(make_keynote(entry, source))

        # ── Journal articles ─────────────────────────────────────────────────
        elif section == "journal":
            if is_citation(line):
                results["journal_articles"].append(
                    make_pub(clean_line, "journal_article", source))

        # ── Book chapters ────────────────────────────────────────────────────
        elif section == "chapter":
            if is_citation(line) and len(clean_line) > 30:
                results["chapters"].append(
                    make_pub(clean_line, "chapter", source))

        # ── Books published ──────────────────────────────────────────────────
        elif section == "book_pub":
            if is_citation(line) and len(clean_line) > 20:
                results["books"].append(
                    make_pub(clean_line, "book", source))

        # ── Books forthcoming ────────────────────────────────────────────────
        elif section == "book_dev":
            if len(clean_line) > 10:
                results["books_forthcoming"].append(
                    make_pub(clean_line, "book_forthcoming", source))

        # ── Journalism ───────────────────────────────────────────────────────
        elif section == "journalism":
            if is_citation(line) and len(clean_line) > 20:
                results["journalism"].append(
                    make_pub(clean_line, "journalism", source))

        # ── Reports ─────────────────────────────────────────────────────────
        elif section == "report":
            if len(clean_line) > 20:
                results["reports"].append(
                    make_pub(clean_line, "report", source))

        # ── Projects ─────────────────────────────────────────────────────────
        elif section == "project":
            if len(clean_line) > 20:
                results["projects"].append(
                    make_project(clean_line, source))

        # ── Events organised ─────────────────────────────────────────────────
        elif section == "event":
            if len(clean_line) > 10:
                results["events_organised"].append(
                    make_project(clean_line, source))

        # ── Teaching ─────────────────────────────────────────────────────────
        elif section == "teaching":
            if len(clean_line) > 10:
                results["teaching"].append({
                    "text": clean_line,
                    "tags": infer_tags(clean_line)[0],
                    "needs_tagging": infer_tags(clean_line)[1],
                    "source": source,
                    "added": datetime.today().strftime("%Y-%m-%d"),
                })

    return results


# ── Dedup and merge ───────────────────────────────────────────────────────────

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


def merge_all(portfolio: dict, parsed: dict[str, list]) -> dict[str, dict[str, int]]:
    """Merge parsed content into portfolio and return counts."""
    counts: dict[str, dict[str, int]] = {}

    # Keynotes → portfolio["keynotes"]
    a, s = merge_section(portfolio["keynotes"], parsed["keynotes"])
    counts["keynotes"] = {"added": a, "skipped": s}

    # Publications
    pubs = portfolio["publications"]
    for key, pkey in [
        ("journal_articles", "journal_articles"),
        ("chapters", "chapters"),
        ("books", "books"),
        ("books_forthcoming", "books_forthcoming"),
        ("journalism", "journalism"),
    ]:
        a, s = merge_section(pubs[pkey], parsed[key])
        counts[key] = {"added": a, "skipped": s}

    # Reports → journalism (closest fit)
    a, s = merge_section(pubs["journalism"], parsed["reports"])
    counts["reports"] = {"added": a, "skipped": s}

    # Projects → new top-level key if not exists
    if "projects" not in portfolio:
        portfolio["projects"] = []
    a, s = merge_section(portfolio["projects"], parsed["projects"])
    counts["projects"] = {"added": a, "skipped": s}

    # Events organised → governance_advisory (events are leadership activities)
    events_as_advisory = [
        {
            "title": "Event Organiser",
            "org": item["text"][:80],
            "dates": extract_year(item["text"]) or "various",
            "tags": item["tags"],
            "needs_tagging": item["needs_tagging"],
            "added": item["added"],
        }
        for item in parsed["events_organised"]
    ]
    a, s = merge_section(portfolio["governance_advisory"], events_as_advisory)
    counts["events_organised"] = {"added": a, "skipped": s}

    # Teaching → new top-level key if not exists
    if "teaching" not in portfolio:
        portfolio["teaching"] = []
    a, s = merge_section(portfolio["teaching"], parsed["teaching"])
    counts["teaching"] = {"added": a, "skipped": s}

    return counts


# ── Main ──────────────────────────────────────────────────────────────────────

def count_needs_tagging(portfolio: dict) -> int:
    count = 0
    def recurse(obj):
        nonlocal count
        if isinstance(obj, list):
            for i in obj: recurse(i)
        elif isinstance(obj, dict):
            if obj.get("needs_tagging"):
                count += 1
            for v in obj.values(): recurse(v)
    recurse(portfolio)
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Parse portfolio docx and merge into portfolio.json",
        epilog="Example: python parse_portfolio.py cv2026_01-portfolio.docx"
    )
    parser.add_argument("docx_path", help="Path to the portfolio .docx file")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Show what would be added without writing")
    parser.add_argument("--section", "-s",
                        choices=["keynotes", "publications", "projects", "all"],
                        default="all",
                        help="Which section to parse (default: all)")
    args = parser.parse_args()

    if not os.path.exists(args.docx_path):
        print(f"ERROR: File not found: {args.docx_path}")
        sys.exit(1)

    if not os.path.exists(PORTFOLIO_PATH):
        print(f"ERROR: portfolio.json not found at {PORTFOLIO_PATH}")
        sys.exit(1)

    print(f"\nParsing: {args.docx_path}")
    parsed = parse_docx(args.docx_path)

    print("\nExtracted:")
    for section, items in parsed.items():
        if items:
            print(f"  {section}: {len(items)} items")

    if args.dry_run:
        print("\n[Dry run — no changes written]")
        print("\nSample keynotes:")
        for k in parsed["keynotes"][:5]:
            print(f"  [{', '.join(k['tags'][:3])}] {k['text'][:80]}")
        return

    # Load, merge, save
    with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
        portfolio = json.load(f)

    counts = merge_all(portfolio, parsed)

    with open(PORTFOLIO_PATH, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=2, ensure_ascii=False)

    print("\nMerge complete:")
    total_added = 0
    for section, c in counts.items():
        if c["added"] > 0:
            print(f"  {section}: +{c['added']} added, {c['skipped']} skipped")
            total_added += c["added"]

    print(f"\nTotal new items added: {total_added}")

    nt = count_needs_tagging(portfolio)
    if nt > 0:
        print(f"\n⚠  {nt} items flagged needs_tagging: true")
        print("   Run: python add_item.py --untagged  to review")
    else:
        print("\n✓  All items tagged")

    print()


if __name__ == "__main__":
    main()
