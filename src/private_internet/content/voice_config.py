"""ElevenLabs voice routing + RTL/display config for SIGNAL.

Maps a resolved BCP-47 language code to an ElevenLabs voice id, and exposes
RTL + human-name helpers so the API can tell the Vue frontend how to render
captions/subtitles without the frontend ever hardcoding a language set.
"""

# TODO: Replace with real ElevenLabs voice IDs after auditioning in the playground.
# (The account's premade voices are reachable; pick per-language and paste here.)
VOICE_MAP: dict[str, str] = {
    "en": "VOICE_ID_ENGLISH",
    "de": "VOICE_ID_GERMAN",
    "ar": "VOICE_ID_ARABIC",
    "ru": "VOICE_ID_RUSSIAN",
    "fr": "VOICE_ID_FRENCH",
}
DEFAULT_VOICE_ID = VOICE_MAP["en"]

# Passed to Claude as a name ("Respond only in Arabic") — more reliable than codes.
LANGUAGE_NAMES: dict[str, str] = {
    "ar": "Arabic",
    "de": "German",
    "ru": "Russian",
    "en": "English",
    "fr": "French",
}

# Right-to-left scripts. The frontend reads `is_rtl` from the API, never this set.
RTL_LANGUAGES: set[str] = {"ar", "he", "fa", "ur"}


def get_voice_id(language_code: str) -> str:
    """ElevenLabs voice id for a language, or the default if unmapped."""
    return VOICE_MAP.get(language_code, DEFAULT_VOICE_ID)


def language_name(language_code: str) -> str:
    """Human language name for the LLM system prompt; falls back to the code
    itself (Claude understands most BCP-47 codes)."""
    return LANGUAGE_NAMES.get(language_code, language_code)


def is_rtl(language_code: str) -> bool:
    return language_code in RTL_LANGUAGES
