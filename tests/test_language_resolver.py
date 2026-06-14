"""Unit tests for the deterministic SIGNAL dominant-language resolver."""

from private_internet.content.language_resolver import (
    resolve_dominant_language,
    dominant_language_confidence,
)


def _m(content, language):
    return {"id": "x", "content": content, "language": language}


def test_clear_majority_arabic_over_german():
    # 4 Arabic memories (800 chars) vs 1 German (150) -> Arabic dominates.
    memories = [_m("ا" * 200, "ar") for _ in range(4)] + [_m("d" * 150, "de")]
    assert resolve_dominant_language(memories, "en") == "ar"


def test_exact_tie_falls_back():
    memories = [_m("a" * 100, "ar"), _m("d" * 100, "de")]
    assert resolve_dominant_language(memories, "en") == "en"


def test_near_tie_within_5pct_falls_back():
    # 100 vs 96 -> (100-96)/100 = 0.04 <= 0.05 -> tie -> fallback.
    memories = [_m("a" * 100, "ar"), _m("d" * 96, "de")]
    assert resolve_dominant_language(memories, "fr") == "fr"


def test_just_outside_5pct_wins():
    # 100 vs 94 -> 0.06 > 0.05 -> clear winner.
    memories = [_m("a" * 100, "ar"), _m("d" * 94, "de")]
    assert resolve_dominant_language(memories, "en") == "ar"


def test_all_null_languages_fall_back():
    memories = [_m("hello", None), _m("world", None)]
    assert resolve_dominant_language(memories, "de") == "de"


def test_single_language_cluster():
    memories = [_m("a" * 50, "ru"), _m("b" * 30, "ru")]
    assert resolve_dominant_language(memories, "en") == "ru"


def test_empty_cluster_falls_back():
    assert resolve_dominant_language([], "en") == "en"


def test_null_language_counts_toward_total_not_tally():
    # ar=200 wins outright; the 1000 NULL chars don't help any language win,
    # but they dilute the confidence ratio.
    memories = [_m("ا" * 200, "ar"), _m("x" * 1000, None)]
    assert resolve_dominant_language(memories, "en") == "ar"
    conf = dominant_language_confidence(memories, "ar")
    assert conf == round(200 / 1200, 4)


def test_confidence_empty_is_zero():
    assert dominant_language_confidence([], "en") == 0.0
