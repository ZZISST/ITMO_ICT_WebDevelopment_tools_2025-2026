import os
import sys
from datetime import datetime, timedelta

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.core.settings.security import (
    create_access_token,
    decode_token,
    get_password_hash,
    verify_password,
)

class TestGetPasswordHash:
    def test_hash_is_not_plain_text(self):
        """Hashed password must differ from the original plain-text."""
        hashed = get_password_hash("supersecret")
        assert hashed != "supersecret"

    def test_hash_starts_with_bcrypt_prefix(self):
        """bcrypt hashes always start with $2b$ (or $2a$)."""
        hashed = get_password_hash("password123")
        assert hashed.startswith("$2")

    def test_two_hashes_of_same_password_differ(self):
        """bcrypt uses random salts — identical passwords produce different hashes."""
        h1 = get_password_hash("same_password")
        h2 = get_password_hash("same_password")
        assert h1 != h2

    def test_hash_minimum_length(self):
        """A valid bcrypt hash is at least 60 characters long."""
        hashed = get_password_hash("x")
        assert len(hashed) >= 60


class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        plain = "correct_horse_battery_staple"
        hashed = get_password_hash(plain)
        assert verify_password(plain, hashed) is True

    def test_wrong_password_returns_false(self):
        hashed = get_password_hash("rightpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_empty_password_vs_hashed_nonempty_returns_false(self):
        hashed = get_password_hash("notempty")
        assert verify_password("", hashed) is False

    def test_case_sensitive(self):
        """Passwords are case-sensitive."""
        hashed = get_password_hash("Password")
        assert verify_password("password", hashed) is False

    def test_verify_is_consistent_across_calls(self):
        """Verifying the same correct password twice gives True both times."""
        plain = "consistent_check"
        hashed = get_password_hash(plain)
        assert verify_password(plain, hashed) is True
        assert verify_password(plain, hashed) is True

    def test_whitespace_matters(self):
        """' password' != 'password'."""
        hashed = get_password_hash("password")
        assert verify_password(" password", hashed) is False


class TestCreateAccessToken:
    def test_returns_non_empty_string(self):
        token = create_access_token({"sub": "alice"})
        assert isinstance(token, str) and len(token) > 0

    def test_token_has_three_parts(self):
        """A well-formed JWT is always header.payload.signature."""
        token = create_access_token({"sub": "alice"})
        assert len(token.split(".")) == 3

    def test_payload_preserved_in_decoded_token(self):
        """The 'sub' claim we put in must come back out after decoding."""
        token = create_access_token({"sub": "bob"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "bob"

    def test_exp_claim_is_present(self):
        """Every token must carry an expiry timestamp."""
        token = create_access_token({"sub": "alice"})
        payload = decode_token(token)
        assert "exp" in payload

    def test_default_expiry_is_roughly_15_minutes(self):
        """Without an explicit delta the default expiry is ~15 minutes."""
        before = datetime.utcnow()
        token = create_access_token({"sub": "alice"})
        after = datetime.utcnow()
        payload = decode_token(token)

        exp_dt = datetime.utcfromtimestamp(payload["exp"])
        # Allow a ±30-second window for test execution time.
        assert before + timedelta(minutes=14, seconds=30) <= exp_dt
        assert exp_dt <= after + timedelta(minutes=15, seconds=30)

    def test_custom_expiry_respected(self):
        """When expires_delta is provided the exp claim must match."""
        delta = timedelta(hours=2)
        before = datetime.utcnow()
        token = create_access_token({"sub": "charlie"}, expires_delta=delta)
        after = datetime.utcnow()
        payload = decode_token(token)

        exp_dt = datetime.utcfromtimestamp(payload["exp"])
        assert before + timedelta(hours=1, minutes=59, seconds=30) <= exp_dt
        assert exp_dt <= after + timedelta(hours=2, seconds=30)

    def test_extra_claims_are_preserved(self):
        """Arbitrary extra claims in the data dict survive the round-trip."""
        token = create_access_token({"sub": "dave", "role": "admin", "uid": 42})
        payload = decode_token(token)
        assert payload["role"] == "admin"
        assert payload["uid"] == 42

class TestDecodeToken:
    def test_valid_token_returns_dict(self):
        token = create_access_token({"sub": "eve"})
        result = decode_token(token)
        assert isinstance(result, dict)

    def test_expired_token_returns_none(self):
        """A token whose expiry is in the past must not be accepted."""
        expired_delta = timedelta(seconds=-1)
        token = create_access_token(
            {"sub": "expired_user"}, expires_delta=expired_delta
        )
        assert decode_token(token) is None

    def test_tampered_signature_returns_none(self):
        """Flipping one character in the signature must invalidate the token."""
        token = create_access_token({"sub": "frank"})
        header, payload, signature = token.split(".")
        # Flip the last character of the signature.
        bad_signature = signature[:-1] + ("A" if signature[-1] != "A" else "B")
        tampered = f"{header}.{payload}.{bad_signature}"
        assert decode_token(tampered) is None

    def test_wrong_secret_returns_none(self):
        """A token signed with a different secret must be rejected."""
        from jose import jwt as jose_jwt

        from app.core.settings.config import settings

        foreign_token = jose_jwt.encode(
            {"sub": "impostor", "exp": datetime.utcnow() + timedelta(minutes=5)},
            key="totally_wrong_secret",
            algorithm=settings.ALGORITHM,
        )
        assert decode_token(foreign_token) is None

    def test_malformed_token_returns_none(self):
        assert decode_token("not.a.jwt") is None

    def test_completely_garbage_input_returns_none(self):
        assert decode_token("garbage!!!") is None

    def test_empty_string_returns_none(self):
        assert decode_token("") is None
