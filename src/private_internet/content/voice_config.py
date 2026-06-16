"""ElevenLabs voice routing + RTL/display config for SIGNAL.

Maps a resolved BCP-47 language code to an ElevenLabs voice id, and exposes
RTL + human-name helpers so the API can tell the Vue frontend how to render
captions/subtitles without the frontend ever hardcoding a language set.
"""

# Real ElevenLabs premade voice IDs (validated against the account). With the
# eleven_multilingual_v2 model a single voice speaks any language, so these are
# distinct voices per language for variety, not native-accent voices.
# TODO: swap in native ar/ru/ja voices after auditioning if pronunciation matters.
VOICE_MAP: dict[str, str] = {
    "en": "SAz9YHcvj6GT2YYXdXww",  # River — relaxed, neutral, informative
    "de": "JBFqnCBsd6RMkjVDRZzb",  # George — warm storyteller
    "ar": "EXAVITQu4vr4xnSDxMaL",  # Sarah — mature, reassuring
    "ru": "CwhRBWXzGAHq8TQ4Fs17",  # Roger — laid-back, resonant
    "fr": "IKne3meq5aSn9XLyUdCD",  # Charlie — confident
    "ja": "cgSgspJ2msm6clMCkdW9",  # Jessica — clear, calm (eleven_multilingual_v2)
    "es": "VR6AewLTigWG4xSOukaG",  # Arnold — strong, composed
    "pt": "ODq5zmih8GrVes37Dx0d",  # Patrick — articulate
    "zh": "SAz9YHcvj6GT2YYXdXww",  # River (fallback until a native Mandarin voice is auditioned)
    "ko": "cgSgspJ2msm6clMCkdW9",  # Jessica (fallback until a native Korean voice is auditioned)
    "it": "IKne3meq5aSn9XLyUdCD",  # Charlie — confident
    "nl": "JBFqnCBsd6RMkjVDRZzb",  # George — warm
}
DEFAULT_VOICE_ID = VOICE_MAP["en"]

# Passed to Claude as a name ("Respond only in Japanese") — more reliable than
# codes. Claude understands most BCP-47 codes too, but explicit names are safer.
LANGUAGE_NAMES: dict[str, str] = {
    "ar": "Arabic",
    "de": "German",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "nl": "Dutch",
    "pt": "Portuguese",
    "ru": "Russian",
    "zh": "Chinese",
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
