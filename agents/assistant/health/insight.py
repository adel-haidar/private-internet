import json
import logging

from assistant.health.models import DailyHealthSummary
from assistant.shared.bedrock_retry import invoke_with_tool_retry

logger = logging.getLogger(__name__)

_MAX_CHARS = 300

HEALTH_INSIGHT_TOOL = {
    "name": "submit_health_insight",
    "description": "Submit a single coaching insight based on the health summary and flags.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "coach_insight": {
                    "type": "string",
                    "description": (
                        "One or two sentences, max 300 chars. "
                        "Direct, practical, no fluff."
                    ),
                }
            },
            "required": ["coach_insight"],
        }
    },
}

_SYSTEM_PROMPT = """
You are a direct, no-nonsense fitness and recovery coach analyzing one user's daily
health data summary. The user (Adel) has lost weight from 102.8kg to roughly his
current weight, targeting 73kg with a visible-muscle/lean physique. He trains regularly
at the gym.

You will receive:
- Today's computed health summary (weight, sleep, HRV, resting HR, steps, trend)
- A list of rule-based flags already detected in Python (do not recompute these —
  they are facts, not suggestions)

Your job: write ONE or TWO sentences of direct, practical coaching advice based on
the flags and trends. Be specific (e.g. "deload this week" not "consider resting more").
No greetings, no filler, no repeating the numbers back. Max 300 characters.
Return only the tool call.
""".strip()


def generate_health_insight(
    summary: DailyHealthSummary,
    flags: list[str],
    bedrock_client,
    model_id: str,
) -> str:
    """Single Bedrock call — temperature=0, forced tool_use. Returns coach_insight string."""
    user_content = json.dumps({
        "date": summary.date.isoformat(),
        "summary": summary.model_dump(exclude_none=True),
        "flags": flags,
    }, default=str)

    result = invoke_with_tool_retry(
        client=bedrock_client,
        model_id=model_id,
        system_prompt=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": [{"text": user_content}]}],
        tool_spec=HEALTH_INSIGHT_TOOL,
        max_tokens=512,
        max_retries=2,
    )

    insight: str = result.get("coach_insight", "")

    # Hard cap at 300 chars — truncate at last sentence boundary if possible
    if len(insight) > _MAX_CHARS:
        truncated = insight[:_MAX_CHARS]
        last_dot = truncated.rfind(".")
        if last_dot > _MAX_CHARS // 2:
            truncated = truncated[:last_dot + 1]
        insight = truncated

    return insight.strip()
