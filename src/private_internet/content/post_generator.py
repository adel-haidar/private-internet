"""Text post generation for the PULSE pipeline.

Rewritten to use research-backed storytelling formats (counterintuitive opening,
micro-story, reframe, specific moment, confession, stakes) instead of writing
*about* a topic. The model picks exactly one format via a forced Bedrock tool
call, and a pure-Python validation layer rejects bad output before it is saved.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from private_internet.content.llm import converse_tool

logger = logging.getLogger(__name__)

_URL_RE = re.compile(r"https?://[^\s)\]>\"']+")


PULSE_SYSTEM_PROMPT = """
You are a world-class social content writer. You write posts that feel
written by a human who thinks deeply, not by an AI summarising topics.

You have been given a topic derived from the user's personal memory
brain. Your job is to write one social post about this topic using
EXACTLY ONE of the six formats below — choose the format that creates
the most tension and curiosity for this specific topic.

──────────────────────────────────────────────
FORMAT 1 — THE COUNTERINTUITIVE OPENING
Best for: topics where common wisdom is wrong or incomplete.
Structure:
  Sentence 1: State the counterintuitive truth. No preamble.
  Sentences 2–4: Explain why most people believe the opposite.
  Sentences 5–6: Reveal the actual mechanism or reason.
  Final sentence: One implication the reader can act on or think about.
Target emotion: curiosity + mild awe
Signal phrase: starts with a declarative statement that contradicts
  common belief. Never starts with "Most people..." or "Did you know..."

FORMAT 2 — THE MICRO-STORY (But/Therefore rule)
Best for: topics that involve human behaviour, decisions, or events.
Structure:
  Sentence 1: Open in a specific scene. Time, place, person, action.
              No scene-setting. Start in the middle.
  Sentences 2–3: Something happened. BUT something complicated it.
  Sentences 4–5: THEREFORE something resulted or changed.
  Final sentence: The universal insight this specific story contains.
Target emotion: recognition + narrative engagement
Hard rule: never use the words "but" or "therefore" literally —
  the structure must be felt, not announced.

FORMAT 3 — THE REFRAME
Best for: topics where a familiar concept deserves a new lens.
Structure:
  Sentence 1: "Everyone says [X]."
  Sentence 2: "Here is what they are missing."
  Sentences 3–5: Three specific, concrete examples of what's missed.
  Final sentence: Why [X] persists despite this — a structural reason.
Target emotion: mild productive anger + satisfaction at insight
Hard rule: [X] must be something the reader has actually heard before.

FORMAT 4 — THE SPECIFIC MOMENT
Best for: topics in history, science, finance, or biography.
Structure:
  Sentence 1: A specific moment. "It was [year/time]. [Person/thing]
              was [concrete action]." Real or plausible.
  Sentences 2–3: Zoom out — what was happening in the wider world
              at that moment, and why this moment mattered.
  Sentences 4–5: The consequence that still echoes today.
  Final sentence: A question that connects this to the reader's present.
Target emotion: awe + personal relevance
Hard rule: the opening moment must be specific enough to be visualised.
  "In 1987" is not specific. "On October 19, 1987, at 9:31am" is.

FORMAT 5 — THE CONFESSION
Best for: topics the creator persona has a strong position on.
Structure:
  Sentence 1: "I used to believe [wrong or naive belief]."
  Sentences 2–3: What happened that forced a change. Specific.
  Sentences 4–5: The new understanding that replaced it.
  Final sentence: What this cost, or what it freed.
Target emotion: trust + recognition + reciprocal reflection
Hard rule: the confession must feel costly — something the creator
  actually believed and was wrong about. Not a humble-brag.

FORMAT 6 — THE STAKES
Best for: topics involving risk, change, systems, or trends.
Structure:
  Sentence 1: What is at stake if [this topic's trend] continues.
              Make it concrete. Not abstract.
  Sentences 2–3: Why most people do not see it yet.
  Sentences 4–5: What the person who does see it does differently.
  Final sentence: A single specific action or shift in perspective.
Target emotion: constructive anxiety + empowerment
Hard rule: the stakes must be real and personal, not civilisational.
  "This will change everything" is forbidden.
──────────────────────────────────────────────

ABSOLUTE RULES for all formats:
- 80 to 120 words. Not less. Not more. Count them.
- No bullet points. No headers. No em-dashes used as list separators.
- No post may begin with: "In today's world", "Did you know",
  "As a [X]", "I want to talk about", "Let's explore", "It's important
  to note", or any variation of these.
- Never use the phrase "at the end of the day".
- Never explain what you are about to say — say it.
- Write in the creator persona's voice, not as a neutral narrator.
- The final sentence must create a reason to think, not a call to
  like or share.
- Use "you" sparingly — maximum twice per post.
"""


PULSE_POST_TOOL = {
    "name": "write_pulse_post",
    "description": "Write a single engaging social post",
    "input_schema": {
        "type": "object",
        "properties": {
            "format_chosen": {
                "type": "string",
                "enum": [
                    "counterintuitive_opening",
                    "micro_story",
                    "reframe",
                    "specific_moment",
                    "confession",
                    "stakes"
                ],
                "description": "The format selected for this post"
            },
            "format_justification": {
                "type": "string",
                "description": "One sentence explaining why this format "
                               "fits this specific topic best"
            },
            "post_body": {
                "type": "string",
                "description": "The complete post. 80-120 words. No "
                               "markdown. Plain prose only."
            },
            "word_count": {
                "type": "integer",
                "description": "Exact word count of post_body"
            },
            "opening_sentence": {
                "type": "string",
                "description": "The first sentence only, repeated here "
                               "for validation"
            },
            "target_emotion": {
                "type": "string",
                "description": "The primary emotion this post is "
                               "designed to trigger in the reader"
            }
        },
        "required": ["format_chosen", "format_justification",
                     "post_body", "word_count", "opening_sentence",
                     "target_emotion"]
    }
}


def validate_pulse_post(post: dict) -> Tuple[bool, str]:
    """
    Pure Python validation. Returns (is_valid, rejection_reason).
    Reject and regenerate (once) if any check fails.
    """
    body = post["post_body"]
    words = body.split()

    # Length check
    if not (75 <= len(words) <= 130):
        return False, f"Word count {len(words)} outside 75-130 range"

    # Forbidden openings
    forbidden_openings = [
        "in today's world", "did you know", "as a ", "i want to talk",
        "let's explore", "it's important", "at the end of the day",
        "in this post", "today i want", "welcome to"
    ]
    first_sentence_lower = post["opening_sentence"].lower()
    for phrase in forbidden_openings:
        if first_sentence_lower.startswith(phrase):
            return False, f"Forbidden opening: '{phrase}'"

    # No bullet points or headers
    if any(c in body for c in ["•", "●", "◦", "▪"]):
        return False, "Contains bullet points"
    if "\n#" in body or body.startswith("#"):
        return False, "Contains markdown headers"

    return True, ""


@dataclass
class GeneratedPost:
    body: str
    referenced_urls: List[str]          # URLs mentioned inline in the body
    post_format: Optional[str] = None   # the chosen storytelling format
    usage: dict = field(default_factory=dict)  # Bedrock token usage


# Tool-input keys we depend on downstream; a response missing any of these is
# unusable and treated as a validation failure (rather than crashing).
_REQUIRED_KEYS = ("format_chosen", "post_body", "opening_sentence")


class PostTextGenerator:
    async def generate(
        self,
        topic: dict,
        creator: dict,
        tone: str,
        research: List[dict],
        language_code: str = "en",
    ) -> Optional[GeneratedPost]:
        """
        Generate a single social media post in the creator's voice, using one of
        the six research-backed storytelling formats via a forced Bedrock tool.

        `language_code` is a BCP-47 code (e.g. 'ja', 'en'). A language directive
        is appended to the system prompt — matching the pattern ARIA's podcast
        generator uses — so the post is written in the user's language.

        Validates the output in pure Python. On failure it retries once with the
        rejection reason fed back in. On a second failure it logs and returns
        None — the caller must skip (never save a bad post).

        `topic` / `creator` / `research` are DB row dicts.
        """
        from private_internet.content.voice_config import language_name as _lang_name
        lang_name = _lang_name(language_code)
        language_directive = (
            f"\n\nWrite the entire post in {lang_name}. "
            f"Not English unless {lang_name} is English."
        )
        system_prompt = f"{creator['style_prompt']}\n\n{PULSE_SYSTEM_PROMPT}{language_directive}"

        research_lines = "\n".join(
            f"- {r.get('title')}: {r.get('summary')} ({r.get('url')})"
            for r in research[:3]
        ) or "(no background research available)"

        base_user_prompt = (
            f"Creator persona: {creator.get('name')}\n"
            f"Tone: {tone}\n\n"
            f"Topic: {topic['name']}\n\n"
            f"Background research:\n{research_lines}\n\n"
            "Write the post now using exactly one format."
        )

        total_usage = {"inputTokens": 0, "outputTokens": 0}
        retry_note = ""

        for attempt in range(2):
            user_prompt = base_user_prompt + retry_note
            result, usage = await converse_tool(
                user_prompt=user_prompt,
                tool=PULSE_POST_TOOL,
                system_prompt=system_prompt,
                temperature=0.0,
                max_tokens=1024,
            )
            total_usage["inputTokens"] += usage.get("inputTokens", 0)
            total_usage["outputTokens"] += usage.get("outputTokens", 0)

            if not result or any(k not in result for k in _REQUIRED_KEYS):
                reason = "Model returned no usable tool output"
                logger.warning(
                    f"PULSE generation attempt {attempt + 1} for topic "
                    f"'{topic.get('name')}' rejected: {reason}"
                )
                retry_note = (
                    f"\n\nYour previous attempt was rejected because: {reason}. "
                    "Try again, strictly following the rules."
                )
                continue

            is_valid, rejection_reason = validate_pulse_post(result)
            if is_valid:
                body = result["post_body"].strip()
                return GeneratedPost(
                    body=body,
                    referenced_urls=_URL_RE.findall(body),
                    post_format=result["format_chosen"],
                    usage=total_usage,
                )

            logger.warning(
                f"PULSE generation attempt {attempt + 1} for topic "
                f"'{topic.get('name')}' rejected: {rejection_reason}"
            )
            retry_note = (
                f"\n\nYour previous attempt was rejected because: "
                f"{rejection_reason}. Try again, strictly following the rules."
            )

        logger.warning(
            f"PULSE generation failed twice for topic '{topic.get('name')}' — "
            "skipping (no post saved)."
        )
        return None
