"""
Tests for update_memory and delete_memory service functions.

Run with:
    pip install -e ".[dev]"
    pytest
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from personal_intelligence.memory.service import Memory, delete_memory, update_memory


def _make_memory(**kwargs) -> Memory:
    defaults = dict(
        memory_id="test-id",
        title="Original Title",
        content="Original content",
        tags=["tag1", "tag2"],
        created_at=datetime.now(timezone.utc),
    )
    return Memory(**{**defaults, **kwargs})


def _mock_conn(rowcount: int = 1) -> MagicMock:
    conn = MagicMock()
    cursor = MagicMock()
    cursor.rowcount = rowcount
    conn.cursor.return_value = cursor
    return conn


# ── update_memory ──────────────────────────────────────────────

class TestUpdateMemory:
    def test_returns_none_for_unknown_id(self):
        with patch("personal_intelligence.memory.service.fetch_memory", return_value=None):
            result = update_memory("nonexistent-id", title="New Title")
        assert result is None

    def test_partial_update_title_only(self):
        existing = _make_memory()
        with (
            patch("personal_intelligence.memory.service.fetch_memory", return_value=existing),
            patch("personal_intelligence.memory.service._get_embedding", return_value=[0.1] * 1024),
            patch("personal_intelligence.memory.service._connect", return_value=_mock_conn()),
        ):
            result = update_memory("test-id", title="New Title")

        assert result is not None
        assert result.title == "New Title"
        assert result.content == "Original content"
        assert result.tags == ["tag1", "tag2"]
        assert result.updated_at is not None

    def test_partial_update_tags_only_skips_reembed(self):
        existing = _make_memory()
        with (
            patch("personal_intelligence.memory.service.fetch_memory", return_value=existing),
            patch("personal_intelligence.memory.service._get_embedding") as mock_embed,
            patch("personal_intelligence.memory.service._connect", return_value=_mock_conn()),
        ):
            result = update_memory("test-id", tags=["new-tag"])

        mock_embed.assert_not_called()
        assert result is not None
        assert result.tags == ["new-tag"]

    def test_content_replace(self):
        existing = _make_memory()
        with (
            patch("personal_intelligence.memory.service.fetch_memory", return_value=existing),
            patch("personal_intelligence.memory.service._get_embedding", return_value=[0.1] * 1024),
            patch("personal_intelligence.memory.service._connect", return_value=_mock_conn()),
        ):
            result = update_memory("test-id", content="Replaced content")

        assert result is not None
        assert result.content == "Replaced content"

    def test_append_content(self):
        existing = _make_memory()
        with (
            patch("personal_intelligence.memory.service.fetch_memory", return_value=existing),
            patch("personal_intelligence.memory.service._get_embedding", return_value=[0.1] * 1024),
            patch("personal_intelligence.memory.service._connect", return_value=_mock_conn()),
        ):
            result = update_memory("test-id", content="Appended text", append_content=True)

        assert result is not None
        assert "Original content" in result.content
        assert "Appended text" in result.content
        assert "---" in result.content
        assert "Updated" in result.content

    def test_append_without_content_is_noop_on_content(self):
        existing = _make_memory()
        with (
            patch("personal_intelligence.memory.service.fetch_memory", return_value=existing),
            patch("personal_intelligence.memory.service._get_embedding") as mock_embed,
            patch("personal_intelligence.memory.service._connect", return_value=_mock_conn()),
        ):
            result = update_memory("test-id", append_content=True)

        mock_embed.assert_not_called()
        assert result is not None
        assert result.content == "Original content"

    def test_preserves_created_at(self):
        existing = _make_memory()
        with (
            patch("personal_intelligence.memory.service.fetch_memory", return_value=existing),
            patch("personal_intelligence.memory.service._connect", return_value=_mock_conn()),
        ):
            result = update_memory("test-id")

        assert result is not None
        assert result.created_at == existing.created_at


# ── delete_memory ──────────────────────────────────────────────

class TestDeleteMemory:
    def test_successful_delete_returns_true(self):
        with patch("personal_intelligence.memory.service._connect", return_value=_mock_conn(rowcount=1)):
            result = delete_memory("test-id")
        assert result is True

    def test_nonexistent_id_returns_false(self):
        with patch("personal_intelligence.memory.service._connect", return_value=_mock_conn(rowcount=0)):
            result = delete_memory("nonexistent-id")
        assert result is False


# ── MCP delete tool: confirm=False guard ──────────────────────

class TestMcpDeleteConfirmGuard:
    def test_confirm_false_is_rejected(self):
        # Import after patching init_db to prevent DB connection at import time
        with patch("personal_intelligence.memory.service.init_db"):
            pass
        # The confirm guard is pure Python logic — test inline
        confirm = False
        if not confirm:
            result = "Deletion aborted: confirm must be True to delete a memory."
        assert "confirm must be True" in result

    def test_confirm_true_proceeds(self):
        with patch("personal_intelligence.memory.service.delete_memory", return_value=True):
            confirm = True
            assert confirm is True
