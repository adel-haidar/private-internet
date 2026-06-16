import json
import logging
from typing import Optional

from assistant.job.models import JobListing, MatchResult
from assistant.shared.base_llm_service import BaseLLMService

logger = logging.getLogger(__name__)

# Neutral, person-agnostic fallback. The real profile is the CALLER's own, built
# from their brain (see agent.run_agent, which gates the scrape on a non-empty
# profile — a user with no profile is never scraped, so this fallback is only a
# defensive back-compat default and must NOT encode any specific person.
_CANDIDATE_PROFILE = """\
No candidate profile was provided. Do not assume any name, location, citizenship,
work rights, languages, skills, salary, target companies, or domain. With no
profile to score against, treat every listing as a REJECT (insufficient
information) rather than matching against any assumed background."""

def _filter_rules(target_countries: list[str]) -> str:
    countries = ", ".join(target_countries) if target_countries else "the candidate's target countries"
    return f"""\
Hard disqualifiers (auto-reject, no scoring):
  WRONG_COUNTRY         Job is not located in {countries}. A remote job qualifies
                        only if the employer is based in one of these countries.
  CITIZENSHIP_RESTRICTED Role open only to local citizens / nationals, and the
                        candidate's profile shows no matching citizenship or work rights.
  NO_SPONSORSHIP        Role is in a country where the candidate needs sponsorship
                        (per their profile) and none is mentioned.
  TECHNOLOGY_MISMATCH   Primary stack has no overlap with the candidate's core stack.
                        If the candidate's main language is listed only as a 'bonus' or
                        'nice to have' while the primary language is different, or the role
                        title is a clear mismatch → HARD REJECT with TECHNOLOGY_MISMATCH.
  ALREADY_APPLIED       Company is in the candidate's active applications list.
  JUNIOR_ROLE           <3 years expected, entry-level, graduate, or trainee.
  PURE_MANAGEMENT       CTO/VP/Head with no individual-contributor track.

Soft disqualifiers (include with note):
  EXPERIENCE_GAP        Role requires significantly more experience than the candidate has.
  SALARY_BELOW          Compensation is clearly below the candidate's stated target.
  RELOCATION_URGENT     Must be on-site within 30 days."""


def _scoring_model(target_countries: list[str]) -> str:
    countries = ", ".join(target_countries) if target_countries else "a target country"
    return f"""\
Technical fit (0-35): score against the candidate's core stack from their profile.
  35 = Full overlap with the candidate's primary stack (incl. their key frameworks)
  25 = Strong overlap, missing one or two secondary technologies
  15 = Partial overlap (adjacent language/framework)
   5 = Other backend with some clear overlap

Domain fit (0-25): score against the candidate's domain from their profile.
  25 = Candidate's target domain explicitly required
  15 = Adjacent / broader version of that domain
  10 = General enterprise backend
   5 = Unrelated domain

Location / work mode (0-20):
  20 = On-site or hybrid in one of: {countries}
  12 = Remote-first with an employer based in one of those countries
   0 = Outside the target countries

Salary fit (0-10):
  10 = At or above the candidate's stated target
   7 = Within 10% below target
   3 = 10-20% below target
   0 = >20% below, or not disclosed

AI / growth signal (0-10):
  10 = LLM/GenAI/Agentic/Bedrock/RAG/embeddings in JD
   7 = "Building AI capabilities" in JD
   3 = Traditional stack, no AI signal
   0 = Legacy only (COBOL, mainframe)

Tiers: >=70 STRONG_MATCH | 50-69 GOOD_MATCH | 30-49 WEAK_MATCH | <30 REJECT"""

_JSON_SCHEMA = """\
{
  "disqualified": true | false,
  "disqualifier_code": "TECHNOLOGY_MISMATCH" | null,
  "rejection_reason": "string" | null,
  "score": 0-100 | null,
  "match_tier": "STRONG_MATCH" | "GOOD_MATCH" | "WEAK_MATCH" | "REJECT" | null,
  "tech_flags": ["Java", "Spring Boot", ...],
  "domain_flags": ["banking", "fintech", ...],
  "positive_flags": ["BANKING_DOMAIN", "KAFKA_REQUIRED", ...],
  "soft_flags": ["EXPERIENCE_GAP", ...],
  "ai_summary": "2-3 sentences on fit",
  "salary_min_local": 120000 | null,
  "salary_max_local": 150000 | null,
  "currency": "CHF" | "CAD" | "NOK" | "SGD" | null,
  "remote_type": "remote" | "hybrid" | "onsite" | "unknown"
}"""


def _build_prompt(listing: JobListing, candidate_profile: str, target_countries: list[str]) -> str:
    return "\n".join([
        "You are a strict job matching agent. Evaluate the listing against the candidate profile.",
        "Apply hard disqualifiers first. If not disqualified, score on the 0-100 scale.",
        "Return ONLY valid JSON — no prose, no markdown fences, nothing outside the JSON.",
        "",
        "=== CANDIDATE PROFILE ===",
        candidate_profile,
        "",
        "=== FILTER RULES ===",
        _filter_rules(target_countries),
        "",
        "=== SCORING MODEL ===",
        _scoring_model(target_countries),
        "",
        "=== REQUIRED RETURN FORMAT (strict JSON) ===",
        _JSON_SCHEMA,
        "",
        "=== JOB LISTING ===",
        f"Title:    {listing.title}",
        f"Company:  {listing.company}",
        f"Location: {listing.location}, {listing.country}",
        f"Platform: {listing.platform}",
        f"Salary:   {listing.salary_raw or 'not disclosed'}",
        "",
        "Description:",
        listing.description[:8000],
    ])


class JobScorer(BaseLLMService):
    def __init__(
        self,
        bedrock_client,
        model_id,
        candidate_profile: Optional[str] = None,
        target_countries: Optional[list[str]] = None,
    ):
        super().__init__(bedrock_client=bedrock_client, model_id=model_id)
        # Score against the CALLER's profile (from their brain). Fall back to the
        # owner profile only if none was supplied (back-compat).
        self._candidate_profile = candidate_profile or _CANDIDATE_PROFILE
        # Target countries are the user's dashboard selection (display names).
        self._target_countries = target_countries or []

    def score(self, listing: JobListing) -> Optional[MatchResult]:
        try:
            raw = self._strip_markdown(
                self._invoke(
                    _build_prompt(listing, self._candidate_profile, self._target_countries),
                    max_tokens=2048,
                )
            )
            data = json.loads(raw)
            return MatchResult(**data)
        except Exception:
            logger.exception(
                "Scoring failed for %r at %r", listing.title, listing.company
            )
            return None
