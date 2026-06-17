"""Tests for hybrid video provider routing (Wan2.1 + Kling).

Covers content/video_provider.py (the single source of truth for routing + cost)
and the per-provider fallback hierarchy in content/video_assembler.py:

    SIGNAL / PULSE → Wan2.1 → colour card   (NEVER Kling — cost protection)
    STORIES        → Kling  → Wan2.1 → colour card
"""

import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock

from private_internet.content import video_provider as vp
from private_internet.content import video_assembler as va
from private_internet.content.video_provider import (
    VIDEO_PROVIDER_MAP,
    ESTIMATED_COST_EUR,
    get_provider,
    log_generation_cost,
)
from private_internet.content.video_assembler import (
    _generate_clip_with_fallback,
    assemble_video,
)
from private_internet.content.replicate_wan_client import Wan2GenerationError
from private_internet.content.slide_clip import SlideClipError


# ── get_provider routing (single source of truth) ──────────────

class TestGetProvider:
    @pytest.mark.parametrize("content_type,expected", [
        ("stories", "kling"),
        ("signal",  "wan2"),
        ("pulse",   "wan2"),
    ])
    def test_returns_correct_provider(self, content_type, expected):
        assert get_provider(content_type) == expected

    def test_map_is_exactly_three_content_types(self):
        assert set(VIDEO_PROVIDER_MAP) == {"stories", "signal", "pulse"}

    def test_unknown_content_type_raises_valueerror(self):
        with pytest.raises(ValueError, match="Unknown content_type"):
            get_provider("podcast")

    def test_valueerror_lists_valid_types(self):
        with pytest.raises(ValueError) as exc:
            get_provider("")
        for ct in ("stories", "signal", "pulse"):
            assert ct in str(exc.value)


# ── Cost logging ───────────────────────────────────────────────

class TestCostLogging:
    def test_cost_constants_present(self):
        assert ESTIMATED_COST_EUR["wan2"] < ESTIMATED_COST_EUR["kling"]

    def test_log_generation_cost_emits_provider_and_cost(self):
        with patch.object(vp.logger, "info") as info:
            log_generation_cost("wan2", "signal", 3, is_fallback=False)
        info.assert_called_once()
        extra = info.call_args.kwargs["extra"]
        assert extra["provider"] == "wan2"
        assert extra["content_type"] == "signal"
        assert extra["scene_number"] == 3
        assert extra["is_fallback"] is False
        assert extra["estimated_cost_eur"] == ESTIMATED_COST_EUR["wan2"]

    def test_unknown_provider_costs_zero(self):
        with patch.object(vp.logger, "info") as info:
            log_generation_cost("midjourney", "signal", 1, is_fallback=True)
        assert info.call_args.kwargs["extra"]["estimated_cost_eur"] == 0.0


# ── Per-provider fallback hierarchy ────────────────────────────

class TestFallbackHierarchy:
    """The per-provider chain (Section 4 rewrite). `_generate_clip_with_fallback`
    now WRITES the clip to `clip_path` and logs its own cost (returns None):

        wan2  (SIGNAL/PULSE): Wan2.1 → image-slide (Ken Burns) → colour card.  NEVER Kling.
        kling (STORIES):      Kling  → Wan2.1 → image-slide → colour card.
    """

    @pytest.mark.anyio
    async def test_wan2_success(self, tmp_path):
        clip = str(tmp_path / "c.mp4")
        cost = []
        with patch.object(va._wan_client, "generate_clip",
                          new=AsyncMock(return_value=b"wan-bytes")) as wan, \
             patch.object(va, "generate_video_clip", new=AsyncMock()) as kling, \
             patch.object(va, "generate_slide_clip", new=AsyncMock()) as slide, \
             patch.object(va, "log_generation_cost", side_effect=lambda *a, **k: cost.append(a)):
            await _generate_clip_with_fallback(
                "wan2", "a prompt", 8, clip, 1, "signal", "calm"
            )
        assert Path(clip).read_bytes() == b"wan-bytes"
        wan.assert_awaited_once()
        kling.assert_not_called()   # SIGNAL/PULSE must NEVER touch Kling
        slide.assert_not_called()
        assert cost == [("wan2", "signal", 1, False)]

    @pytest.mark.anyio
    async def test_wan2_failure_uses_slide_before_card_never_kling(self, tmp_path):
        """A failed Wan2.1 clip tries the image-slide tier (motion) BEFORE the flat
        colour card, and must NEVER trigger a Kling call. Here the slide succeeds."""
        clip = str(tmp_path / "c.mp4")
        cost = []
        with patch.object(va._wan_client, "generate_clip",
                          new=AsyncMock(side_effect=Wan2GenerationError("boom"))), \
             patch.object(va, "generate_video_clip", new=AsyncMock()) as kling, \
             patch.object(va, "generate_slide_clip", new=AsyncMock()) as slide, \
             patch.object(va, "generate_fallback_card") as card, \
             patch.object(va, "log_generation_cost", side_effect=lambda *a, **k: cost.append(a)):
            await _generate_clip_with_fallback(
                "wan2", "a prompt", 8, clip, 2, "signal", "tense"
            )
        kling.assert_not_called()       # absolute constraint
        slide.assert_awaited_once()     # slide tier reached
        card.assert_not_called()        # slide succeeded — no colour card
        assert cost == [("slide", "signal", 2, True)]

    @pytest.mark.anyio
    async def test_wan2_and_slide_fail_uses_card_never_kling(self, tmp_path):
        """Wan2.1 AND the slide tier fail → flat colour card; Kling never called."""
        clip = str(tmp_path / "c.mp4")
        cost = []
        with patch.object(va._wan_client, "generate_clip",
                          new=AsyncMock(side_effect=Wan2GenerationError("boom"))), \
             patch.object(va, "generate_video_clip", new=AsyncMock()) as kling, \
             patch.object(va, "generate_slide_clip",
                          new=AsyncMock(side_effect=SlideClipError("no fal"))) as slide, \
             patch.object(va, "generate_fallback_card") as card, \
             patch.object(va, "log_generation_cost", side_effect=lambda *a, **k: cost.append(a)):
            await _generate_clip_with_fallback(
                "wan2", "a prompt", 8, clip, 3, "signal", "warm"
            )
        kling.assert_not_called()       # absolute constraint
        slide.assert_awaited_once()
        card.assert_called_once()
        assert cost == [("colour_card", "signal", 3, True)]

    @pytest.mark.anyio
    async def test_kling_success(self, tmp_path):
        clip = str(tmp_path / "c.mp4")
        cost = []
        with patch.object(va, "generate_video_clip",
                          new=AsyncMock(return_value=b"kling-bytes")) as kling, \
             patch.object(va._wan_client, "generate_clip", new=AsyncMock()) as wan, \
             patch.object(va, "generate_slide_clip", new=AsyncMock()) as slide, \
             patch.object(va, "log_generation_cost", side_effect=lambda *a, **k: cost.append(a)):
            await _generate_clip_with_fallback(
                "kling", "a prompt", 10, clip, 1, "stories", "calm"
            )
        assert Path(clip).read_bytes() == b"kling-bytes"
        kling.assert_awaited_once()
        wan.assert_not_called()
        slide.assert_not_called()
        assert cost == [("kling", "stories", 1, False)]

    @pytest.mark.anyio
    async def test_kling_failure_falls_back_to_wan2(self, tmp_path):
        clip = str(tmp_path / "c.mp4")
        cost = []
        with patch.object(va, "generate_video_clip",
                          new=AsyncMock(side_effect=RuntimeError("kling down"))), \
             patch.object(va._wan_client, "generate_clip",
                          new=AsyncMock(return_value=b"wan-bytes")) as wan, \
             patch.object(va, "generate_slide_clip", new=AsyncMock()) as slide, \
             patch.object(va, "log_generation_cost", side_effect=lambda *a, **k: cost.append(a)):
            await _generate_clip_with_fallback(
                "kling", "a prompt", 10, clip, 1, "stories", "calm"
            )
        # STORIES degrades to Wan2.1 before the slide/card; cost reflects wan2.
        assert Path(clip).read_bytes() == b"wan-bytes"
        wan.assert_awaited_once()
        slide.assert_not_called()
        assert cost == [("wan2", "stories", 1, True)]

    @pytest.mark.anyio
    async def test_kling_wan2_slide_all_fail_uses_card(self, tmp_path):
        clip = str(tmp_path / "c.mp4")
        cost = []
        with patch.object(va, "generate_video_clip",
                          new=AsyncMock(side_effect=RuntimeError("kling down"))), \
             patch.object(va._wan_client, "generate_clip",
                          new=AsyncMock(side_effect=Wan2GenerationError("wan down"))), \
             patch.object(va, "generate_slide_clip",
                          new=AsyncMock(side_effect=SlideClipError("no fal"))) as slide, \
             patch.object(va, "generate_fallback_card") as card, \
             patch.object(va, "log_generation_cost", side_effect=lambda *a, **k: cost.append(a)):
            await _generate_clip_with_fallback(
                "kling", "a prompt", 10, clip, 1, "stories", "calm"
            )
        slide.assert_awaited_once()
        card.assert_called_once()
        assert cost == [("colour_card", "stories", 1, True)]


# ── Cost logging fires during assembly ─────────────────────────

def _scene(n):
    return {
        "scene_number": n,
        "narration_text": f"Narration {n}.",
        "visual_description": f"A beat number {n}",
        "duration_seconds": 8,
        "scene_type": "development",
    }


class TestAssemblyLogsCost:
    @pytest.mark.anyio
    async def test_cost_logged_once_per_successful_clip(self):
        """log_generation_cost fires for each clip a provider actually produces
        (SIGNAL → wan2). A clip that degrades to a colour card logs no cost."""
        from tests.test_video_assembler import _patch_pipeline

        scenes = [_scene(1), _scene(2), _scene(3)]

        async def clip(prompt, *, duration, aspect_ratio):
            return b"ok"

        cost_calls = []
        patches, _ = _patch_pipeline(clip)
        patches.append(patch.object(
            va, "log_generation_cost",
            side_effect=lambda *a, **k: cost_calls.append((a, k)),
        ))
        for p in patches:
            p.start()
        try:
            await assemble_video(
                scenes=scenes,
                narration_text="n",
                language_code="en",
                output_s3_key="k.mp4",
                content_type="signal",
            )
        finally:
            for p in patches:
                p.stop()

        # One cost log per successful clip, all attributed to wan2 for SIGNAL.
        assert len(cost_calls) == 3
        assert all(args[0] == "wan2" for args, _ in cost_calls)
        assert all(args[1] == "signal" for args, _ in cost_calls)
