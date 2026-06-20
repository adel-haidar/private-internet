import os
import json
import logging
import asyncio
from dataclasses import dataclass
from typing import List, Tuple

import google.generativeai as genai
from google.generativeai import protos
from private_internet.content.topic_intelligence import TopicCandidate

logger = logging.getLogger(__name__)

# Relevance scoring via Gemini grounding metadata:
# Each grounding chunk = one web source the model actually used.  More sources
# = stronger signal that the topic is real, current, and well-documented.
# We map chunk count → [0.5, 1.0] with a sigmoid-like piecewise scale:
#   0 chunks  → 0.6 (conservative default; topic still came from the user's brain)
#   1 chunk   → 0.65
#   2 chunks  → 0.72
#   3 chunks  → 0.80
#   4 chunks  → 0.88
#   ≥5 chunks → 0.95
_GROUNDING_SCORE = [0.6, 0.65, 0.72, 0.80, 0.88, 0.95]


@dataclass
class ResearchResult:
    url: str
    title: str
    summary: str


class WebResearchService:
    def __init__(self):
        # Configure Gemini API key from environment variable
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY environment variable is not set.")
        genai.configure(api_key=api_key)

        # Configure the generative model with Google Search grounding enabled.
        # Note: gemini-2.0 models require the `google_search` tool — the API
        # rejects the older `google_search_retrieval` (1.5-only). The legacy
        # SDK can't build `google_search` from a dict, so use the proto directly.
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            tools=[protos.Tool(google_search=protos.Tool.GoogleSearch())]
        )
        # Grounding chunk count from the most recent research_topic() call.
        # Used by assess_topic_relevance() to derive a relevance weight without
        # a second LLM call.  Keyed per-instance so concurrent callers each get
        # their own service object (topic_job creates one per job run).
        self._last_grounding_count: int = 0

    async def research_topic(self, topic: TopicCandidate) -> List[ResearchResult]:
        """
        Research the topic using Gemini 2.0 Flash with Google Search Grounding.
        Returns a list of ResearchResult objects.
        """
        prompt = (
            f"Research the topic: '{topic.name}'\n\n"
            "Find:\n"
            "1. 3–5 authoritative articles or sources published in the last 6 months\n"
            "2. For each: title, URL, and a 2-sentence neutral summary\n"
            "3. Key statistics or data points if available\n"
            "4. Any controversy or opposing viewpoints\n\n"
            "Output ONLY a JSON array of objects:\n"
            '[{ "url": str, "title": str, "summary": str }]\n'
            "Do not output any introductory or concluding text, nor markdown fences (like ```json). Just the raw JSON."
        )

        loop = asyncio.get_event_loop()
        
        def generate_content():
            return self.model.generate_content(prompt)

        try:
            response = await loop.run_in_executor(None, generate_content)
        except Exception as e:
            logger.error(f"Gemini content generation failed: {e}", exc_info=True)
            return []

        response_text = response.text.strip() if response and hasattr(response, "text") else ""

        # Clean JSON markdown blocks if the model included them
        clean_text = response_text
        if clean_text.startswith("```"):
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            else:
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()

        results = []
        try:
            if clean_text:
                data_list = json.loads(clean_text)
                for item in data_list:
                    results.append(ResearchResult(
                        url=item.get("url", ""),
                        title=item.get("title", ""),
                        summary=item.get("summary", "")
                    ))
        except Exception as e:
            logger.warning(f"Failed to parse JSON text from Gemini research: '{response_text}'. Error: {e}")

        # Parse grounding metadata from response candidates
        grounding_sources: List[Tuple[str, str]] = []
        try:
            if response and hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "grounding_metadata") and candidate.grounding_metadata:
                    metadata = candidate.grounding_metadata
                    if hasattr(metadata, "grounding_chunks") and metadata.grounding_chunks:
                        for chunk in metadata.grounding_chunks:
                            if hasattr(chunk, "web") and chunk.web:
                                uri = chunk.web.uri
                                title = chunk.web.title
                                if uri:
                                    grounding_sources.append((uri, title))
        except Exception as e:
            logger.warning(f"Failed to parse grounding metadata: {e}")

        # Persist chunk count so assess_topic_relevance() can read it without a
        # second LLM call.
        self._last_grounding_count = len(grounding_sources)
        logger.debug(
            f"research_topic: {self._last_grounding_count} grounding chunk(s) "
            f"for topic '{topic.name}'"
        )

        # Fallback: if we failed to get structured results from the text, but have grounding URLs, use them!
        if not results and grounding_sources:
            logger.info("Using fallback grounding metadata sources for research results")
            for url, title in grounding_sources:
                # Deduplicate by url
                if not any(r.url == url for r in results):
                    results.append(ResearchResult(
                        url=url,
                        title=title or "Cited Source",
                        summary=f"Resource cited during Google Search Grounding for topic: '{topic.name}'."
                    ))

        return results

    async def assess_topic_relevance(self, topic: TopicCandidate, research: List[ResearchResult]) -> float:
        """
        Returns a relevance weight (0.0–1.0) derived from Gemini's Google Search
        grounding metadata — specifically the number of grounding chunks returned
        by the preceding research_topic() call.

        This replaces a redundant second Bedrock LLM call: Gemini already signals
        how well a topic is documented on the live web through the number of web
        sources it actually cited.  More grounding chunks → higher weight.

        Scoring table (see _GROUNDING_SCORE at module level):
          0 chunks → 0.60  (topic came from user's brain; conservative default)
          1 chunk  → 0.65
          2 chunks → 0.72
          3 chunks → 0.80
          4 chunks → 0.88
          ≥5 chunks → 0.95

        If research_topic() was not called first (e.g. unit tests that call this
        method in isolation) the chunk count defaults to 0 → 0.60 weight, which
        is a safe, conservative fallback that keeps the topic in the feed.
        """
        chunk_count = self._last_grounding_count
        weight = _GROUNDING_SCORE[min(chunk_count, len(_GROUNDING_SCORE) - 1)]
        logger.info(
            f"assess_topic_relevance: topic='{topic.name}', "
            f"grounding_chunks={chunk_count}, weight={weight:.2f} "
            f"(derived from Gemini grounding; no Bedrock call)"
        )
        return weight
