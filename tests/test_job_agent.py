"""
Tests for the job agent's per-user query derivation and pre-filter removal.

Coverage:
- derive_queries_from_profile: happy path (teacher profile → teaching queries)
- derive_queries_from_profile: engineer profile still produces engineering queries
- derive_queries_from_profile: fallback on LLM failure
- derive_queries_from_profile: fallback on empty profile
- derive_queries_from_profile: strips markdown fences from LLM response
- No java pre-filter: a job listing with no "java" in text is NOT rejected by
  is_search_results_page (verifying the old gate is truly gone)
- is_search_results_page: still catches search-result aggregate pages
- JobScorer scoring model is profile-relative (prompt references "candidate's"
  background, not a hardcoded tech stack)
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from assistant.job.agent import (
    _FALLBACK_QUERIES,
    derive_queries_from_profile,
    is_search_results_page,
)
from assistant.job.models import JobListing
from assistant.job.scorer import _build_prompt, _filter_rules, _scoring_model


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bedrock_client(response_text: str) -> MagicMock:
    """Return a mock bedrock client whose converse() returns *response_text*."""
    client = MagicMock()
    client.converse.return_value = {
        "output": {
            "message": {
                "content": [{"text": response_text}]
            }
        }
    }
    return client


def _make_listing(title: str, description: str = "", company: str = "ACME") -> JobListing:
    return JobListing(
        platform="test",
        title=title,
        company=company,
        location="Tokyo",
        country="Japan",
        job_url="https://example.com/job/1",
        description=description,
    )


# ---------------------------------------------------------------------------
# derive_queries_from_profile
# ---------------------------------------------------------------------------

class TestDeriveQueriesFromProfile(unittest.TestCase):

    def test_teacher_profile_returns_teaching_queries(self):
        """A Japanese teacher's profile should generate teaching-related queries."""
        teacher_profile = (
            "Name: Yuki\n"
            "Education: Tokyo University of Education, graduated March 2013\n"
            "Work experience: Public middle school teacher in Tokyo, April 2013 - present\n"
            "Skills: Classroom management, curriculum development, student assessment"
        )
        llm_response = '["Middle School Teacher", "Education Coordinator", "Curriculum Developer", "School Teacher"]'
        client = _make_bedrock_client(llm_response)

        queries = derive_queries_from_profile(client, "model-id", teacher_profile)

        # Must produce at least one query and none should be Java/backend-specific
        self.assertGreater(len(queries), 0)
        query_strings = [q for q, _ in queries]
        for q in query_strings:
            self.assertNotIn("java", q.lower())
            self.assertNotIn("spring boot", q.lower())
            self.assertNotIn("backend", q.lower())
        # At least one teaching-related query present
        teaching_related = any(
            any(kw in q.lower() for kw in ("teacher", "education", "school", "curriculum"))
            for q in query_strings
        )
        self.assertTrue(teaching_related, f"Expected a teaching query in {query_strings}")

    def test_engineer_profile_returns_engineering_queries(self):
        """An engineer's profile should still generate engineering-relevant queries."""
        engineer_profile = (
            "Senior Java Engineer with 8 years experience in Spring Boot, Kafka, and AWS. "
            "Looking for AI Engineer or Senior Backend Developer roles in fintech."
        )
        llm_response = '["Senior Java Engineer", "Spring Boot Developer", "AI Engineer", "Backend Developer fintech"]'
        client = _make_bedrock_client(llm_response)

        queries = derive_queries_from_profile(client, "model-id", engineer_profile)

        query_strings = [q for q, _ in queries]
        engineering_related = any(
            any(kw in q.lower() for kw in ("java", "engineer", "backend", "developer"))
            for q in query_strings
        )
        self.assertTrue(engineering_related, f"Expected an engineering query in {query_strings}")

    def test_fallback_on_llm_exception(self):
        """When Bedrock raises, fallback queries are returned."""
        client = MagicMock()
        client.converse.side_effect = RuntimeError("Bedrock unavailable")

        queries = derive_queries_from_profile(client, "model-id", "Some profile text")

        self.assertEqual(queries, list(_FALLBACK_QUERIES))

    def test_fallback_on_empty_profile(self):
        """Empty profile short-circuits to fallback without calling Bedrock."""
        client = MagicMock()

        queries = derive_queries_from_profile(client, "model-id", "")

        client.converse.assert_not_called()
        self.assertEqual(queries, list(_FALLBACK_QUERIES))

    def test_fallback_on_whitespace_profile(self):
        """Whitespace-only profile short-circuits to fallback without calling Bedrock."""
        client = MagicMock()

        queries = derive_queries_from_profile(client, "model-id", "   \n\t  ")

        client.converse.assert_not_called()
        self.assertEqual(queries, list(_FALLBACK_QUERIES))

    def test_strips_markdown_fences(self):
        """LLM response wrapped in ```json ... ``` is handled correctly."""
        llm_response = '```json\n["Teacher", "Educator"]\n```'
        client = _make_bedrock_client(llm_response)

        queries = derive_queries_from_profile(client, "model-id", "teacher profile")

        query_strings = [q for q, _ in queries]
        self.assertIn("Teacher", query_strings)
        self.assertIn("Educator", query_strings)

    def test_fallback_on_invalid_json(self):
        """Non-JSON LLM response falls back gracefully."""
        client = _make_bedrock_client("Sorry, I cannot generate queries.")

        queries = derive_queries_from_profile(client, "model-id", "some profile")

        self.assertEqual(queries, list(_FALLBACK_QUERIES))

    def test_fallback_on_empty_json_array(self):
        """Empty JSON array from LLM falls back to defaults."""
        client = _make_bedrock_client("[]")

        queries = derive_queries_from_profile(client, "model-id", "some profile")

        self.assertEqual(queries, list(_FALLBACK_QUERIES))

    def test_city_hints_are_none(self):
        """All derived queries must have None as city hint (location handled at country level)."""
        llm_response = '["Teacher", "Educator", "School Counselor"]'
        client = _make_bedrock_client(llm_response)

        queries = derive_queries_from_profile(client, "model-id", "teacher profile")

        for _, city in queries:
            self.assertIsNone(city)

    def test_bedrock_called_with_temperature_zero(self):
        """Query derivation must use temperature=0 (deterministic)."""
        llm_response = '["Teacher"]'
        client = _make_bedrock_client(llm_response)

        derive_queries_from_profile(client, "test-model", "teacher cv")

        call_kwargs = client.converse.call_args
        inference_config = call_kwargs[1].get("inferenceConfig") or call_kwargs[0][3] if call_kwargs[0] else {}
        # The call is always made with keyword args
        actual_config = client.converse.call_args.kwargs.get("inferenceConfig", {})
        self.assertEqual(actual_config.get("temperature"), 0)

    def test_fallback_queries_are_not_java_specific(self):
        """The fallback queries must not mention Java, Spring Boot, or backend engineering."""
        for query, _ in _FALLBACK_QUERIES:
            self.assertNotIn("java", query.lower())
            self.assertNotIn("spring", query.lower())
            self.assertNotIn("backend", query.lower())
            self.assertNotIn("engineer", query.lower())


# ---------------------------------------------------------------------------
# Pre-filter removal: non-engineering listings must NOT be auto-rejected
# ---------------------------------------------------------------------------

class TestPreFilterRemoval(unittest.TestCase):

    def test_non_java_listing_not_rejected(self):
        """A teaching job with no 'java' in it must NOT be caught by is_search_results_page.

        The old pre_filter_technology_mismatch would have returned True (reject)
        for any listing without 'java'. Verifying that function is gone and
        the only remaining filter is the aggregate-page check.
        """
        listing = _make_listing(
            title="Middle School Teacher",
            description="We are looking for a passionate teacher for grades 7-9. "
                        "Experience in classroom management and curriculum planning required.",
        )
        # The ONLY structural pre-filter remaining is is_search_results_page
        self.assertFalse(is_search_results_page(listing))

    def test_healthcare_listing_not_rejected(self):
        """A nurse / healthcare listing must pass through the pre-filter."""
        listing = _make_listing(
            title="Registered Nurse",
            description="ICU nurse position at Tokyo Medical Centre. "
                        "3+ years of clinical experience required.",
        )
        self.assertFalse(is_search_results_page(listing))

    def test_marketing_listing_not_rejected(self):
        """A marketing role with no 'java' must not be pre-rejected."""
        listing = _make_listing(
            title="Senior Marketing Manager",
            description="Lead our brand campaigns across APAC. Python analytics a bonus.",
        )
        self.assertFalse(is_search_results_page(listing))

    def test_java_listing_still_passes_prefilter(self):
        """An engineering listing with 'java' must also pass the structural pre-filter."""
        listing = _make_listing(
            title="Senior Java Engineer",
            description="Java, Spring Boot, Kafka, AWS experience required.",
        )
        self.assertFalse(is_search_results_page(listing))

    def test_no_pre_filter_technology_mismatch_symbol(self):
        """Confirm pre_filter_technology_mismatch was deleted from the module."""
        import assistant.job.agent as agent_module
        self.assertFalse(
            hasattr(agent_module, "pre_filter_technology_mismatch"),
            "pre_filter_technology_mismatch must be removed from agent.py",
        )


# ---------------------------------------------------------------------------
# is_search_results_page: aggregate/listing pages still caught
# ---------------------------------------------------------------------------

class TestIsSearchResultsPage(unittest.TestCase):

    def test_catches_numeric_jobs_title(self):
        listing = _make_listing(title="1234 jobs found in Tokyo")
        self.assertTrue(is_search_results_page(listing))

    def test_catches_job_offers_prefix(self):
        listing = _make_listing(title="Job Offers - Tokyo 2024")
        self.assertTrue(is_search_results_page(listing))

    def test_catches_job_offers_in(self):
        listing = _make_listing(title="Job offers in Japan")
        self.assertTrue(is_search_results_page(listing))

    def test_does_not_catch_regular_job(self):
        listing = _make_listing(title="Senior Data Scientist")
        self.assertFalse(is_search_results_page(listing))

    def test_does_not_catch_teacher(self):
        listing = _make_listing(title="English Teacher Tokyo")
        self.assertFalse(is_search_results_page(listing))


# ---------------------------------------------------------------------------
# Scorer: scoring model is profile-relative, not tech-stack-hardcoded
# ---------------------------------------------------------------------------

class TestScoringModelIsProfileRelative(unittest.TestCase):

    def test_scoring_model_does_not_hardcode_java(self):
        """The scoring model must not mention Java, Spring Boot, or Kafka."""
        model_text = _scoring_model(["Japan"])
        for term in ("java", "spring boot", "kafka", "python engineer"):
            self.assertNotIn(term, model_text.lower(), f"Found hardcoded term: {term!r}")

    def test_scoring_model_does_not_hardcode_ai_signal(self):
        """The AI/GenAI growth signal must not be the fifth named dimension any more."""
        model_text = _scoring_model(["Japan"])
        # The old hardcoded dimension explicitly mentioned LLM/GenAI/Bedrock/RAG as
        # score-10 items. Verify none of those exact marketing labels are baked in.
        for term in ("llm/genai", "bedrock/rag", "agentic"):
            self.assertNotIn(term, model_text.lower(), f"Found hardcoded AI term: {term!r}")

    def test_scoring_model_references_candidate_profile(self):
        """Scoring dimensions must reference 'candidate' to stay profile-relative."""
        model_text = _scoring_model(["Japan"])
        self.assertIn("candidate", model_text.lower())

    def test_filter_rules_use_generic_field_mismatch(self):
        """Hard-reject must use CLEAR_FIELD_MISMATCH, not TECHNOLOGY_MISMATCH."""
        rules_text = _filter_rules(["Japan"])
        self.assertIn("CLEAR_FIELD_MISMATCH", rules_text)
        self.assertNotIn("TECHNOLOGY_MISMATCH", rules_text)

    def test_filter_rules_do_not_mention_java(self):
        """Filter rules must not hardcode Java as the reference language."""
        rules_text = _filter_rules(["Japan"])
        self.assertNotIn("java", rules_text.lower())

    def test_build_prompt_includes_candidate_profile(self):
        """The assembled scorer prompt must embed the caller's profile text."""
        listing = _make_listing("Teacher", "Seeking an experienced teacher")
        profile = "Yuki: middle school teacher, Tokyo, 13 years experience"
        prompt = _build_prompt(listing, profile, ["Japan"])
        self.assertIn(profile, prompt)

    def test_build_prompt_teacher_profile_not_java_gated(self):
        """A teacher's profile prompt must not reference 'java' anywhere."""
        listing = _make_listing("Home Room Teacher", "Looking for a homeroom teacher")
        profile = "Yuki: public middle school teacher, Tokyo University of Education"
        prompt = _build_prompt(listing, profile, ["Japan"])
        self.assertNotIn("java", prompt.lower())


if __name__ == "__main__":
    unittest.main()
