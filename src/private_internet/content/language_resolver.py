"""Deterministic dominant-language resolution for SIGNAL topic clusters.

Pure Python — no LLM, no DB, no I/O. Given the memories that formed a topic
cluster, it picks the BCP-47 language the user predominantly *thinks in* for
that topic: the language with the highest total character count across the
cluster's memories. The user never picks a language; it is always inferred.

Rules (see the SIGNAL language-aware design):
  - Group memories by their detected `language`; sum len(content) per language.
  - Memories with NULL/unknown language count toward the cluster total (used for
    the confidence ratio) but never toward any language's tally.
  - If the top two languages are within 5% of each other by total chars, the
    result is a tie -> return the fallback language.
  - All-NULL or empty cluster -> return the fallback language.

`fallback_language` comes from the user's onboarding-introduction memory (or "en").
"""

from collections import defaultdict

# Within this fraction of the top language's char count counts as a tie.
TIE_THRESHOLD = 0.05


def _char_totals_by_language(memories: list[dict]) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for m in memories:
        lang = m.get("language")
        if not lang:
            continue  # NULL/unknown does not contribute to any language's tally
        totals[lang] += len(m.get("content") or "")
    return dict(totals)


def resolve_dominant_language(
    memories: list[dict],         # each dict: {id, content, language}
    fallback_language: str,       # from onboarding memory or "en"
) -> str:
    """Return the BCP-47 code that dominates the cluster by total character
    count, or `fallback_language` on a tie (top two within 5%) or no signal."""
    totals = _char_totals_by_language(memories)
    if not totals:
        return fallback_language

    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    if len(ranked) >= 2:
        top_chars, second_chars = ranked[0][1], ranked[1][1]
        # Exact ties and near-ties (second within 5% of top) fall back.
        if top_chars > 0 and (top_chars - second_chars) / top_chars <= TIE_THRESHOLD:
            return fallback_language
    return ranked[0][0]


def dominant_language_confidence(memories: list[dict], language_code: str) -> float:
    """Ratio of `language_code`'s char count to the total chars across ALL
    memories in the cluster (including NULL-language ones). 0.0 if empty.

    Useful for debugging and future UI decisions; pure arithmetic."""
    total = sum(len(m.get("content") or "") for m in memories)
    if total == 0:
        return 0.0
    lang_chars = sum(
        len(m.get("content") or "") for m in memories if m.get("language") == language_code
    )
    return round(lang_chars / total, 4)
