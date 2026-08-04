from __future__ import annotations

import base64
import binascii
from collections.abc import Callable, Iterable, Mapping
import json
import math
import threading
import time
from typing import Any
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from .test_environment import ValidatedClaims


GENERIC_AUTHENTICATION_ERROR = "authentication failed"
MAX_CLOCK_SKEW_SECONDS = 300

_MAX_TOKEN_LENGTH = 32_768
_MAX_JSON_SEGMENT_LENGTH = 16_384
_MAX_JWKS_KEYS = 100
_MAX_CACHE_TTL_SECONDS = 86_400
_MIN_RSA_KEY_SIZE = 2_048
_MAX_RSA_KEY_SIZE = 8_192
MAX_JWKS_RESPONSE_BYTES = 262_144
MICROSOFT_LOGIN_HOSTS = frozenset({"login.microsoftonline.com"})
_BASE64URL_ALPHABET = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
)

JwksFetcher = Callable[[str], Mapping[str, Any]]
Clock = Callable[[], float]


class EntraAccessTokenValidationError(ValueError):
    """Generic external failure for every rejected bearer token."""


class _TokenRejected(Exception):
    pass


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class EntraAccessTokenValidator:
    """Validate delegated Entra v2 access tokens for the BFF boundary."""

    def __init__(
        self,
        *,
        expected_tenant_id: str,
        expected_audience: str,
        expected_issuer: str,
        required_scopes: Iterable[str] | None = None,
        required_roles: Iterable[str] | None = None,
        jwks_uri: str,
        jwks_fetcher: JwksFetcher | None = None,
        clock_skew_seconds: int = 60,
        jwks_cache_ttl_seconds: int = 300,
        timeout_seconds: float = 5.0,
        now: Clock | None = None,
    ) -> None:
        self._expected_tenant_id = _configuration_string(
            expected_tenant_id, "expected_tenant_id"
        )
        self._expected_audience = _configuration_string(
            expected_audience, "expected_audience"
        )
        self._expected_issuer = _configuration_string(
            expected_issuer, "expected_issuer"
        )
        if (required_scopes is None) == (required_roles is None):
            raise ValueError("exactly one delegated-scope or application-role policy is required")
        self._required_scopes = (
            _configuration_claim_values(required_scopes, "required_scopes")
            if required_scopes is not None
            else None
        )
        self._required_roles = (
            _configuration_claim_values(required_roles, "required_roles")
            if required_roles is not None
            else None
        )
        self._jwks_uri = _configuration_https_url(jwks_uri, "jwks_uri")

        if (
            isinstance(clock_skew_seconds, bool)
            or not isinstance(clock_skew_seconds, int)
            or not 0 <= clock_skew_seconds <= MAX_CLOCK_SKEW_SECONDS
        ):
            raise ValueError(
                f"clock_skew_seconds must be between 0 and {MAX_CLOCK_SKEW_SECONDS}"
            )
        if (
            isinstance(jwks_cache_ttl_seconds, bool)
            or not isinstance(jwks_cache_ttl_seconds, int)
            or not 1 <= jwks_cache_ttl_seconds <= _MAX_CACHE_TTL_SECONDS
        ):
            raise ValueError(
                f"jwks_cache_ttl_seconds must be between 1 and {_MAX_CACHE_TTL_SECONDS}"
            )
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(float(timeout_seconds))
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be a positive finite number")
        if jwks_fetcher is not None and not callable(jwks_fetcher):
            raise ValueError("jwks_fetcher must be callable")
        if now is not None and not callable(now):
            raise ValueError("now must be callable")

        self._clock_skew_seconds = clock_skew_seconds
        self._jwks_cache_ttl_seconds = jwks_cache_ttl_seconds
        self._now = now or time.time
        self._jwks_fetcher = jwks_fetcher or (
            lambda url: _fetch_json(url, timeout_seconds=float(timeout_seconds))
        )
        self._cache_lock = threading.Lock()
        self._cached_keys: tuple[Mapping[str, Any], ...] = ()
        self._cache_expires_at = 0.0

    def __call__(self, authorization_header: object) -> ValidatedClaims:
        return self.validate(authorization_header)

    def validate_authorization_header(
        self, authorization_header: object
    ) -> ValidatedClaims:
        return self.validate(authorization_header)

    def validate(self, authorization_header: object) -> ValidatedClaims:
        try:
            return self._validate(authorization_header)
        except Exception:
            # The boundary intentionally exposes neither token material nor the
            # reason that signature, key lookup or claims validation failed.
            raise EntraAccessTokenValidationError(
                GENERIC_AUTHENTICATION_ERROR
            ) from None

    def _validate(self, authorization_header: object) -> ValidatedClaims:
        token = _extract_bearer_token(authorization_header)
        header_segment, claims_segment, signature_segment = _split_token(token)
        header = _decode_json_object(header_segment)
        claims = _decode_json_object(claims_segment)

        if header.get("alg") != "RS256":
            raise _TokenRejected
        kid = _bounded_string(header.get("kid"))
        if kid is None:
            raise _TokenRejected

        now = _finite_clock_value(self._now())
        keys = self._get_jwks(now=now, force_refresh=False)
        jwk = _unique_key_for_kid(keys, kid)
        if jwk is None:
            keys = self._get_jwks(now=now, force_refresh=True)
            jwk = _unique_key_for_kid(keys, kid)
        if jwk is None:
            raise _TokenRejected

        signing_input = f"{header_segment}.{claims_segment}".encode("ascii")
        signature = _base64url_decode(signature_segment)
        _verify_rs256(signing_input, signature, jwk)
        return self._validated_claims(claims, now=now)

    def _get_jwks(
        self, *, now: float, force_refresh: bool
    ) -> tuple[Mapping[str, Any], ...]:
        with self._cache_lock:
            if (
                not force_refresh
                and self._cached_keys
                and now < self._cache_expires_at
            ):
                return self._cached_keys

            payload = self._jwks_fetcher(self._jwks_uri)
            if not isinstance(payload, Mapping):
                raise _TokenRejected
            raw_keys = payload.get("keys")
            if (
                not isinstance(raw_keys, list)
                or not raw_keys
                or len(raw_keys) > _MAX_JWKS_KEYS
                or not all(isinstance(key, Mapping) for key in raw_keys)
            ):
                raise _TokenRejected
            keys = tuple(dict(key) for key in raw_keys)
            self._cached_keys = keys
            self._cache_expires_at = now + self._jwks_cache_ttl_seconds
            return keys

    def _validated_claims(
        self, claims: Mapping[str, Any], *, now: float
    ) -> ValidatedClaims:
        tenant_id = _bounded_string(claims.get("tid"))
        object_id = _bounded_string(claims.get("oid"))
        if tenant_id != self._expected_tenant_id or object_id is None:
            raise _TokenRejected
        if claims.get("ver") != "2.0":
            raise _TokenRejected
        if claims.get("aud") != self._expected_audience:
            raise _TokenRejected
        if claims.get("iss") != self._expected_issuer:
            raise _TokenRejected

        if self._required_scopes is not None:
            scopes = _token_scopes(claims.get("scp"))
            if scopes is None or not self._required_scopes.issubset(scopes):
                raise _TokenRejected
            if claims.get("roles") is not None:
                raise _TokenRejected
        else:
            roles = _token_roles(claims.get("roles"))
            if roles is None or not self._required_roles.issubset(roles):
                raise _TokenRejected
            if claims.get("scp") is not None:
                raise _TokenRejected

        expires_at = _numeric_date(claims.get("exp"))
        not_before = _numeric_date(claims.get("nbf"))
        if expires_at is None or not_before is None or expires_at <= not_before:
            raise _TokenRejected
        if now >= expires_at + self._clock_skew_seconds:
            raise _TokenRejected
        if now + self._clock_skew_seconds < not_before:
            raise _TokenRejected

        # Entra oid is the stable actor identifier used by the BFF policy port.
        # No unvalidated browser or optional token claim enters this type.
        return ValidatedClaims(
            object_id=object_id,
            tenant_id=tenant_id,
            subject=object_id,
        )


def build_entra_access_token_validator(
    **kwargs: Any,
) -> EntraAccessTokenValidator:
    return EntraAccessTokenValidator(**kwargs)


def _configuration_string(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or value != value.strip()
        or not value
        or len(value) > 2_048
    ):
        raise ValueError(f"{name} must be a non-empty normalized string")
    return value


def _configuration_https_url(value: object, name: str) -> str:
    normalized = _configuration_string(value, name)
    try:
        parsed = urlsplit(normalized)
        port = parsed.port
    except ValueError:
        raise ValueError(f"{name} must be an allowed Microsoft HTTPS URL") from None
    if (
        parsed.scheme != "https"
        or parsed.hostname not in MICROSOFT_LOGIN_HOSTS
        or port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError(f"{name} must be an allowed Microsoft HTTPS URL")
    return normalized


def _configuration_claim_values(
    value: Iterable[str], name: str
) -> frozenset[str]:
    if isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must be an iterable of claim values")
    try:
        values = frozenset(value)
    except TypeError as exc:
        raise ValueError(f"{name} must be an iterable of claim values") from exc
    if not values or any(
        not isinstance(item, str)
        or not item
        or item != item.strip()
        or any(character.isspace() for character in item)
        or len(item) > 256
        for item in values
    ):
        raise ValueError(f"{name} contains an invalid claim value")
    return values


def _extract_bearer_token(authorization_header: object) -> str:
    if not isinstance(authorization_header, str):
        raise _TokenRejected
    parts = authorization_header.strip().split()
    if len(parts) != 2 or parts[0].casefold() != "bearer":
        raise _TokenRejected
    token = parts[1]
    if not token or len(token) > _MAX_TOKEN_LENGTH:
        raise _TokenRejected
    return token


def _split_token(token: str) -> tuple[str, str, str]:
    parts = token.split(".")
    if len(parts) != 3 or not all(parts):
        raise _TokenRejected
    return parts[0], parts[1], parts[2]


def _decode_json_object(segment: str) -> Mapping[str, Any]:
    if len(segment) > _MAX_JSON_SEGMENT_LENGTH:
        raise _TokenRejected
    try:
        payload = json.loads(
            _base64url_decode(segment).decode("utf-8"),
            object_pairs_hook=_unique_json_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise _TokenRejected from None
    if not isinstance(payload, Mapping):
        raise _TokenRejected
    return payload


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _TokenRejected
        result[key] = value
    return result


def _base64url_decode(value: str) -> bytes:
    if (
        not isinstance(value, str)
        or not value
        or any(character not in _BASE64URL_ALPHABET for character in value)
    ):
        raise _TokenRejected
    try:
        encoded = value.encode("ascii")
        return base64.b64decode(
            encoded + (b"=" * (-len(encoded) % 4)),
            altchars=b"-_",
            validate=True,
        )
    except (UnicodeEncodeError, binascii.Error, ValueError):
        raise _TokenRejected from None


def _base64url_integer(value: object) -> int:
    if not isinstance(value, str):
        raise _TokenRejected
    decoded = _base64url_decode(value)
    if not decoded:
        raise _TokenRejected
    return int.from_bytes(decoded, "big")


def _unique_key_for_kid(
    keys: tuple[Mapping[str, Any], ...], kid: str
) -> Mapping[str, Any] | None:
    matches = [key for key in keys if key.get("kid") == kid]
    if len(matches) > 1:
        raise _TokenRejected
    return matches[0] if matches else None


def _verify_rs256(
    signing_input: bytes, signature: bytes, jwk: Mapping[str, Any]
) -> None:
    if jwk.get("kty") != "RSA":
        raise _TokenRejected
    if jwk.get("use") not in (None, "sig"):
        raise _TokenRejected
    if jwk.get("alg") not in (None, "RS256"):
        raise _TokenRejected

    modulus = _base64url_integer(jwk.get("n"))
    exponent = _base64url_integer(jwk.get("e"))
    try:
        public_key = rsa.RSAPublicNumbers(exponent, modulus).public_key()
    except ValueError:
        raise _TokenRejected from None
    if not _MIN_RSA_KEY_SIZE <= public_key.key_size <= _MAX_RSA_KEY_SIZE:
        raise _TokenRejected
    try:
        public_key.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())
    except (InvalidSignature, ValueError):
        raise _TokenRejected from None


def _bounded_string(value: object) -> str | None:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > 256
    ):
        return None
    return value


def _token_scopes(value: object) -> frozenset[str] | None:
    if not isinstance(value, str) or not value or len(value) > 4_096:
        return None
    scopes = value.split(" ")
    if not scopes or any(
        not scope or len(scope) > 256 or any(character.isspace() for character in scope)
        for scope in scopes
    ):
        return None
    return frozenset(scopes)


def _token_roles(value: object) -> frozenset[str] | None:
    if not isinstance(value, list) or not 1 <= len(value) <= 64:
        return None
    if any(
        not isinstance(role, str)
        or not role
        or role != role.strip()
        or len(role) > 256
        or any(character.isspace() for character in role)
        for role in value
    ):
        return None
    roles = frozenset(value)
    return roles if len(roles) == len(value) else None


def _numeric_date(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def _finite_clock_value(value: object) -> float:
    numeric = _numeric_date(value)
    if numeric is None:
        raise _TokenRejected
    return numeric


def _fetch_json(url: str, *, timeout_seconds: float) -> Mapping[str, Any]:
    request = urllib.request.Request(
        url, headers={"Accept": "application/json"}, method="GET"
    )
    opener = urllib.request.build_opener(_NoRedirectHandler())
    # nosec B310 - configuration permits only fixed Microsoft login hosts.
    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            content_length = response.headers.get("Content-Length")
            if content_length is not None and _response_length_exceeds_limit(
                content_length, MAX_JWKS_RESPONSE_BYTES
            ):
                raise _TokenRejected
            raw = response.read(MAX_JWKS_RESPONSE_BYTES + 1)
            if len(raw) > MAX_JWKS_RESPONSE_BYTES:
                raise _TokenRejected
    except urllib.error.HTTPError as error:
        error.close()
        raise _TokenRejected from None
    payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_json_object)
    if not isinstance(payload, Mapping):
        raise _TokenRejected
    return payload


def _response_length_exceeds_limit(value: object, limit: int) -> bool:
    try:
        length = int(value)
    except (TypeError, ValueError):
        raise _TokenRejected from None
    return length < 0 or length > limit
