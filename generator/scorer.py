"""
scorer.py — Weighted relevance scoring for CV items based on focus area tags.

Title/text matches score higher than tag-only matches.
Exact focus area matches score highest.
"""

from __future__ import annotations
import re
from typing import Any


def resolve_tags(focus: str, focus_areas: dict[str, list[str]]) -> list[str]:
    """
    Return the full list of tags for a given focus keyword.
    Falls back to treating the focus string itself as a tag if not found.
    """
    key = focus.lower().replace(" ", "-")
    if key in focus_areas:
        return focus_areas[key]
    for k, tags in focus_areas.items():
        if key in k or k in key:
            return tags
    return [key]


def score_item(item: dict[str, Any], active_tags: list[str],
               query: str = "") -> int:
    """
    Weighted scoring:
    - Each tag overlap with active_tags: +2 points
    - Query word found in item text/title: +3 points (title matches prioritised)
    - Item has needs_tagging=False (human-verified): +1 bonus
    """
    item_tags = item.get("tags", [])
    tag_score = len(set(item_tags) & set(active_tags)) * 2

    text_score = 0
    if query:
        query_words = set(re.findall(r"[a-z]{3,}", query.lower()))
        item_text = (
            item.get("text") or
            item.get("citation") or
            item.get("title") or ""
        ).lower()
        text_score = sum(3 for w in query_words if w in item_text)

    verified_bonus = 1 if not item.get("needs_tagging", True) else 0

    return tag_score + text_score + verified_bonus


def filter_and_rank(
    items: list[dict[str, Any]],
    active_tags: list[str],
    min_score: int = 1,
    max_items: int | None = None,
    query: str = "",
) -> list[dict[str, Any]]:
    """
    Filter and rank items by weighted score.
    Items scoring below min_score are excluded.
    """
    scored = []
    for item in items:
        s = score_item(item, active_tags, query)
        if s >= min_score:
            scored.append((s, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    result = [item for _, item in scored]

    if max_items is not None:
        result = result[:max_items]

    return result


def filter_bullets(bullets: list[dict[str, Any]],
                   active_tags: list[str]) -> list[str]:
    """
    Return bullet texts matching active tags.
    Falls back to all bullets if none match.
    """
    matched = [b["text"] for b in bullets
               if score_item(b, active_tags) > 0]
    if not matched:
        matched = [b["text"] for b in bullets]
    return matched
