"""
scorer.py — Relevance scoring for CV items based on focus area tags.
"""

from __future__ import annotations
from typing import Any


def resolve_tags(focus: str, focus_areas: dict[str, list[str]]) -> list[str]:
    """
    Return the full list of tags for a given focus keyword.
    Falls back to treating the focus string itself as a tag if not found.
    """
    key = focus.lower().replace(" ", "-")
    if key in focus_areas:
        return focus_areas[key]
    # Try partial match
    for k, tags in focus_areas.items():
        if key in k or k in key:
            return tags
    # Return focus as a single-tag list so the generator still runs
    return [key]


def score_item(item_tags: list[str], active_tags: list[str]) -> int:
    """
    Score a single item by counting tag overlaps with the active tag set.
    """
    return len(set(item_tags) & set(active_tags))


def filter_and_rank(
    items: list[dict[str, Any]],
    active_tags: list[str],
    min_score: int = 1,
    max_items: int | None = None,
) -> list[dict[str, Any]]:
    """
    Filter a list of tagged items by relevance, returning those with score >= min_score,
    sorted descending by score.  Each item must have a 'tags' key.
    """
    scored = []
    for item in items:
        s = score_item(item.get("tags", []), active_tags)
        if s >= min_score:
            scored.append((s, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    result = [item for _, item in scored]

    if max_items is not None:
        result = result[:max_items]

    return result


def filter_bullets(bullets: list[dict[str, Any]], active_tags: list[str]) -> list[str]:
    """
    From a list of bullet dicts (each with 'text' and 'tags'), return the
    text of bullets that match at least one active tag.  If none match,
    return all bullet texts (fallback so the role isn't empty).
    """
    matched = [b["text"] for b in bullets if score_item(b.get("tags", []), active_tags) > 0]
    if not matched:
        matched = [b["text"] for b in bullets]
    return matched
