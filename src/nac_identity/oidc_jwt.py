from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Callable, Mapping
from urllib.request import Request, urlopen


OidcJsonFetcher = Callable[[str], Mapping[str, Any]]
OidcIdTokenVerifier = Callable[[str], dict[str, Any] | None]

_DISCOVERY_PATH = "/.well-known/openid-configuration"
_RS256_DIGEST_INFO_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")


def build_oidc_id_token_verifier(
    *,
    issuer: str,
    audience: str,
    jwks_fetcher: OidcJsonFetcher | None = None,
    now: int | None = None,
    timeout_seconds: float = 5.0,
) -> OidcIdTokenVerifier | None:
    normalized_issuer = issuer.strip().rstrip("/") if isinstance(issuer, str) else ""
    normalized_audience = audience.strip() if isinstance(audience, str) else ""
    if not normalized_issuer or not normalized_audience:
        return None

    fetcher = jwks_fetcher or (lambda url: _fetch_json(url, timeout_seconds=timeout_seconds))
    jwks_cache: dict[str, Any] = {}

    def verify(id_token: str) -> dict[str, Any] | None:
        return _verify_id_token(
            id_token,
            issuer=normalized_issuer,
            audience=normalized_audience,
            fetcher=fetcher,
            jwks_cache=jwks_cache,
            now=int(time.time() if now is None else now),
        )

    return verify


def _verify_id_token(
    id_token: str,
    *,
    issuer: str,
    audience: str,
    fetcher: OidcJsonFetcher,
    jwks_cache: dict[str, Any],
    now: int,
) -> dict[str, Any] | None:
    try:
        header_segment, payload_segment, signature_segment = id_token.split(".")
        signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
        header = json.loads(_base64url_decode(header_segment).decode("utf-8"))
        claims = json.loads(_base64url_decode(payload_segment).decode("utf-8"))
        signature = _base64url_decode(signature_segment)
    except (AttributeError, UnicodeDecodeError, ValueError, json.JSONDecodeError):
        return None

    if not isinstance(header, dict) or not isinstance(claims, dict):
        return None
    if header.get("alg") != "RS256":
        return None

    try:
        keys = _jwks_for_issuer(issuer, fetcher=fetcher, jwks_cache=jwks_cache)
    except Exception:
        return None
    jwk = _select_jwk(keys, header.get("kid"))
    if not jwk or not _verify_rs256_signature(signing_input, signature, jwk):
        return None
    if not _claims_valid(claims, issuer=issuer, audience=audience, now=now):
        return None
    return dict(claims)


def _jwks_for_issuer(
    issuer: str,
    *,
    fetcher: OidcJsonFetcher,
    jwks_cache: dict[str, Any],
) -> list[Mapping[str, Any]]:
    if "keys" in jwks_cache:
        keys = jwks_cache.get("keys")
        return list(keys) if isinstance(keys, list) else []

    discovery = fetcher(f"{issuer}{_DISCOVERY_PATH}")
    if not isinstance(discovery, Mapping):
        return []
    jwks_uri = discovery.get("jwks_uri")
    if not isinstance(jwks_uri, str) or not jwks_uri.strip():
        return []
    jwks = fetcher(jwks_uri.strip())
    if not isinstance(jwks, Mapping):
        return []
    keys = jwks.get("keys")
    if not isinstance(keys, list):
        return []
    jwks_cache["keys"] = keys
    return list(keys)


def _select_jwk(keys: list[Mapping[str, Any]], kid: object) -> Mapping[str, Any] | None:
    if isinstance(kid, str) and kid:
        for key in keys:
            if key.get("kid") == kid:
                return key
        return None
    if len(keys) == 1:
        return keys[0]
    return None


def _verify_rs256_signature(signing_input: bytes, signature: bytes, jwk: Mapping[str, Any]) -> bool:
    if jwk.get("kty") != "RSA":
        return False
    modulus = _base64url_int(jwk.get("n"))
    exponent = _base64url_int(jwk.get("e"))
    if modulus is None or exponent is None or modulus <= 0 or exponent <= 0:
        return False

    key_length = (modulus.bit_length() + 7) // 8
    if len(signature) != key_length:
        return False
    try:
        verified_block = pow(int.from_bytes(signature, "big"), exponent, modulus).to_bytes(key_length, "big")
    except (OverflowError, ValueError):
        return False
    expected_block = _rs256_encoded_message(signing_input, key_length)
    return expected_block is not None and hmac.compare_digest(verified_block, expected_block)


def _rs256_encoded_message(signing_input: bytes, key_length: int) -> bytes | None:
    digest_info = _RS256_DIGEST_INFO_PREFIX + hashlib.sha256(signing_input).digest()
    padding_length = key_length - len(digest_info) - 3
    if padding_length < 8:
        return None
    return b"\x00\x01" + (b"\xff" * padding_length) + b"\x00" + digest_info


def _claims_valid(claims: Mapping[str, Any], *, issuer: str, audience: str, now: int) -> bool:
    token_issuer = claims.get("iss")
    if not isinstance(token_issuer, str) or token_issuer.rstrip("/") != issuer:
        return False
    if not _audience_matches(claims.get("aud"), audience):
        return False

    expires_at = _numeric_time(claims.get("exp"))
    if expires_at is None or now >= expires_at:
        return False
    not_before = _numeric_time(claims.get("nbf"))
    if not_before is not None and now < not_before:
        return False
    return True


def _audience_matches(value: Any, audience: str) -> bool:
    if isinstance(value, str):
        return value == audience
    if isinstance(value, list):
        return audience in [item for item in value if isinstance(item, str)]
    return False


def _numeric_time(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _base64url_int(value: object) -> int | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return int.from_bytes(_base64url_decode(value), "big")
    except (ValueError, TypeError):
        return None


def _fetch_json(url: str, *, timeout_seconds: float) -> Mapping[str, Any]:
    request = Request(url, headers={"Accept": "application/json"}, method="GET")
    with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310 - URL is trusted IdP config.
        payload = json.loads(response.read().decode("utf-8"))
    return payload if isinstance(payload, Mapping) else {}
