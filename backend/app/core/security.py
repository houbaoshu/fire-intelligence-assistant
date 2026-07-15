from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Literal


class TokenError(ValueError):
    pass


@dataclass(frozen=True)
class TokenPayload:
    subject: uuid.UUID
    token_type: Literal["access", "refresh"]
    expires_at: int


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    n, r, p = 2**14, 8, 1
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=64)
    return "$".join(
        (
            "scrypt",
            str(n),
            str(r),
            str(p),
            _b64encode(salt),
            _b64encode(digest),
        )
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$", maxsplit=5)
        if algorithm != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_b64decode(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=64,
        )
        return hmac.compare_digest(digest, _b64decode(expected))
    except (TypeError, ValueError):
        return False


def create_token(
    *,
    subject: uuid.UUID,
    token_type: Literal["access", "refresh"],
    lifetime: timedelta,
    secret: bytes,
) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + int(lifetime.total_seconds()),
        "jti": str(uuid.uuid4()),
        "iss": "fire-intelligence-platform",
    }
    unsigned = f"{_json_segment(header)}.{_json_segment(payload)}"
    signature = hmac.new(secret, unsigned.encode("ascii"), hashlib.sha256).digest()
    return f"{unsigned}.{_b64encode(signature)}"


def decode_token(
    token: str, *, expected_type: Literal["access", "refresh"], secret: bytes
) -> TokenPayload:
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
        unsigned = f"{header_segment}.{payload_segment}"
        signature = _b64decode(signature_segment)
        expected_signature = hmac.new(secret, unsigned.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected_signature):
            raise TokenError("Invalid token signature")
        header = _decode_json(header_segment)
        payload = _decode_json(payload_segment)
        if header.get("alg") != "HS256" or header.get("typ") != "JWT":
            raise TokenError("Unsupported token header")
        if payload.get("iss") != "fire-intelligence-platform":
            raise TokenError("Invalid token issuer")
        if payload.get("type") != expected_type:
            raise TokenError("Invalid token type")
        expires_at = int(payload["exp"])
        if expires_at <= int(time.time()):
            raise TokenError("Token has expired")
        return TokenPayload(
            subject=uuid.UUID(str(payload["sub"])),
            token_type=expected_type,
            expires_at=expires_at,
        )
    except TokenError:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise TokenError("Malformed token") from error


def _json_segment(value: dict[str, Any]) -> str:
    return _b64encode(json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def _decode_json(segment: str) -> dict[str, Any]:
    value = json.loads(_b64decode(segment))
    if not isinstance(value, dict):
        raise TokenError("Malformed token payload")
    return value


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
