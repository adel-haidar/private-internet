"""Canonical country list for the job hunt agent.

Single source of truth for the country dropdown (frontend) and the JSearch
scrape + scorer (backend). Codes are ISO 3166-1 alpha-2 — exactly what the
JSearch `country` parameter expects. The user picks any of these; nothing about
the target market is hardcoded anymore.
"""

# (ISO 3166-1 alpha-2, display name). Curated to the markets JSearch covers
# well; alphabetical by name so the dropdown reads naturally.
COUNTRIES: list[tuple[str, str]] = [
    ("AR", "Argentina"),
    ("AU", "Australia"),
    ("AT", "Austria"),
    ("BE", "Belgium"),
    ("BR", "Brazil"),
    ("CA", "Canada"),
    ("CL", "Chile"),
    ("CN", "China"),
    ("CO", "Colombia"),
    ("CZ", "Czechia"),
    ("DK", "Denmark"),
    ("EG", "Egypt"),
    ("FI", "Finland"),
    ("FR", "France"),
    ("DE", "Germany"),
    ("GR", "Greece"),
    ("HK", "Hong Kong"),
    ("HU", "Hungary"),
    ("IN", "India"),
    ("ID", "Indonesia"),
    ("IE", "Ireland"),
    ("IL", "Israel"),
    ("IT", "Italy"),
    ("JP", "Japan"),
    ("LU", "Luxembourg"),
    ("MY", "Malaysia"),
    ("MX", "Mexico"),
    ("NL", "Netherlands"),
    ("NZ", "New Zealand"),
    ("NO", "Norway"),
    ("PH", "Philippines"),
    ("PL", "Poland"),
    ("PT", "Portugal"),
    ("QA", "Qatar"),
    ("RO", "Romania"),
    ("SA", "Saudi Arabia"),
    ("SG", "Singapore"),
    ("ZA", "South Africa"),
    ("KR", "South Korea"),
    ("ES", "Spain"),
    ("SE", "Sweden"),
    ("CH", "Switzerland"),
    ("TW", "Taiwan"),
    ("TH", "Thailand"),
    ("TR", "Türkiye"),
    ("AE", "United Arab Emirates"),
    ("GB", "United Kingdom"),
    ("US", "United States"),
    ("UA", "Ukraine"),
    ("VN", "Vietnam"),
]

_NAME_BY_CODE: dict[str, str] = {code: name for code, name in COUNTRIES}


def is_valid(code: str) -> bool:
    """True if `code` is a known ISO alpha-2 country code (case-insensitive)."""
    return bool(code) and code.upper() in _NAME_BY_CODE


def name_for(code: str) -> str:
    """Display name for an ISO code; falls back to the upper-cased code."""
    return _NAME_BY_CODE.get((code or "").upper(), (code or "").upper())


def as_dicts() -> list[dict[str, str]]:
    """Serialisable form for the API: ``[{"code": "CH", "name": "Switzerland"}]``."""
    return [{"code": code, "name": name} for code, name in COUNTRIES]
