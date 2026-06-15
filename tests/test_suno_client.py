"""Suno client unit tests — no network, no DB, no pydub/ffmpeg.

All HTTP leaves (_post / _get / _download_audio) and duration measurement
(_duration / generate_track) are mocked, so these run fully offline.

Coverage:
  - successful generation + polling (PENDING → SUCCESS)
  - submit payload correctness (instrumental vs lyrics)
  - job failure status → SunoGenerationError
  - poll timeout (MAX_POLL_ATTEMPTS exceeded)
  - min-duration: pass on first try, retry-then-pass, retry-then-fail
  - _extract_audio_url helper
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from private_internet.content.aria import suno_client as sc
from private_internet.content.aria.suno_client import (
    SunoClient,
    SunoGenerationError,
    SunoResult,
    _extract_audio_url,
)

MODULE = "private_internet.content.aria.suno_client"


def _client() -> SunoClient:
    # Explicit args so the test never depends on env/.env contents.
    return SunoClient(
        api_key="test-key",
        base_url="https://api.sunoapi.org",
        model="V4_5",
        callback_url="https://example.com/cb",
    )


def _no_sleep():
    """Patch the 10s poll interval to a no-op so tests are instant."""
    return patch(f"{MODULE}.asyncio.sleep", new=AsyncMock())


# ── successful generation + polling ───────────────────────────────────────────


def test_generate_track_success_after_pending():
    client = _client()
    client._post = AsyncMock(
        return_value={"code": 200, "msg": "success", "data": {"taskId": "task-1"}}
    )
    client._get = AsyncMock(
        side_effect=[
            {"data": {"status": "PENDING"}},
            {"data": {"status": "FIRST_SUCCESS"}},
            {
                "data": {
                    "status": "SUCCESS",
                    "response": {"sunoData": [{"audioUrl": "https://cdn/a.mp3"}]},
                }
            },
        ]
    )
    client._download_audio = AsyncMock(return_value=b"MP3BYTES")

    with _no_sleep():
        result = asyncio.run(
            client.generate_track(prompt="", style="ambient piano", title="Calm")
        )

    assert isinstance(result, SunoResult)
    assert result.audio == b"MP3BYTES"
    assert result.task_id == "task-1"
    client._download_audio.assert_awaited_once_with("https://cdn/a.mp3")
    assert client._get.await_count == 3  # polled until SUCCESS


def test_submit_payload_instrumental_omits_prompt():
    client = _client()
    captured = {}

    async def fake_post(path, payload):
        captured["path"] = path
        captured["payload"] = payload
        return {"code": 200, "data": {"taskId": "t"}}

    client._post = fake_post
    client._get = AsyncMock(
        return_value={
            "data": {
                "status": "SUCCESS",
                "response": {"sunoData": [{"audioUrl": "u"}]},
            }
        }
    )
    client._download_audio = AsyncMock(return_value=b"x")

    with _no_sleep():
        asyncio.run(client.generate_track(prompt="ignored lyrics", style="s", title="T"))

    assert captured["path"] == "/api/v1/generate"
    p = captured["payload"]
    assert p["customMode"] is True
    assert p["instrumental"] is True
    assert p["model"] == "V4_5"
    assert p["style"] == "s"
    assert p["title"] == "T"
    assert p["callBackUrl"] == "https://example.com/cb"
    assert "prompt" not in p  # instrumental → lyrics dropped


def test_submit_payload_vocal_includes_lyrics_as_prompt():
    client = _client()
    captured = {}

    async def fake_post(path, payload):
        captured["payload"] = payload
        return {"code": 200, "data": {"taskId": "t"}}

    client._post = fake_post
    client._get = AsyncMock(
        return_value={
            "data": {"status": "SUCCESS", "response": {"sunoData": [{"audioUrl": "u"}]}}
        }
    )
    client._download_audio = AsyncMock(return_value=b"x")

    with _no_sleep():
        asyncio.run(
            client.generate_track(
                prompt="la la la", style="pop", title="T", instrumental=False
            )
        )

    assert captured["payload"]["instrumental"] is False
    assert captured["payload"]["prompt"] == "la la la"


# ── failure + timeout ─────────────────────────────────────────────────────────


def test_job_failure_raises():
    client = _client()
    client._post = AsyncMock(return_value={"code": 200, "data": {"taskId": "t"}})
    client._get = AsyncMock(return_value={"data": {"status": "GENERATE_AUDIO_FAILED"}})

    with _no_sleep(), pytest.raises(SunoGenerationError, match="GENERATE_AUDIO_FAILED"):
        asyncio.run(client.generate_track(prompt="", style="s", title="T"))


def test_submit_non_200_raises():
    client = _client()
    client._post = AsyncMock(return_value={"code": 429, "msg": "rate limited"})

    with _no_sleep(), pytest.raises(SunoGenerationError, match="rejected"):
        asyncio.run(client.generate_track(prompt="", style="s", title="T"))


def test_poll_timeout_raises():
    client = _client()
    client._post = AsyncMock(return_value={"code": 200, "data": {"taskId": "t"}})
    client._get = AsyncMock(return_value={"data": {"status": "PENDING"}})

    with _no_sleep(), patch.object(sc, "MAX_POLL_ATTEMPTS", 3), pytest.raises(
        SunoGenerationError, match="timed out"
    ):
        asyncio.run(client.generate_track(prompt="", style="s", title="T"))
    assert client._get.await_count == 3


def test_success_without_audio_url_raises():
    client = _client()
    client._post = AsyncMock(return_value={"code": 200, "data": {"taskId": "t"}})
    client._get = AsyncMock(
        return_value={"data": {"status": "SUCCESS", "response": {"sunoData": []}}}
    )

    with _no_sleep(), pytest.raises(SunoGenerationError, match="no audioUrl"):
        asyncio.run(client.generate_track(prompt="", style="s", title="T"))


# ── min-duration enforcement + retry ──────────────────────────────────────────


def test_min_duration_pass_first_try():
    client = _client()
    client.generate_track = AsyncMock(return_value=SunoResult(b"good", "t1"))
    client._duration = AsyncMock(return_value=180.0)

    result = asyncio.run(
        client.generate_with_min_duration(prompt="", style="s", title="T")
    )

    assert result.task_id == "t1"
    assert result.duration_seconds == 180.0
    assert client.generate_track.await_count == 1


def test_min_duration_retry_then_pass():
    client = _client()
    client.generate_track = AsyncMock(
        side_effect=[SunoResult(b"short", "t1"), SunoResult(b"long", "t2")]
    )
    client._duration = AsyncMock(side_effect=[90.0, 200.0])

    result = asyncio.run(
        client.generate_with_min_duration(prompt="", style="ambient", title="T")
    )

    assert result.task_id == "t2"
    assert result.duration_seconds == 200.0
    assert client.generate_track.await_count == 2
    # Retry appends the extension hint to the style prompt.
    retry_kwargs = client.generate_track.await_args_list[1].kwargs
    assert "extended version, full length" in retry_kwargs["style"]


def test_min_duration_retry_then_fail():
    client = _client()
    client.generate_track = AsyncMock(
        side_effect=[SunoResult(b"s1", "t1"), SunoResult(b"s2", "t2")]
    )
    client._duration = AsyncMock(side_effect=[60.0, 75.0])

    with pytest.raises(SunoGenerationError, match="too short after retry"):
        asyncio.run(
            client.generate_with_min_duration(prompt="", style="s", title="T")
        )
    assert client.generate_track.await_count == 2


# ── helper ────────────────────────────────────────────────────────────────────


def test_extract_audio_url_prefers_audio_then_stream():
    assert (
        _extract_audio_url(
            {"response": {"sunoData": [{"audioUrl": "a", "streamAudioUrl": "s"}]}}
        )
        == "a"
    )
    assert (
        _extract_audio_url({"response": {"sunoData": [{"streamAudioUrl": "s"}]}}) == "s"
    )
    assert _extract_audio_url({}) is None
    assert _extract_audio_url({"response": {"sunoData": []}}) is None
