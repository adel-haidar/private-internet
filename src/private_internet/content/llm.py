"""Shared Bedrock text-generation helper for the content pipelines."""

import os
import time
import logging
import asyncio
from typing import Optional, Tuple

import boto3

from private_internet.config import get_settings

logger = logging.getLogger(__name__)

# Forced tool_choice needs a model that supports it. Mistral/Pixtral do NOT, and
# the Anthropic Claude models on Bedrock require an AWS Marketplace agreement
# (the Haiku 4.5 one expired 2026-06-15 → AccessDenied). Amazon Nova is
# first-party (no agreement), enabled in eu-central-1, and supports forced tools,
# so it is the safe default. Override per-instance with BEDROCK_PULSE_MODEL_ID.
PULSE_MODEL_DEFAULT = "eu.amazon.nova-pro-v1:0"


def bedrock_text_region() -> str:
    """Region for the primary content TEXT model (Amazon Nova Pro) — available
    in eu-central-1, so default to settings.aws_region. Override with
    BEDROCK_TEXT_REGION. (The Nova Canvas image model uses the eu-west-1
    image region instead — see _bedrock_nova_region.)"""
    return os.getenv("BEDROCK_TEXT_REGION") or get_settings().aws_region


def _bedrock_nova_region() -> str:
    """Region for the Nova models (text fallback + Nova Canvas images). Nova is
    not in eu-central-1, so default to the eu-west-1 image region."""
    return os.getenv("BEDROCK_IMAGE_REGION") or "eu-west-1"


async def converse_text(
    user_prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> Tuple[str, dict]:
    """
    Invoke Amazon Nova on Bedrock via the converse API, falling back to the
    configured general model on failure. Returns (text, usage) where usage is
    the converse `usage` dict ({inputTokens, outputTokens, totalTokens}).
    Raises if both models fail.
    """
    # Primary text model: Amazon Nova Pro (first-party, eu-central-1, no
    # Marketplace agreement). Override with BEDROCK_TEXT_MODEL_ID.
    model_id = os.getenv("BEDROCK_TEXT_MODEL_ID", "eu.amazon.nova-pro-v1:0")

    def invoke():
        kwargs = {
            "messages": [{"role": "user", "content": [{"text": user_prompt}]}],
            "inferenceConfig": {"temperature": temperature, "maxTokens": max_tokens},
        }
        if system_prompt:
            kwargs["system"] = [{"text": system_prompt}]
        try:
            # Primary: Amazon Nova Pro in eu-central-1 (bedrock_text_region).
            client = boto3.client("bedrock-runtime", region_name=bedrock_text_region())
            response = client.converse(modelId=model_id, **kwargs)
        except Exception as e:
            logger.warning(f"Primary text model {model_id} failed: {e}. Trying Nova fallback.")
            # Fallback: Nova Lite in eu-west-1.
            fallback_model = os.getenv("BEDROCK_MODEL_ID", "eu.amazon.nova-lite-v1:0")
            client = boto3.client("bedrock-runtime", region_name=_bedrock_nova_region())
            response = client.converse(modelId=fallback_model, **kwargs)
        text = response["output"]["message"]["content"][0]["text"]
        usage = response.get("usage", {})
        return text, usage

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, invoke)


async def converse_tool(
    user_prompt: str,
    tool: dict,
    *,
    system_prompt: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
    model_id: Optional[str] = None,
) -> Tuple[Optional[dict], dict]:
    """
    Invoke an Amazon Nova model on Bedrock with a single FORCED tool (toolChoice).
    Returns (tool_input, usage) where tool_input is the model's structured
    arguments for the tool, or None if no toolUse block came back.

    `tool` is in Anthropic-native shape: {"name", "description", "input_schema"}.
    It is adapted to the Bedrock converse `toolSpec` format here.

    Resilience: unlike a single converse call, the primary model is retried once
    on a transient Bedrock failure (ThrottlingException / ModelErrorException —
    both common under the all-users content fan-out), then falls back to a
    secondary Nova model in the Nova fallback region. Forced toolChoice is
    preserved on every attempt (Nova Lite supports tool use). Raises only if all
    attempts fail — so callers like PULSE/STORIES/ARIA stop losing a whole item
    to one transient model error.
    """
    primary = model_id or os.getenv("BEDROCK_PULSE_MODEL_ID", PULSE_MODEL_DEFAULT)
    # First-party fallback that also supports forced tools. Deliberately NOT
    # BEDROCK_MODEL_ID (that env may carry an unrelated/typo'd value); override
    # here only via BEDROCK_TOOL_FALLBACK_MODEL_ID.
    fallback = os.getenv("BEDROCK_TOOL_FALLBACK_MODEL_ID", "eu.amazon.nova-lite-v1:0")

    def invoke(model: str, region: str):
        client = boto3.client("bedrock-runtime", region_name=region)
        kwargs = {
            "modelId": model,
            "messages": [{"role": "user", "content": [{"text": user_prompt}]}],
            "inferenceConfig": {"temperature": temperature, "maxTokens": max_tokens},
            "toolConfig": {
                "tools": [{"toolSpec": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "inputSchema": {"json": tool["input_schema"]},
                }}],
                "toolChoice": {"tool": {"name": tool["name"]}},
            },
        }
        if system_prompt:
            kwargs["system"] = [{"text": system_prompt}]
        response = client.converse(**kwargs)
        usage = response.get("usage", {})
        for block in response["output"]["message"]["content"]:
            if "toolUse" in block:
                return block["toolUse"]["input"], usage
        return None, usage

    def run():
        # (model, region): retry primary once with backoff (transient errors),
        # then fall back to a second model/region.
        attempts = [
            (primary, bedrock_text_region()),
            (primary, bedrock_text_region()),
            (fallback, _bedrock_nova_region()),
        ]
        last_exc: Optional[Exception] = None
        for i, (model, region) in enumerate(attempts):
            try:
                return invoke(model, region)
            except Exception as e:  # noqa: BLE001 — surface only after all attempts
                last_exc = e
                logger.warning(
                    "converse_tool attempt %d/%d (%s @ %s) failed: %s",
                    i + 1, len(attempts), model, region, e,
                )
                if i < len(attempts) - 1:
                    time.sleep(1.5 * (i + 1))
        raise last_exc  # type: ignore[misc]

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run)
