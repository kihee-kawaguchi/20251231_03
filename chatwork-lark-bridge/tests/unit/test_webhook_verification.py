"""Unit tests for webhook signature verification."""

import base64
import hashlib
import hmac
import pytest

from src.utils.webhook_verification import (
    verify_chatwork_signature,
    verify_lark_verification_token,
)
from src.core.exceptions import SignatureVerificationError


@pytest.mark.unit
class TestChatworkSignatureVerification:
    """Test Chatwork webhook signature verification."""

    def test_valid_chatwork_signature(self):
        """Test verification with valid signature."""
        body = b'{"webhook_event_type":"message_created"}'
        secret = base64.b64encode(b"test_secret").decode()

        # Generate valid signature
        decoded_secret = base64.b64decode(secret)
        digest = hmac.new(decoded_secret, body, hashlib.sha256).digest()
        signature = base64.b64encode(digest).decode()

        # Should not raise exception
        verify_chatwork_signature(body, signature, secret)

    def test_invalid_chatwork_signature(self):
        """Test verification with invalid signature."""
        body = b'{"webhook_event_type":"message_created"}'
        secret = base64.b64encode(b"test_secret").decode()
        invalid_signature = "invalid_signature_here"

        with pytest.raises(SignatureVerificationError) as exc_info:
            verify_chatwork_signature(body, invalid_signature, secret)

        assert "chatwork" in str(exc_info.value).lower()

    def test_tampered_body(self):
        """Test verification with tampered request body."""
        original_body = b'{"webhook_event_type":"message_created"}'
        tampered_body = b'{"webhook_event_type":"message_deleted"}'
        secret = base64.b64encode(b"test_secret").decode()

        # Generate signature for original body
        decoded_secret = base64.b64decode(secret)
        digest = hmac.new(decoded_secret, original_body, hashlib.sha256).digest()
        signature = base64.b64encode(digest).decode()

        # Verification should fail with tampered body
        with pytest.raises(SignatureVerificationError):
            verify_chatwork_signature(tampered_body, signature, secret)

    def test_different_secret(self):
        """Test verification with different secret."""
        body = b'{"webhook_event_type":"message_created"}'
        secret1 = base64.b64encode(b"test_secret_1").decode()
        secret2 = base64.b64encode(b"test_secret_2").decode()

        # Generate signature with secret1
        decoded_secret = base64.b64decode(secret1)
        digest = hmac.new(decoded_secret, body, hashlib.sha256).digest()
        signature = base64.b64encode(digest).decode()

        # Verification should fail with secret2
        with pytest.raises(SignatureVerificationError):
            verify_chatwork_signature(body, signature, secret2)


@pytest.mark.unit
class TestLarkVerificationToken:
    """Test Lark verification token validation."""

    def test_valid_lark_token(self, setup_test_env):
        """Test verification with valid token."""
        # Use the token set in conftest.py setup_test_env fixture
        # which sets LARK_VERIFICATION_TOKEN to "test_verification_token"
        from src.core.config import settings

        # Should not raise exception
        verify_lark_verification_token(settings.lark_verification_token)

    def test_invalid_lark_token(self, setup_test_env):
        """Test verification with invalid token."""
        with pytest.raises(SignatureVerificationError) as exc_info:
            verify_lark_verification_token("wrong_token")

        assert "lark" in str(exc_info.value).lower()

    def test_none_token(self, setup_test_env):
        """Test verification with None token."""
        with pytest.raises(SignatureVerificationError):
            verify_lark_verification_token(None)

    def test_empty_token(self, setup_test_env):
        """Test verification with empty token."""
        with pytest.raises(SignatureVerificationError):
            verify_lark_verification_token("")
