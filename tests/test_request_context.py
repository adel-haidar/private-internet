"""INTERNAL_SECRET → seed-admin auth (same-host service access)."""

import os
from unittest.mock import patch

from private_internet.core.request_context import _is_internal_secret


class _Req:
    """Minimal stand-in for a Starlette Request (only .headers is used)."""
    def __init__(self, headers: dict):
        self.headers = headers


SECRET = "0123456789abcdef0123456789abcdef"


class TestInternalSecret:
    def test_x_internal_secret_header_matches(self):
        with patch.dict(os.environ, {"INTERNAL_SECRET": SECRET}):
            assert _is_internal_secret(_Req({"X-Internal-Secret": SECRET})) is True

    def test_bearer_secret_matches(self):
        with patch.dict(os.environ, {"INTERNAL_SECRET": SECRET}):
            assert _is_internal_secret(_Req({"Authorization": f"Bearer {SECRET}"})) is True

    def test_wrong_value_rejected(self):
        with patch.dict(os.environ, {"INTERNAL_SECRET": SECRET}):
            assert _is_internal_secret(_Req({"X-Internal-Secret": "nope"})) is False
            assert _is_internal_secret(_Req({"Authorization": "Bearer nope"})) is False

    def test_no_credential_rejected(self):
        with patch.dict(os.environ, {"INTERNAL_SECRET": SECRET}):
            assert _is_internal_secret(_Req({})) is False

    def test_unconfigured_secret_never_matches(self):
        with patch.dict(os.environ, {"INTERNAL_SECRET": ""}):
            assert _is_internal_secret(_Req({"X-Internal-Secret": ""})) is False
            assert _is_internal_secret(_Req({"Authorization": "Bearer "})) is False
