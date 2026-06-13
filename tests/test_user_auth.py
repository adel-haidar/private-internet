"""Tests for email/password user auth: password hashing + auth router."""

import json
from unittest.mock import patch

import pytest

from private_internet.users.passwords import (
    MIN_PASSWORD_LENGTH,
    hash_password,
    verify_password,
)
from private_internet.users.routes import (
    LoginRequest,
    OnboardingRequest,
    RegisterRequest,
    login,
    register,
    update_onboarding,
)
from private_internet.core.request_context import RequestContext

_GOOD_PW = "correct-horse-battery"  # ≥ 12 chars


class _Settings:
    def __init__(self, registration_open=True, max_users=0):
        self.registration_open = registration_open
        self.max_users = max_users


def _body(resp):
    return json.loads(resp.body)


# ── password hashing ───────────────────────────────────────────

class TestPasswordHashing:
    def test_round_trip(self):
        stored = hash_password(_GOOD_PW)
        assert stored.startswith("scrypt$")
        assert verify_password(_GOOD_PW, stored) is True

    def test_wrong_password_fails(self):
        stored = hash_password(_GOOD_PW)
        assert verify_password("not-the-password!", stored) is False

    def test_salt_makes_hashes_unique(self):
        assert hash_password(_GOOD_PW) != hash_password(_GOOD_PW)

    def test_malformed_or_missing_stored_is_false(self):
        assert verify_password(_GOOD_PW, None) is False
        assert verify_password(_GOOD_PW, "") is False
        assert verify_password(_GOOD_PW, "garbage") is False
        assert verify_password(_GOOD_PW, "bcrypt$x$y") is False

    def test_too_short_raises(self):
        with pytest.raises(ValueError):
            hash_password("a" * (MIN_PASSWORD_LENGTH - 1))


# ── register ───────────────────────────────────────────────────

class TestRegister:
    @pytest.mark.anyio
    async def test_happy_path(self):
        created = {"id": "u-123", "email": "lena@example.com", "display_name": "Lena",
                   "is_admin": False, "onboarding_completed": False, "onboarding_step": 0}
        with (
            patch("private_internet.users.routes.get_settings", return_value=_Settings()),
            patch("private_internet.users.routes.count_users", return_value=0),
            patch("private_internet.users.routes.get_user_by_email", return_value=None),
            patch("private_internet.users.routes.create_user", return_value=created) as mock_create,
            patch("private_internet.users.routes.save_memory") as mock_mem,
            patch("private_internet.users.routes.create_user_token", return_value="jwt-tok"),
        ):
            result = await register(RegisterRequest(
                email="Lena@Example.com", display_name="Lena",
                password=_GOOD_PW, referral_source="a friend",
            ))

        assert result["token"] == "jwt-tok"
        assert result["user"]["id"] == "u-123"
        # email normalized to lowercase before persistence
        assert mock_create.call_args.kwargs["email"] == "lena@example.com"
        # welcome memory seeded with the onboarding tags + referral text
        kw = mock_mem.call_args.kwargs
        assert kw["user_id"] == "u-123"
        assert kw["tags"] == ["introduction", "onboarding", "profile"]
        assert "a friend" in kw["content"]

    @pytest.mark.anyio
    async def test_duplicate_email_409(self):
        with (
            patch("private_internet.users.routes.get_settings", return_value=_Settings()),
            patch("private_internet.users.routes.count_users", return_value=0),
            patch("private_internet.users.routes.get_user_by_email", return_value={"id": "x"}),
        ):
            resp = await register(RegisterRequest(
                email="dup@example.com", display_name="Dup", password=_GOOD_PW))
        assert resp.status_code == 409
        assert "already exists" in _body(resp)["error"]

    @pytest.mark.anyio
    async def test_registration_closed_403(self):
        with patch("private_internet.users.routes.get_settings",
                   return_value=_Settings(registration_open=False)):
            resp = await register(RegisterRequest(
                email="x@example.com", display_name="X", password=_GOOD_PW))
        assert resp.status_code == 403
        assert "invite-only" in _body(resp)["error"]

    @pytest.mark.anyio
    async def test_max_users_403(self):
        with (
            patch("private_internet.users.routes.get_settings", return_value=_Settings(max_users=5)),
            patch("private_internet.users.routes.count_users", return_value=5),
        ):
            resp = await register(RegisterRequest(
                email="x@example.com", display_name="X", password=_GOOD_PW))
        assert resp.status_code == 403
        assert "limit reached" in _body(resp)["error"]

    @pytest.mark.anyio
    async def test_short_password_422(self):
        with (
            patch("private_internet.users.routes.get_settings", return_value=_Settings()),
            patch("private_internet.users.routes.count_users", return_value=0),
        ):
            resp = await register(RegisterRequest(
                email="x@example.com", display_name="X", password="short"))
        assert resp.status_code == 422


# ── login ──────────────────────────────────────────────────────

class TestLogin:
    @pytest.mark.anyio
    async def test_unknown_email_404(self):
        with patch("private_internet.users.routes.get_user_by_email", return_value=None):
            resp = await login(LoginRequest(email="nobody@example.com", password=_GOOD_PW))
        assert resp.status_code == 404
        assert "No account found" in _body(resp)["error"]

    @pytest.mark.anyio
    async def test_wrong_password_401(self):
        user = {"id": "u-1", "email": "a@b.com", "password_hash": hash_password(_GOOD_PW)}
        with patch("private_internet.users.routes.get_user_by_email", return_value=user):
            resp = await login(LoginRequest(email="a@b.com", password="wrong-password!!"))
        assert resp.status_code == 401
        assert _body(resp)["error"] == "Incorrect password."

    @pytest.mark.anyio
    async def test_success_strips_hash_and_returns_token(self):
        user = {"id": "u-1", "email": "a@b.com", "display_name": "A",
                "password_hash": hash_password(_GOOD_PW)}
        with (
            patch("private_internet.users.routes.get_user_by_email", return_value=user),
            patch("private_internet.users.routes.touch_last_active") as mock_touch,
            patch("private_internet.users.routes.create_user_token", return_value="jwt-tok"),
        ):
            result = await login(LoginRequest(email="A@B.com", password=_GOOD_PW))
        assert result["token"] == "jwt-tok"
        assert "password_hash" not in result["user"]
        mock_touch.assert_called_once_with("u-1")


# ── onboarding ─────────────────────────────────────────────────

class TestOnboarding:
    @pytest.mark.anyio
    async def test_updates_only_provided_fields(self):
        ctx = RequestContext(user_id="u-1", user_email="a@b.com", is_admin=False)
        updated = {"id": "u-1", "onboarding_step": 3, "onboarding_completed": False}
        with patch("private_internet.users.routes.update_user", return_value=updated) as mock_upd:
            result = await update_onboarding(OnboardingRequest(onboarding_step=3), ctx=ctx)
        assert result["user"]["onboarding_step"] == 3
        assert mock_upd.call_args.args[0] == "u-1"
        assert mock_upd.call_args.kwargs == {"onboarding_step": 3}

    @pytest.mark.anyio
    async def test_empty_update_422(self):
        ctx = RequestContext(user_id="u-1", user_email="a@b.com", is_admin=False)
        resp = await update_onboarding(OnboardingRequest(), ctx=ctx)
        assert resp.status_code == 422
