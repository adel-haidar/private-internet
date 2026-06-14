"""fal.ai video generation (Kling) for SIGNAL section clips.

Replaces the legacy still-image + Ken-Burns slides with a real generated video
clip per section. Uses fal's async queue API: submit a job, poll until COMPLETE,
then download the resulting mp4 bytes. Kling produces short (5/10s) silent clips;
the assembler loops a clip under the section's narration to fill its duration.

Callers keep a slide fallback, so an unfunded balance or any error degrades to a
gradient slide rather than failing the whole video.
"""

import asyncio

import httpx

from private_internet.config import get_settings

_QUEUE = "https://queue.fal.run/"
_POLL_INTERVAL_S = 5
_MAX_POLLS = 120  # ~10 min ceiling per clip


async def generate_video_clip(
    prompt: str,
    *,
    duration: str = "5",
    aspect_ratio: str = "16:9",
) -> bytes:
    """Generate one short video clip from a text prompt; return mp4 bytes. Raises on failure."""
    s = get_settings()
    if not s.fal_api_key:
        raise RuntimeError("FAL_AI_API_KEY not configured")

    model = s.fal_video_model
    headers = {"Authorization": f"Key {s.fal_api_key}", "Content-Type": "application/json"}
    body = {"prompt": prompt, "duration": duration, "aspect_ratio": aspect_ratio}

    async with httpx.AsyncClient(timeout=120) as client:
        # 1. Submit to the queue.
        sub = await client.post(f"{_QUEUE}{model}", json=body, headers=headers)
        sub.raise_for_status()
        job = sub.json()
        req_id = job["request_id"]
        status_url = job.get("status_url") or f"{_QUEUE}{model}/requests/{req_id}/status"
        response_url = job.get("response_url") or f"{_QUEUE}{model}/requests/{req_id}"

        # 2. Poll until done.
        for _ in range(_MAX_POLLS):
            await asyncio.sleep(_POLL_INTERVAL_S)
            st = await client.get(status_url, headers=headers)
            st.raise_for_status()
            status = st.json().get("status")
            if status == "COMPLETED":
                break
            if status in ("FAILED", "ERROR"):
                raise RuntimeError(f"fal video job failed: {str(st.json())[:200]}")
        else:
            raise RuntimeError("fal video job timed out")

        # 3. Fetch result + download the mp4.
        res = await client.get(response_url, headers=headers)
        res.raise_for_status()
        url = (res.json().get("video") or {}).get("url")
        if not url:
            raise RuntimeError(f"fal video: no url in result {str(res.json())[:200]}")
        vid = await client.get(url)
        vid.raise_for_status()
        return vid.content
