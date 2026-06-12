import logging
from urllib.parse import urlparse

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

logger = logging.getLogger(__name__)

# Text filters run against the memory REST API (ILIKE on title/tags) — German and
# English, since medical documents are uploaded in both languages.
_MEDICAL_QUERIES = [
    "medical", "Arzt", "Befund", "Blut", "Labor", "Diagnose",
    "medication", "Medikament", "Impf", "doctor", "lab result",
]

# Semantic fallback query for the MCP `search` tool when the REST API is down.
_SEMANTIC_QUERY = (
    "medical records, doctor letters, lab results, blood work, "
    "diagnoses, medications, vaccinations"
)

# Daily summaries are saved by this workflow itself — never feed them back in
# as "medical records" or the analysis becomes self-referential.
_SELF_TITLE_PREFIX = "health summary"

_MAX_TOTAL_CHARS = 16_000


def _api_base_url(mcp_url: str) -> str:
    """'https://host/mcp/mcp' → 'https://host' (same derivation as MemoryClient)."""
    parsed = urlparse(mcp_url)
    return f"{parsed.scheme}://{parsed.netloc}"


async def _list_memories_api(
    base_url: str, token: str, query: str, page_size: int = 100
) -> list[dict]:
    """Paginated REST fetch — deterministic and exhaustive for a given filter."""
    headers = {"Authorization": f"Bearer {token}"}
    all_items: list[dict] = []
    page = 1
    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        while True:
            resp = await client.get(
                f"{base_url}/api/memory",
                params={"page": str(page), "page_size": str(page_size), "q": query},
            )
            resp.raise_for_status()
            data = resp.json()
            all_items.extend(data.get("items", []))
            if page >= data.get("pages", 1):
                break
            page += 1
    return all_items


async def fetch_medical_records(
    mcp_url: str, token: str
) -> list[tuple[str, str]]:
    """Fetch medical-record memories from the MCP memory server.

    Returns a list of (title, content) tuples, deduplicated by title, so the
    workflow can both feed the content to the LLM and report exactly which
    documents informed the analysis.
    """
    base_url = _api_base_url(mcp_url)
    by_title: dict[str, str] = {}

    try:
        for query in _MEDICAL_QUERIES:
            for item in await _list_memories_api(base_url, token, query):
                title = (item.get("title") or "").strip()
                content = item.get("content") or ""
                if not title or not content:
                    continue
                if title.lower().startswith(_SELF_TITLE_PREFIX):
                    continue
                by_title.setdefault(title, content)
    except Exception:
        logger.warning(
            "REST medical-record fetch failed — falling back to MCP semantic search",
            exc_info=True,
        )
        text = await _semantic_search(mcp_url, token, _SEMANTIC_QUERY)
        if text:
            by_title[f"MCP semantic search: {_SEMANTIC_QUERY}"] = text

    # Cap total prompt size — keep whole documents, drop the overflow.
    records: list[tuple[str, str]] = []
    total = 0
    for title, content in by_title.items():
        if total + len(content) > _MAX_TOTAL_CHARS and records:
            logger.info("Medical records truncated at %d docs (%d chars)", len(records), total)
            break
        records.append((title, content))
        total += len(content)

    logger.info("Fetched %d medical-record documents from MCP memory", len(records))
    return records


async def _semantic_search(mcp_url: str, token: str, query: str) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient(headers=headers) as http_client:
            async with streamable_http_client(
                url=mcp_url, http_client=http_client
            ) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool("search", {"query": query})
                    if result.isError or not result.content:
                        return ""
                    return "\n".join(
                        item.text
                        for item in result.content
                        if hasattr(item, "text") and item.text
                    )
    except Exception:
        logger.warning("MCP semantic search failed for %r", query, exc_info=True)
        return ""
