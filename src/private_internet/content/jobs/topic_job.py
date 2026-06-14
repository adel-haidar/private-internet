import asyncio
import logging
from private_internet.database import _connect
from private_internet.content.topic_intelligence import MCPMemoryReader, TopicStorageService
from private_internet.content.research_service import WebResearchService

logger = logging.getLogger(__name__)


async def run_topic_intelligence_job(*, user_id: str):
    """
    Full pipeline for a single user — every read and write is user-scoped.
    # MUST SCOPE BY USER

    1. MCPMemoryReader.fetch_recent_memories()
    2. MCPMemoryReader.extract_topic_candidates()
    3. For each candidate (parallel with asyncio.gather):
       a. Check for duplicates (last 14 days)
       b. WebResearchService.research_topic()
       c. WebResearchService.assess_topic_relevance()
       d. TopicStorageService.save_topic()
    4. Log summary: N topics added, N skipped (duplicate), N failed
    """
    assert user_id is not None, "user_id must be set before any content operation"
    logger.info(f"[user:{user_id[:8]}] Starting run_topic_intelligence_job")

    reader = MCPMemoryReader()
    research_service = WebResearchService()
    storage_service = TopicStorageService()

    # 1-2. Discover candidate topics by clustering the user's memory embeddings
    #      locally and naming each cluster/intersection from keywords only.
    #      Bedrock receives keyword sets, never raw memory text.
    try:
        candidates = await reader.extract_topic_candidates_clustered(user_id=user_id)
        logger.info(f"Discovered {len(candidates)} topic candidates: {[c.name for c in candidates]}")
    except Exception as e:
        logger.error(f"Failed to discover topic candidates: {e}", exc_info=True)
        return

    if not candidates:
        logger.info("No topic candidates discovered. Topic intelligence run finished with 0 topics.")
        return

    # 3. Process each candidate (parallel research, relevance score, and DB save)
    added = 0
    skipped = 0
    failed = 0

    async def process_candidate(candidate):
        nonlocal added, skipped, failed
        
        # Each task gets its own connection to avoid cross-coroutine connection state issues
        conn = None
        try:
            conn = _connect()
            
            # Check for duplication (14 days threshold)
            is_dup = storage_service.is_duplicate(conn, candidate.slug, threshold_days=14, user_id=user_id)
            if is_dup:
                logger.info(f"Skipping topic candidate '{candidate.name}' - duplicate detected in the last 14 days.")
                skipped += 1
                return

            # Research (web-grounded) is best-effort ENRICHMENT — a topic extracted
            # from the user's own memories is still worth generating content about
            # even if web research is unavailable (e.g. no/invalid Gemini key). Don't
            # let a research failure throw away the topic.
            research_results = await research_service.research_topic(candidate)
            if research_results:
                weight = await research_service.assess_topic_relevance(candidate, research_results)
            else:
                logger.info(f"No research for '{candidate.name}' — saving topic without research links.")
                research_results = []
                weight = 0.6

            # Store the topic (+ any research links)
            storage_service.save_topic(conn, candidate, research_results, weight, user_id=user_id)
            logger.info(f"Successfully added/updated topic '{candidate.name}' with weight {weight:.2f}")
            added += 1

        except Exception as e:
            logger.error(f"Error processing topic candidate '{candidate.name}': {e}", exc_info=True)
            failed += 1
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    # Run in parallel
    await asyncio.gather(*(process_candidate(candidate) for candidate in candidates))

    logger.info(
        f"Topic intelligence job completed. Summary - Added: {added}, Skipped (Duplicate): {skipped}, Failed: {failed}"
    )
