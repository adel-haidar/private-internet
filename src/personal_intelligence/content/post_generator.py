"""Text post generation for the PULSE pipeline (Phase 3, Task 2)."""

import re
import logging
from dataclasses import dataclass, field
from typing import List

from personal_intelligence.content.llm import converse_text

logger = logging.getLogger(__name__)

_URL_RE = re.compile(r"https?://[^\s)\]>\"']+")


@dataclass
class GeneratedPost:
    body: str
    referenced_urls: List[str]   # URLs mentioned inline in the body
    usage: dict = field(default_factory=dict)  # Bedrock token usage


class PostTextGenerator:
    async def generate(
        self,
        topic: dict,
        creator: dict,
        tone: str,
        research: List[dict],
    ) -> GeneratedPost:
        """
        Generate a single social media post in the creator's voice.
        `topic` / `creator` / `research` are DB row dicts.
        """
        system_prompt = (
            f"{creator['style_prompt']}\n\n"
            "You are writing a single social media post.\n"
            f"Tone: {tone}.\n"
            "Keep it under 300 words.\n"
            "You may include 1–2 relevant links from the research provided.\n"
            "Do NOT add hashtags unless they feel natural for this creator's voice.\n"
            "Output ONLY the post text, no labels or preamble."
        )

        research_lines = "\n".join(
            f"- {r.get('title')}: {r.get('summary')} ({r.get('url')})"
            for r in research[:3]
        )
        user_prompt = (
            f"Write a post about: {topic['name']}\n\n"
            f"Background research:\n{research_lines}\n\n"
            "Write the post now."
        )

        text, usage = await converse_text(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=1024,
        )
        body = text.strip()
        referenced_urls = _URL_RE.findall(body)
        return GeneratedPost(body=body, referenced_urls=referenced_urls, usage=usage)
