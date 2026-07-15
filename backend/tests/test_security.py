from __future__ import annotations

import uuid
from datetime import timedelta

import pytest

from app.core.security import (
    TokenError,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_is_salted_and_verifiable() -> None:
    first = hash_password("correct horse battery staple")
    second = hash_password("correct horse battery staple")
    assert first != second
    assert verify_password("correct horse battery staple", first)
    assert not verify_password("wrong", first)


def test_tokens_are_signed_and_type_checked() -> None:
    user_id = uuid.uuid4()
    secret = b"a-test-secret-that-is-long-enough"
    token = create_token(
        subject=user_id,
        token_type="access",
        lifetime=timedelta(minutes=5),
        secret=secret,
    )
    assert decode_token(token, expected_type="access", secret=secret).subject == user_id
    with pytest.raises(TokenError):
        decode_token(token, expected_type="refresh", secret=secret)
    with pytest.raises(TokenError):
        decode_token(token, expected_type="access", secret=b"different-secret")
