"""Webhook signature verification utilities."""

import base64
import hmac
import hashlib
from typing import Optional

from ..core.config import settings
from ..core.exceptions import SignatureVerificationError
from ..core.logging import get_logger

logger = get_logger(__name__)


def verify_chatwork_signature(
    body: bytes,
    signature: str,
    secret: Optional[str] = None,
) -> bool:
    """
    Verify Chatwork webhook signature.

    Args:
        body: Raw request body as bytes
        signature: Signature from x-chatworkwebhooksignature header
        secret: Webhook secret (base64 encoded), defaults to config

    Returns:
        True if signature is valid

    Raises:
        SignatureVerificationError: If signature verification fails
    """
    try:
        secret_key = secret or settings.chatwork_webhook_secret

        # Decode the secret from base64
        decoded_secret = base64.b64decode(secret_key)

        # Compute HMAC-SHA256
        digest = hmac.new(decoded_secret, body, hashlib.sha256).digest()

        # Base64 encode the digest
        expected_signature = base64.b64encode(digest).decode()

        # Compare signatures (constant time comparison)
        is_valid = hmac.compare_digest(signature, expected_signature)

        if not is_valid:
            logger.warning(
                "chatwork_signature_verification_failed",
                received_signature=signature[:20] + "...",  # Truncate for security
            )
            raise SignatureVerificationError("Chatwork webhook signature mismatch")

        logger.debug("chatwork_signature_verified")
        return True

    except Exception as e:
        logger.error("chatwork_signature_verification_error", error=str(e))
        if isinstance(e, SignatureVerificationError):
            raise
        raise SignatureVerificationError(f"Failed to verify Chatwork signature: {e}")


def verify_lark_signature(
    timestamp: str,
    nonce: str,
    encrypt_key: str,
    body: str,
    signature: str,
) -> bool:
    """
    Verify Lark event signature.

    Args:
        timestamp: Timestamp from request
        nonce: Nonce from request
        encrypt_key: Encryption key from config
        body: Request body string
        signature: Signature from request

    Returns:
        True if signature is valid

    Raises:
        SignatureVerificationError: If signature verification fails
    """
    try:
        # Concatenate timestamp + nonce + encrypt_key + body
        content = f"{timestamp}{nonce}{encrypt_key}{body}"

        # Compute SHA256
        expected_signature = hashlib.sha256(content.encode()).hexdigest()

        # Compare signatures
        is_valid = hmac.compare_digest(signature, expected_signature)

        if not is_valid:
            logger.warning(
                "lark_signature_verification_failed",
                timestamp=timestamp,
                nonce=nonce[:10] + "...",
            )
            raise SignatureVerificationError("Lark event signature mismatch")

        logger.debug("lark_signature_verified")
        return True

    except Exception as e:
        logger.error("lark_signature_verification_error", error=str(e))
        if isinstance(e, SignatureVerificationError):
            raise
        raise SignatureVerificationError(f"Failed to verify Lark signature: {e}")


def verify_lark_verification_token(token: str | None) -> bool:
    """
    Verify Lark verification token.

    This is used for the initial webhook verification challenge.
    """
    if token is None:
        logger.warning("lark_verification_token_missing")
        raise SignatureVerificationError("lark")

    expected_token = settings.lark_verification_token
    is_valid = hmac.compare_digest(token, expected_token)

    if not is_valid:
        logger.warning("lark_verification_token_mismatch")
        raise SignatureVerificationError("lark")

    return True
