#!/usr/bin/env python3
"""
add_item.py — Quickly add new items to portfolio.json from the terminal.

Usage:
    python add_item.py keynote "AI Ethics in Sport, Oxford University, June 2026"
    python add_item.py publication "Miah, A. (2026) The Ethics of AI. Nature."
    python add_item.py grant "AHRC Digital Futures — Co-I — £450,000 — 2026–2029"
    python add_item.py award "2026 — Fellowship of the Royal Society"
    python add_item.py partnership "Greater Manchester Combined Authority — strategic lead"
    python add_item.py appointment "Visiting Professor — MIT Media Lab — 2026–present"
    python add_item.py advisory "Ethics Board — DeepMind — 2026–present"

After adding, the item is saved with needs_tagging: true.
The script prints the available tags and prompts you to add them inline.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime

PORTFOLIO_PATH = os.path.join(os.path.dirname(__file__), "portfolio.json")

ITEM_TYPES = {
    "keynote":      ("keynotes",        "text"),
    "talk":         ("keynotes",        "text"),
    "publication":  ("publications",    "citation"),
    "pub":          ("publications",    "citation"),
    "grant":        ("grants",          "title"),
    "award":        ("awards",          "text"),
    "partnership":  ("partnerships",    "org"),
    "appointment":  ("appointments",    "title"),
    "advisory":     ("governance_advisory", "title"),
    "media":        ("media",           "text"),
    "uom":          ("uom_collaborations", "text"),
}

PUB_SUBSECTIONS = {
    "book":         "books",
    "chapter":      "chapters",
    "article":      "journal_articles",
    "journal":      "journal_articles",
    "journalism":   "journalism",
    "forthcoming":  "books_forthcoming",
}

COLOURS = {
    "green":  "\033[92m",
    "yellow": "\033[93m",
    "cyan":   "\033[96m",
    "bold":   "\033[1m",
    "reset":  "\033[0m",
}

def c(colour: str, text: str) -> str:
    return f"{COLOURS.get(colour, '')}{text}{COLOURS['reset']}"


def load() -> dict:
    with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save(portfolio: dict) -> None:
    with open(PORTFOLIO_PATH, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=2, ensure_ascii=False)


def print_tags(portfolio: dict) -> None:
    focus_areas = portfolio.get("focus_areas", {})
    all_tags: set[str] = set()
    for tags in focus_areas.values():
        all_tags.update(tags)
    sorted_tags = sorted(all_tags)
    print(c("cyan", "\nAvailable tags:"))
    # Print in rows of 4
    row = []
    for tag in sorted_tags:
        row.append(f"  {tag:<28}")
        if len(row) == 4:
            print("".join(row))
            row = []
    if row:
        print("".join(row))
    print()


def prompt_tags(portfolio: dict) -> list[str]:
    print_tags(portfolio)
    raw = input(c("yellow", "Enter tags (comma-separated, or press Enter to skip): ")).strip()
    if not raw:
        return []
    return [t.strip() for t in raw.split(",") if t.strip()]


def prompt_pub_subsection() -> str:
    print(c("cyan", "\nPublication type:"))
    for key in PUB_SUBSECTIONS:
        print(f"  {key}")
    raw = input(c("yellow", "Type (default: article): ")).strip().lower()
    return PUB_SUBSECTIONS.get(raw, "journal_articles")


def add_keynote(portfolio: dict, text: str) -> None:
    tags = prompt_tags(portfolio)
    item = {
        "text": text,
        "tags": tags,
        "needs_tagging": len(tags) == 0,
        "added": datetime.today().strftime("%Y-%m-%d"),
    }
    portfolio["keynotes"].append(item)
    save(portfolio)
    _confirm("keynote", text, tags)


def add_publication(portfolio: dict, citation: str) -> None:
    subsection = prompt_pub_subsection()
    tags = prompt_tags(portfolio)
    item = {
        "citation": citation,
        "tags": tags,
        "needs_tagging": len(tags) == 0,
        "added": datetime.today().strftime("%Y-%m-%d"),
    }
    portfolio["publications"][subsection].append(item)
    save(portfolio)
    _confirm(f"publication ({subsection})", citation, tags)


def add_grant(portfolio: dict, raw: str) -> None:
    # Try to parse "Title — Role — Amount — Dates" format
    parts = [p.strip() for p in raw.split("—")]
    item: dict = {
        "title":       parts[0] if len(parts) > 0 else raw,
        "funder":      parts[1] if len(parts) > 1 else "",
        "role":        parts[2] if len(parts) > 2 else "",
        "amount":      parts[3] if len(parts) > 3 else "",
        "dates":       parts[4] if len(parts) > 4 else "",
        "description": "",
        "tags":        [],
        "needs_tagging": True,
        "added":       datetime.today().strftime("%Y-%m-%d"),
    }
    print(c("cyan", "\nParsed grant entry:"))
    for k, v in item.items():
        if k not in ("tags", "needs_tagging", "added") and v:
            print(f"  {k}: {v}")
    print(c("yellow", "\nIf any fields are wrong, edit portfolio.json directly after saving.\n"))
    tags = prompt_tags(portfolio)
    item["tags"] = tags
    item["needs_tagging"] = len(tags) == 0
    portfolio["grants"].append(item)
    save(portfolio)
    _confirm("grant", item["title"], tags)


def add_award(portfolio: dict, text: str) -> None:
    tags = prompt_tags(portfolio)
    item = {
        "text": text,
        "tags": tags,
        "needs_tagging": len(tags) == 0,
        "added": datetime.today().strftime("%Y-%m-%d"),
    }
    portfolio["awards"].append(item)
    save(portfolio)
    _confirm("award", text, tags)


def add_partnership(portfolio: dict, raw: str) -> None:
    # Try to parse "Org — Description"
    parts = [p.strip() for p in raw.split("—", 1)]
    item = {
        "org":         parts[0],
        "description": parts[1] if len(parts) > 1 else "",
        "tags":        [],
        "needs_tagging": True,
        "added":       datetime.today().strftime("%Y-%m-%d"),
    }
    tags = prompt_tags(portfolio)
    item["tags"] = tags
    item["needs_tagging"] = len(tags) == 0
    portfolio["partnerships"].append(item)
    save(portfolio)
    _confirm("partnership", item["org"], tags)


def add_appointment(portfolio: dict, raw: str) -> None:
    # Try to parse "Title — Institution — Dates"
    parts = [p.strip() for p in raw.split("—")]
    item = {
        "title":       parts[0] if len(parts) > 0 else raw,
        "institution": parts[1] if len(parts) > 1 else "",
        "dates":       parts[2] if len(parts) > 2 else "",
        "tags":        [],
        "bullets":     [],
        "needs_tagging": True,
        "added":       datetime.today().strftime("%Y-%m-%d"),
    }
    tags = prompt_tags(portfolio)
    item["tags"] = tags
    item["needs_tagging"] = len(tags) == 0
    portfolio["appointments"].append(item)
    save(portfolio)
    _confirm("appointment", item["title"], tags)


def add_advisory(portfolio: dict, raw: str) -> None:
    # Try to parse "Title — Org — Dates"
    parts = [p.strip() for p in raw.split("—")]
    item = {
        "title": parts[0] if len(parts) > 0 else raw,
        "org":   parts[1] if len(parts) > 1 else "",
        "dates": parts[2] if len(parts) > 2 else "",
        "tags":  [],
        "needs_tagging": True,
        "added": datetime.today().strftime("%Y-%m-%d"),
    }
    tags = prompt_tags(portfolio)
    item["tags"] = tags
    item["needs_tagging"] = len(tags) == 0
    portfolio["governance_advisory"].append(item)
    save(portfolio)
    _confirm("advisory role", item["title"], tags)


def add_media(portfolio: dict, text: str) -> None:
    tags = prompt_tags(portfolio)
    item = {
        "text": text,
        "tags": tags,
        "needs_tagging": len(tags) == 0,
        "added": datetime.today().strftime("%Y-%m-%d"),
    }
    portfolio["media"]["highlights"].append(item)
    save(portfolio)
    _confirm("media item", text, tags)


def add_uom(portfolio: dict, text: str) -> None:
    tags = prompt_tags(portfolio)
    item = {
        "text": text,
        "tags": tags,
        "needs_tagging": len(tags) == 0,
        "added": datetime.today().strftime("%Y-%m-%d"),
    }
    portfolio["uom_collaborations"].append(item)
    save(portfolio)
    _confirm("UoM collaboration", text, tags)


def _confirm(kind: str, text: str, tags: list[str]) -> None:
    print()
    print(c("green", f"✓  Added {kind}:"))
    print(f"   {text[:100]}")
    if tags:
        print(f"   Tags: {', '.join(tags)}")
    else:
        print(c("yellow", "   ⚠  No tags added — item flagged as needs_tagging: true"))
        print("   Run:  python add_item.py --untagged  to review all untagged items")
    print()


def show_untagged(portfolio: dict) -> None:
    """Print all items with needs_tagging: true."""
    found = []

    def recurse(obj, path=""):
        if isinstance(obj, list):
            for i, item in enumerate(obj):
                recurse(item, f"{path}[{i}]")
        elif isinstance(obj, dict):
            if obj.get("needs_tagging"):
                text = obj.get("text") or obj.get("citation") or obj.get("title") or "?"
                found.append((path, text))
            else:
                for k, v in obj.items():
                    recurse(v, f"{path}.{k}" if path else k)

    recurse(portfolio)

    if not found:
        print(c("green", "\n✓  All items are tagged.\n"))
    else:
        print(c("yellow", f"\n⚠  {len(found)} item(s) need tagging:\n"))
        for path, text in found:
            print(f"  {c('cyan', path)}")
            print(f"  {text[:100]}\n")


HANDLERS = {
    "keynote":     add_keynote,
    "talk":        add_keynote,
    "publication": add_publication,
    "pub":         add_publication,
    "grant":       add_grant,
    "award":       add_award,
    "partnership": add_partnership,
    "appointment": add_appointment,
    "advisory":    add_advisory,
    "media":       add_media,
    "uom":         add_uom,
}


def print_usage() -> None:
    print(c("bold", "\nadd_item.py — Add items to portfolio.json\n"))
    print("Usage:")
    print("  python add_item.py <type> \"<content>\"")
    print("  python add_item.py --untagged\n")
    print("Types:")
    types = [
        ("keynote",     '"AI Ethics in Sport, Oxford, June 2026"'),
        ("publication", '"Miah, A. (2026) The Ethics of AI. Nature."'),
        ("grant",       '"AHRC — Co-I — £450k — 2026–2029"  (dash-separated fields)'),
        ("award",       '"2026 — Fellowship of the Royal Society"'),
        ("partnership", '"DeepMind — AI ethics advisory"'),
        ("appointment", '"Visiting Professor — MIT Media Lab — 2026–present"'),
        ("advisory",    '"Ethics Board — DeepMind — 2026–present"'),
        ("media",       '"BBC Newsnight, AI and sport ethics (2026)"'),
        ("uom",         '"Prof Jane Smith — joint grant application (2026)"'),
    ]
    for t, example in types:
        print(f"  {c('cyan', t):<20}  e.g. {example}")
    print()


def main() -> None:
    if not os.path.exists(PORTFOLIO_PATH):
        print(f"ERROR: portfolio.json not found at {PORTFOLIO_PATH}", file=sys.stderr)
        sys.exit(1)

    # --untagged flag
    if len(sys.argv) == 2 and sys.argv[1] in ("--untagged", "-u"):
        portfolio = load()
        show_untagged(portfolio)
        return

    if len(sys.argv) < 3:
        print_usage()
        sys.exit(0)

    item_type = sys.argv[1].lower()
    content = " ".join(sys.argv[2:])

    if item_type not in HANDLERS:
        print(f"\nERROR: Unknown type '{item_type}'")
        print(f"Valid types: {', '.join(sorted(set(HANDLERS.keys())))}\n")
        sys.exit(1)

    portfolio = load()
    print(c("bold", f"\nAdding {item_type}: {content[:80]}"))

    HANDLERS[item_type](portfolio, content)


if __name__ == "__main__":
    main()
