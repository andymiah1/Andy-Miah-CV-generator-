#!/usr/bin/env python3
"""
generate_cv.py — CLI for generating a tailored PDF CV from portfolio.json

Usage:
    python generate_cv.py --focus esports
    python generate_cv.py --focus "creative-manchester"
    python generate_cv.py --focus "science-communication" --out output/custom.pdf
    python generate_cv.py --list-focuses
"""

import argparse
import json
import os
import sys

from generator.scorer import resolve_tags
from generator.builder import build_cv


PORTFOLIO_PATH = os.path.join(os.path.dirname(__file__), "portfolio.json")
OUTPUT_DIR     = os.path.join(os.path.dirname(__file__), "output")


def load_portfolio() -> dict:
    if not os.path.exists(PORTFOLIO_PATH):
        print(f"ERROR: portfolio.json not found at {PORTFOLIO_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a tailored PDF CV from Andy Miah's portfolio data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_cv.py --focus esports
  python generate_cv.py --focus creative-manchester
  python generate_cv.py --focus "science communication"
  python generate_cv.py --focus ai-ethics --out my_cv.pdf
  python generate_cv.py --list-focuses
        """
    )
    parser.add_argument(
        "--focus", "-f",
        type=str,
        help="Focus area for the CV (e.g. esports, ai-ethics, science-communication)",
    )
    parser.add_argument(
        "--out", "-o",
        type=str,
        default=None,
        help="Output PDF path (default: output/cv_<focus>.pdf)",
    )
    parser.add_argument(
        "--list-focuses",
        action="store_true",
        help="List all available focus areas and exit",
    )
    args = parser.parse_args()

    portfolio = load_portfolio()
    focus_areas = portfolio["focus_areas"]

    if args.list_focuses:
        print("\nAvailable focus areas:\n")
        for key, tags in focus_areas.items():
            print(f"  {key}")
            print(f"    Tags: {', '.join(tags)}\n")
        sys.exit(0)

    if not args.focus:
        parser.print_help()
        print("\nERROR: --focus is required. Use --list-focuses to see options.", file=sys.stderr)
        sys.exit(1)

    # Resolve focus to tags
    focus_label = args.focus.lower().replace(" ", "-")
    active_tags = resolve_tags(focus_label, focus_areas)

    print(f"\nGenerating CV for focus: '{focus_label}'")
    print(f"Active tags: {', '.join(active_tags)}")

    # Determine output path
    if args.out:
        output_path = args.out
    else:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        safe_name = focus_label.replace("/", "-").replace("\\", "-")
        output_path = os.path.join(OUTPUT_DIR, f"cv_{safe_name}.pdf")

    # Build the CV
    result = build_cv(
        portfolio=portfolio,
        active_tags=active_tags,
        focus_label=focus_label,
        output_path=output_path,
    )

    print(f"\n✓  CV generated: {result}")
    print(f"   Focus: {focus_label}")
    print(f"   Tags used: {', '.join(active_tags)}\n")


if __name__ == "__main__":
    main()
