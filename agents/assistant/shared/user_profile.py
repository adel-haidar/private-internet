"""Per-user "ABOUT THE USER" context builder.

Service B's analysis agents (banking, health, job, trading) must reason about the
CALLER, not the platform owner. Previously every system prompt hardcoded the
platform owner's identity (name, weight goal, bank, target employers), so in a
multi-tenant deployment every user's analysis was computed as if they were the owner.

This module builds a concise, per-user profile block from the caller's OWN brain
via `MemoryClient` (Service A's per-user memory REST API, scoped by the forwarded
bearer token). It searches for profile-relevant facts and returns a short text
block suitable for injection into an LLM system/user prompt. When the brain has
nothing relevant, it returns neutral, person-agnostic defaults — never a hardcoded
identity.

Each domain has its own search queries and default so the injected block is
focused (financial facts for banking, training/medical context for health, etc.).
"""

import logging
from typing import Literal

logger = logging.getLogger(__name__)

Domain = Literal["general", "banking", "investing", "trading", "health", "job"]

# Semantic queries per domain — run against the CALLER's brain. Kept short and
# generic (no person, no place) so they generalise to any user.
_PROFILE_QUERIES: dict[Domain, list[str]] = {
    "general": [
        "user's name, role, profession, and where they are based",
        "personal goals, priorities, and life context",
    ],
    "banking": [
        "user's name, location, and currency they are paid in",
        "income, salary, bank accounts, and recurring fixed costs",
        "savings goals, budget targets, and financial priorities",
        "household commitments, family support, subscriptions",
    ],
    "investing": [
        "user's name, location, and risk profile",
        "investment goals, savings target, time horizon",
        "brokerage accounts, portfolio preferences, asset preferences",
    ],
    "trading": [
        "user's risk appetite and trading preferences",
        "markets, regions, and instruments the user trades or follows",
        "position sizing and risk tolerance for speculative trades",
    ],
    "health": [
        "user's name, age, and physical context",
        "weight, body composition goals, and target weight",
        "training routine, fitness goals, and activity level",
        "medical conditions, diagnoses, and dietary context",
    ],
    "job": [
        "user's name, current job title, seniority, and location",
        "work rights, citizenship, visa status, and languages",
        "technical skills, core technology stack, and domain expertise",
        "target roles, desired companies, salary expectations, and relocation preferences",
    ],
}

# Neutral, person-agnostic fallbacks. These deliberately assert NO identity — they
# instruct the model to reason only from the data actually provided and to flag the
# missing profile, rather than assuming any particular person's circumstances.
_DEFAULT_PROFILE: dict[Domain, str] = {
    "general": (
        "No personal profile is available in this user's brain yet. Do not assume "
        "any name, location, or personal circumstances. Reason only from the data "
        "provided in this request, and keep advice general."
    ),
    "banking": (
        "No personal financial profile is available in this user's brain yet. Do not "
        "assume a country, currency, salary, savings target, or fixed commitments. "
        "Infer the currency and recurring costs from the statement itself, and keep "
        "budgets and recommendations grounded only in the observed transactions. "
        "If a savings target is needed and none is known, state that it is unknown "
        "rather than inventing one."
    ),
    "investing": (
        "No personal investing profile is available in this user's brain yet. Do not "
        "assume a country, currency, broker, risk profile, or savings target. Base the "
        "analysis only on the strategy and financial context provided; if risk profile "
        "or contribution capacity is unknown, say so rather than guessing."
    ),
    "trading": (
        "No personal trading profile is available in this user's brain yet. Do not "
        "assume a risk appetite, broker, or position sizing. Treat this as a small "
        "speculative sleeve, be explicit about uncertainty, and base calls only on the "
        "provided market snapshot and any strategy context."
    ),
    "health": (
        "No personal health profile is available in this user's brain yet. Do not "
        "assume a starting weight, target weight, body-composition goal, training "
        "routine, or any medical condition. Base the analysis only on the device "
        "metrics and medical records actually provided; if a goal is referenced but "
        "unknown, state that it is unknown rather than inventing one."
    ),
    "job": (
        "No candidate profile is available in this user's brain yet. Do not assume a "
        "name, location, citizenship, work rights, skill set, target companies, or "
        "salary expectations. If no profile is provided, do not score against any "
        "assumed background."
    ),
}

_PROFILE_HEADER = "ABOUT THE USER (sourced from the user's own brain)"


async def build_user_profile(
    memory_client,
    domain: Domain = "general",
    *,
    max_chars: int = 2500,
) -> str:
    """Build an "ABOUT THE USER" context block for the caller from their brain.

    Searches the caller's per-user memory (via `memory_client`, whose bearer token
    is already scoped to the caller) for profile-relevant facts in the given
    `domain`, and returns a short labelled text block. Falls back to a neutral,
    person-agnostic default when the brain has nothing — never a hardcoded identity.

    Args:
        memory_client: A `MemoryClient` whose token is scoped to the caller. May be
            None (e.g. memory not configured) — the neutral default is returned.
        domain: Which profile facets to retrieve and which default to use.
        max_chars: Soft cap on the assembled fact block (keeps the prompt small).

    Returns:
        A labelled text block beginning with `ABOUT THE USER …`, always non-empty.
    """
    default = _DEFAULT_PROFILE.get(domain, _DEFAULT_PROFILE["general"])
    if memory_client is None:
        return f"{_PROFILE_HEADER}\n{default}"

    queries = _PROFILE_QUERIES.get(domain, _PROFILE_QUERIES["general"])
    seen: set[str] = set()
    parts: list[str] = []
    for query in queries:
        try:
            result = (await memory_client._search(query)).strip()
        except Exception:
            logger.warning("User-profile search failed for query %r", query, exc_info=True)
            continue
        if result and result not in seen:
            seen.add(result)
            parts.append(result)

    facts = "\n".join(parts).strip()
    if not facts:
        return f"{_PROFILE_HEADER}\n{default}"

    if len(facts) > max_chars:
        facts = facts[:max_chars].rstrip() + " …"

    return (
        f"{_PROFILE_HEADER}\n"
        "The following facts were retrieved from this user's personal memory. Treat "
        "them as authoritative for who the user is, their goals, and their context. "
        "Do not assume any facts not supported below or by the request data.\n"
        f"{facts}"
    )
