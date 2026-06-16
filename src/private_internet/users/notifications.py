"""Transactional email — SES-ready abstraction.

`_send` is the single swap-point for the email provider. It is gated by
`EMAIL_BACKEND`:
  - "log" (default): just log the actionable URL at INFO (visible in
    `journalctl`) and return True. Deploying without SES configured changes
    nothing.
  - "ses" (and `SES_SENDER_EMAIL` set): send via AWS SESv2. On ANY failure it
    logs the exception, falls back to the INFO log of the body so an operator
    can still hand out the link, and returns False.
The link-building and call sites stay the same regardless of backend.

These functions NEVER raise: a notification failure must not break registration,
verification, or password reset. Tokens appear in logs by necessity (so an
operator can hand a link to a user) but raw passwords and password hashes are
never logged anywhere.
"""

import logging

from private_internet.config import get_settings

logger = logging.getLogger(__name__)


def _send(to: str, subject: str, body: str) -> bool:
    """Dispatch an email. Gated by EMAIL_BACKEND; NEVER raises."""
    settings = get_settings()

    if settings.email_backend == "ses" and settings.ses_sender_email:
        try:
            import boto3

            client = boto3.client("sesv2", region_name=settings.aws_region)
            kwargs = {
                "FromEmailAddress": settings.ses_sender_email,
                "Destination": {"ToAddresses": [to]},
                "Content": {
                    "Simple": {
                        "Subject": {"Data": subject, "Charset": "UTF-8"},
                        "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
                    }
                },
            }
            if settings.ses_configuration_set:
                kwargs["ConfigurationSetName"] = settings.ses_configuration_set
            client.send_email(**kwargs)
            return True
        except Exception:
            # Never break the calling flow; log the failure, then fall back to
            # the INFO log of the body so an operator can still hand out the link.
            logger.exception("SES send failed for %s; falling back to log", to)
            logger.info("EMAIL → %s | %s\n%s", to, subject, body)
            return False

    # Log backend (default): keep the actionable link visible to operators.
    try:
        logger.info("EMAIL → %s | %s\n%s", to, subject, body)
        return True
    except Exception:  # pragma: no cover - logging should never fail
        logger.exception("Failed to dispatch email to %s", to)
        return False


def send_verification_email(to: str, token: str) -> bool:
    settings = get_settings()
    link = f"{settings.base_url}/api/auth/verify-email?token={token}"
    return _send(
        to,
        "Verify your Private Internet email",
        f"Confirm your account by visiting:\n{link}\n\n"
        f"This link expires in {settings.verification_token_ttl_hours} hours.",
    )


def send_password_reset_email(to: str, token: str) -> bool:
    settings = get_settings()
    link = f"{settings.base_url}/reset-password?token={token}"
    return _send(
        to,
        "Reset your Private Internet password",
        f"Reset your password by visiting:\n{link}\n\n"
        f"This link expires in {settings.reset_token_ttl_hours} hour(s). "
        f"If you did not request this, ignore this email.",
    )


def send_welcome_email(to: str, display_name: str) -> bool:
    settings = get_settings()
    return _send(
        to,
        "Welcome to Private Internet",
        f"Hi {display_name},\n\n"
        f"Your private AI brain is being set up. Sign in at {settings.base_url} "
        f"to get started.",
    )
