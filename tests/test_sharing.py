from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from private_internet.core.request_context import RequestContext
from private_internet.sharing import service
from private_internet.sharing.page import render_share_html, render_unavailable_html

_CTX = RequestContext(user_id="u1", user_email="u1@example.com", is_admin=False)


class TestBuildSnapshot:
    def test_rejects_unknown_kind(self):
        with pytest.raises(HTTPException) as exc:
            service.build_snapshot(_CTX, "not_a_kind", "x", None, "tok")
        assert exc.value.status_code == 400

    def test_media_kind_requires_ref_id(self):
        with pytest.raises(HTTPException) as exc:
            service.build_snapshot(_CTX, "pulse_post", None, None, "tok")
        assert exc.value.status_code == 400

    def test_missing_item_is_404(self):
        with patch.object(service, "_fetch_one", return_value=None):
            with pytest.raises(HTTPException) as exc:
                service.build_snapshot(_CTX, "pulse_post", "p1", None, "tok")
        assert exc.value.status_code == 404

    def test_pulse_post_snapshot_only_exposes_chosen_fields(self):
        row = {"body": "hello world " * 30, "image_url": "https://cdn/x.png",
               "creator_name": "Maya"}
        with patch.object(service, "_fetch_one", return_value=row):
            snap = service.build_snapshot(_CTX, "pulse_post", "p1", None, "tok")
        assert snap["kicker"] == "PULSE"
        assert snap["subtitle"] == "Maya"
        assert snap["media_type"] == "image"
        assert snap["image_url"] == "https://cdn/x.png"
        # description is truncated; no user_id or other columns leak through
        assert snap["description"].endswith("…")
        assert "user_id" not in snap

    def test_signal_video_snapshot(self):
        row = {"title": "My Video", "description": "desc", "video_url": "https://cdn/v.mp4",
               "thumbnail_url": "https://cdn/t.png", "creator_name": "Leo"}
        with patch.object(service, "_fetch_one", return_value=row):
            snap = service.build_snapshot(_CTX, "signal_video", "v1", None, "tok")
        assert snap["media_type"] == "video"
        assert snap["media_url"] == "https://cdn/v.mp4"
        assert snap["image_url"] == "https://cdn/t.png"

    def test_health_card_renders_image_and_reads_no_metrics(self):
        fake_store = MagicMock()
        fake_store.upload_share_card.return_value = "https://cdn/content/shares/tok/card.png"
        with patch.object(service, "AssetStore", return_value=fake_store), \
             patch("private_internet.content.cover_art.render_cover",
                   return_value=b"PNG") as render, \
             patch.object(service, "_fetch_one") as fetch:
            snap = service.build_snapshot(
                _CTX, "health_card", None,
                {"headline": "Hit my step goal", "caption": "12,431 steps"}, "tok",
            )
        # cards never touch the database
        fetch.assert_not_called()
        render.assert_called_once()
        assert snap["kicker"] == "HEALTH"
        assert snap["media_type"] == "card"
        assert snap["image_url"].endswith("card.png")

    def test_health_card_requires_headline(self):
        with pytest.raises(HTTPException) as exc:
            service.build_snapshot(_CTX, "health_card", None, {"caption": "x"}, "tok")
        assert exc.value.status_code == 400


class TestRenderPage:
    def test_html_has_open_graph_tags(self):
        snap = {
            "kicker": "ARIA", "title": "Night Drive", "subtitle": "Calm · AI music",
            "description": "An AI track", "media_type": "audio",
            "media_url": "https://cdn/a.mp3", "image_url": "https://cdn/art.png",
        }
        html = render_share_html(snap, "https://app.example/api/share/tok")
        assert 'property="og:title"' in html
        assert "Night Drive" in html
        assert 'property="og:image"' in html
        assert "https://cdn/a.mp3" in html  # audio source embedded
        assert "<audio" in html

    def test_video_uses_og_video(self):
        snap = {"kicker": "SIGNAL", "title": "V", "media_type": "video",
                "media_url": "https://cdn/v.mp4", "image_url": "https://cdn/p.png"}
        html = render_share_html(snap, "https://app.example/api/share/tok")
        assert 'property="og:video"' in html
        assert "<video" in html

    def test_escapes_html_in_snapshot(self):
        snap = {"title": "<script>alert(1)</script>", "media_type": "text"}
        html = render_share_html(snap, "https://app.example/api/share/tok")
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html

    def test_unavailable_page_renders(self):
        assert "no longer available" in render_unavailable_html()
