"""Shared Bedrock text-generation helper for the content pipelines."""

import os
import logging
import asyncio
from typing import Optional, Tuple

import boto3

from private_internet.config import get_settings

logger = logging.getLogger(__name__)


async def converse_text(
    user_prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> Tuple[str, dict]:
    """
    Invoke Claude Haiku on Bedrock via the converse API, falling back to the
    configured general model on failure. Returns (text, usage) where usage is
    the converse `usage` dict ({inputTokens, outputTokens, totalTokens}).
    Raises if both models fail.
    """
    settings = get_settings()
    model_id = os.getenv("BEDROCK_HAIKU_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")

    def invoke():
        client = boto3.client("bedrock-runtime", region_name=settings.aws_region)
        kwargs = {
            "messages": [{"role": "user", "content": [{"text": user_prompt}]}],
            "inferenceConfig": {"temperature": temperature, "maxTokens": max_tokens},
        }
        if system_prompt:
            kwargs["system"] = [{"text": system_prompt}]
        try:
            response = client.converse(modelId=model_id, **kwargs)
        except Exception as e:
            logger.warning(f"Bedrock Haiku invocation failed: {e}. Trying fallback model.")
            fallback_model = os.getenv("BEDROCK_MODEL_ID", "eu.amazon.nova-2-lite-v1:0")
            response = client.converse(modelId=fallback_model, **kwargs)
        text = response["output"]["message"]["content"][0]["text"]
        usage = response.get("usage", {})
        return text, usage

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, invoke)
