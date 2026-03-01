"""
Fuzzy search over the indicator catalog using rapidfuzz.
Falls back gracefully if rapidfuzz is not installed.
"""

from __future__ import annotations

try:
    from rapidfuzz import fuzz
    _HAS_RAPIDFUZZ = True
except ImportError:
    _HAS_RAPIDFUZZ = False


def _score(query: str, indicator: dict) -> float:
    q = query.lower()
    if _HAS_RAPIDFUZZ:
        name_score = fuzz.partial_ratio(q, indicator["name"].lower())
        tag_score = max(
            (fuzz.ratio(q, t.lower()) for t in indicator["tags"]),
            default=0,
        )
        cat_score = fuzz.ratio(q, indicator["category"].lower())
    else:
        # Simple substring fallback
        name_score = 100 if q in indicator["name"].lower() else 0
        tag_score = max((100 if q in t.lower() else 0 for t in indicator["tags"]), default=0)
        cat_score = 100 if q in indicator["category"].lower() else 0
    return max(name_score, tag_score * 0.9, cat_score * 0.7)


def fuzzy_search(query: str, indicators: list, limit: int = 10) -> list:
    """Return indicators sorted by relevance to *query*."""
    if not query.strip():
        return indicators[:limit]
    ranked = sorted(indicators, key=lambda ind: _score(query, ind), reverse=True)
    return ranked[:limit]
