"""Best-effort language detection for memories (lingua-based).

Runs at memory *save* time and stores a BCP-47 code on the row so the SIGNAL
pipeline can resolve a topic cluster's dominant language deterministically
(content/language_resolver.py) without re-scanning text on read.

Best-effort by design: any failure — library missing, text too short, or
confidence below threshold — returns None, which is stored as NULL ("unknown")
and never blocks a save. lingua handles short, non-Latin scripts (Arabic,
Russian, Chinese) better than langdetect.
"""

from functools import lru_cache

# Curated to the platform's supported locales so the detector stays small and
# fast instead of loading all ~75 lingua models.
_LANGUAGES = (
    "ENGLISH", "GERMAN", "FRENCH", "SPANISH", "ARABIC", "RUSSIAN", "CHINESE", "SWEDISH",
)
_MIN_CONFIDENCE = 0.85   # below this -> store NULL (treated as unknown)
_MIN_CHARS = 10          # too short to detect reliably


@lru_cache(maxsize=1)
def _detector():
    """Built once, lazily — importing lingua and loading models is expensive."""
    from lingua import Language, LanguageDetectorBuilder

    langs = [getattr(Language, name) for name in _LANGUAGES]
    return LanguageDetectorBuilder.from_languages(*langs).build()


def detect_language(text: str | None) -> str | None:
    """Return a lowercase BCP-47 code (e.g. 'ar') or None when unknown."""
    text = (text or "").strip()
    if len(text) < _MIN_CHARS:
        return None
    try:
        values = _detector().compute_language_confidence_values(text)
        if not values:
            return None
        top = values[0]
        if top.value < _MIN_CONFIDENCE:
            return None
        return top.language.iso_code_639_1.name.lower()
    except Exception:
        # Library missing or any detection error -> unknown, never break the save.
        return None
