import json
import logging

from assistant.health.models import DailyHealthSummary, SourceAvailability
from assistant.shared.bedrock_retry import invoke_with_tool_retry

logger = logging.getLogger(__name__)

_MAX_INSIGHT_CHARS = 300

HEALTH_ANALYSIS_TOOL = {
    "name": "submit_health_analysis",
    "description": "Submit the daily health analysis as structured data.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "coach_insight": {
                    "type": "string",
                    "description": (
                        "One or two sentences of direct, practical coaching advice, "
                        "max 300 chars. No fluff."
                    ),
                },
                "analysis": {
                    "type": "string",
                    "description": (
                        "Basic health analysis (3–8 sentences). Combine today's device "
                        "metrics (when available) with the medical records context. "
                        "If device data is missing, base the analysis on the medical "
                        "records alone and state the date when new device data is expected."
                    ),
                },
                "reasoning": {
                    "type": "string",
                    "description": (
                        "Plain-text explanation (3–8 sentences) of WHY the analysis says "
                        "what it says: which data sources and documents were used, which "
                        "were missing, and how the conclusions follow from them. "
                        "Be specific — name documents and actual values."
                    ),
                },
            },
            "required": ["coach_insight", "analysis", "reasoning"],
        }
    },
}

_SYSTEM_PROMPT = """
You are a direct, no-nonsense fitness, recovery, and health coach analyzing one
user's daily health data. The user (Adel) has lost weight from 102.8kg toward his
73kg goal with a visible-muscle/lean physique target. He trains regularly at the gym.

You will receive:
- Today's computed device summary (weight, sleep, HRV, resting HR, steps, trend) —
  fields may be null when the scale or Apple Watch has not reported yet
- A list of rule-based flags already detected in Python (facts, do not recompute)
- Data availability per device source, including the date new data is expected
  when a source has not reported for today
- Medical records fetched from Adel's personal memory server (doctor letters,
  lab results, diagnoses, medications), each with its document title

RULES
- NEVER invent metric values. If the scale or watch has no data for today, say so
  and reference the next_expected_date from the availability section instead.
- Ground the analysis in the medical records where relevant (e.g. lab values,
  known conditions, medications) — this is a basic wellness analysis, not a
  diagnosis. Do not give medical advice beyond lifestyle/training guidance.
- The reasoning field is mandatory: explain which documents and data points led
  to each conclusion, and call out data gaps explicitly.
- coach_insight: max 300 characters, specific and actionable
  (e.g. "deload this week", not "consider resting more").

Return only the tool call.
""".strip()


def generate_health_analysis(
    summary: DailyHealthSummary,
    flags: list[str],
    availability: list[SourceAvailability],
    medical_records: list[tuple[str, str]],
    bedrock_client,
    model_id: str,
) -> dict:
    """Single Bedrock call — temperature=0, forced tool_use.

    Returns {coach_insight, analysis, reasoning}.
    """
    payload = {
        "date": summary.date.isoformat(),
        "summary": summary.model_dump(exclude_none=True),
        "flags": flags,
        "data_availability": [a.model_dump() for a in availability],
    }

    parts = [json.dumps(payload, default=str)]
    if medical_records:
        docs = "\n\n".join(
            f"=== DOCUMENT: {title} ===\n{content}"
            for title, content in medical_records
        )
        parts.append(f"<medical-records>\n{docs}\n</medical-records>")
    else:
        parts.append(
            "<medical-records>No medical records found in the memory server.</medical-records>"
        )

    result = invoke_with_tool_retry(
        client=bedrock_client,
        model_id=model_id,
        system_prompt=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": [{"text": "\n\n".join(parts)}]}],
        tool_spec=HEALTH_ANALYSIS_TOOL,
        max_tokens=2048,
        max_retries=2,
    )

    insight = str(result.get("coach_insight", "")).strip()
    # Hard cap at 300 chars — truncate at last sentence boundary if possible
    if len(insight) > _MAX_INSIGHT_CHARS:
        truncated = insight[:_MAX_INSIGHT_CHARS]
        last_dot = truncated.rfind(".")
        if last_dot > _MAX_INSIGHT_CHARS // 2:
            truncated = truncated[:last_dot + 1]
        insight = truncated.strip()

    return {
        "coach_insight": insight,
        "analysis": str(result.get("analysis", "")).strip(),
        "reasoning": str(result.get("reasoning", "")).strip(),
    }
