from __future__ import annotations

import base64
import io
import json
from pathlib import Path
import sys
import unittest
import urllib.error
from unittest.mock import patch

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_bff.entra_access_token import (  # noqa: E402
    GENERIC_AUTHENTICATION_ERROR,
    MAX_JWKS_RESPONSE_BYTES,
    EntraAccessTokenValidationError,
    EntraAccessTokenValidator,
)


NOW = 1_750_000_000
TENANT_ID = "11111111-2222-3333-4444-555555555555"
OBJECT_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
AUDIENCE = "api://nac-bff"
ISSUER = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"
JWKS_URI = "https://login.microsoftonline.com/common/discovery/v2.0/keys"
REQUIRED_SCOPE = "Matter.Read"


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _integer_b64url(value: int) -> str:
    return _b64url(value.to_bytes((value.bit_length() + 7) // 8, "big"))


def _jwk(key: rsa.RSAPrivateKey, kid: str) -> dict[str, str]:
    numbers = key.public_key().public_numbers()
    return {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": kid,
        "n": _integer_b64url(numbers.n),
        "e": _integer_b64url(numbers.e),
    }


def _claims(**overrides: object) -> dict[str, object]:
    claims: dict[str, object] = {
        "tid": TENANT_ID,
        "oid": OBJECT_ID,
        "scp": f"openid {REQUIRED_SCOPE}",
        "ver": "2.0",
        "aud": AUDIENCE,
        "iss": ISSUER,
        "exp": NOW + 300,
        "nbf": NOW - 300,
    }
    claims.update(overrides)
    return claims


def _token(
    key: rsa.RSAPrivateKey,
    *,
    kid: str = "key-1",
    claims: dict[str, object] | None = None,
    algorithm: str = "RS256",
) -> str:
    header_segment = _b64url(
        json.dumps({"alg": algorithm, "kid": kid, "typ": "JWT"}, separators=(",", ":")).encode()
    )
    claims_segment = _b64url(
        json.dumps(_claims() if claims is None else claims, separators=(",", ":")).encode()
    )
    signing_input = f"{header_segment}.{claims_segment}".encode("ascii")
    signature = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return f"{header_segment}.{claims_segment}.{_b64url(signature)}"


class _JwksFetcher:
    def __init__(self, *responses: object) -> None:
        self.responses = list(responses)
        self.calls: list[str] = []

    def __call__(self, url: str) -> dict[str, object]:
        self.calls.append(url)
        index = min(len(self.calls) - 1, len(self.responses) - 1)
        response = self.responses[index]
        if isinstance(response, Exception):
            raise response
        if not isinstance(response, dict):
            raise TypeError("test response must be a dictionary")
        return response


class _HttpResponse:
    def __init__(self, raw: bytes, *, headers: dict[str, str] | None = None) -> None:
        self.raw = raw
        self.headers = {} if headers is None else headers
        self.read_limits: list[int] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self, limit: int) -> bytes:
        self.read_limits.append(limit)
        return self.raw[:limit]


class _HttpOpener:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[tuple[object, float]] = []

    def open(self, request, timeout: float):
        self.calls.append((request, timeout))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class EntraAccessTokenValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.key_1 = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.key_2 = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def _validator(
        self,
        fetcher: _JwksFetcher | None = None,
        *,
        now: list[float] | None = None,
        clock_skew_seconds: int = 60,
        cache_ttl_seconds: int = 300,
    ) -> EntraAccessTokenValidator:
        clock = [float(NOW)] if now is None else now
        return EntraAccessTokenValidator(
            expected_tenant_id=TENANT_ID,
            expected_audience=AUDIENCE,
            expected_issuer=ISSUER,
            required_scopes={REQUIRED_SCOPE},
            jwks_uri=JWKS_URI,
            jwks_fetcher=fetcher or _JwksFetcher({"keys": [_jwk(self.key_1, "key-1")]}),
            clock_skew_seconds=clock_skew_seconds,
            jwks_cache_ttl_seconds=cache_ttl_seconds,
            now=lambda: clock[0],
        )

    def _network_validator(self) -> EntraAccessTokenValidator:
        return EntraAccessTokenValidator(
            expected_tenant_id=TENANT_ID,
            expected_audience=AUDIENCE,
            expected_issuer=ISSUER,
            required_scopes={REQUIRED_SCOPE},
            jwks_uri=JWKS_URI,
            now=lambda: float(NOW),
        )

    def assertRejected(
        self,
        validator: EntraAccessTokenValidator,
        authorization_header: object,
    ) -> None:
        with self.assertRaises(EntraAccessTokenValidationError) as caught:
            validator.validate(authorization_header)
        self.assertEqual(str(caught.exception), GENERIC_AUTHENTICATION_ERROR)
        if isinstance(authorization_header, str) and authorization_header:
            self.assertNotIn(authorization_header, str(caught.exception))
            self.assertNotIn(authorization_header, repr(caught.exception))

    def test_valid_bearer_token_returns_only_validated_identity_claims(self) -> None:
        fetcher = _JwksFetcher({"keys": [_jwk(self.key_1, "key-1")]})
        validator = self._validator(fetcher)

        result = validator.validate(f"Bearer {_token(self.key_1)}")

        self.assertEqual(result.object_id, OBJECT_ID)
        self.assertEqual(result.tenant_id, TENANT_ID)
        self.assertEqual(result.subject, OBJECT_ID)
        self.assertEqual(fetcher.calls, [JWKS_URI])

    def test_bearer_scheme_is_case_insensitive_but_header_shape_is_strict(self) -> None:
        validator = self._validator()
        result = validator("bearer " + _token(self.key_1))
        self.assertEqual(result.object_id, OBJECT_ID)

        for header in (
            None,
            42,
            "",
            "Bearer",
            "Basic abc",
            "Bearer one two",
            "Bearer not-a-jwt",
        ):
            with self.subTest(header=header):
                self.assertRejected(self._validator(), header)

    def test_every_required_claim_is_fail_closed_when_missing(self) -> None:
        for claim_name in ("tid", "oid", "scp", "ver", "aud", "iss", "exp", "nbf"):
            with self.subTest(claim=claim_name):
                claims = _claims()
                del claims[claim_name]
                self.assertRejected(
                    self._validator(),
                    "Bearer " + _token(self.key_1, claims=claims),
                )

    def test_identity_scope_and_protocol_claims_must_match_exactly(self) -> None:
        invalid_claims = {
            "tenant": _claims(tid="other-tenant"),
            "object_id_empty": _claims(oid=""),
            "object_id_non_string": _claims(oid=123),
            "scope_missing": _claims(scp="openid profile"),
            "scope_non_string": _claims(scp=[REQUIRED_SCOPE]),
            "version": _claims(ver="1.0"),
            "audience": _claims(aud="api://other"),
            "audience_list": _claims(aud=[AUDIENCE]),
            "issuer": _claims(iss=ISSUER + "/"),
        }
        for label, claims in invalid_claims.items():
            with self.subTest(label=label):
                self.assertRejected(
                    self._validator(),
                    "Bearer " + _token(self.key_1, claims=claims),
                )

    def test_expiration_and_not_before_use_only_the_bounded_clock_skew(self) -> None:
        validator = self._validator(clock_skew_seconds=60)
        accepted = (
            _claims(exp=NOW - 59),
            _claims(nbf=NOW + 60),
        )
        rejected = (
            _claims(exp=NOW - 60),
            _claims(nbf=NOW + 61),
            _claims(exp=True),
            _claims(nbf="1749999999"),
        )

        for claims in accepted:
            with self.subTest(accepted=claims):
                result = validator.validate("Bearer " + _token(self.key_1, claims=claims))
                self.assertEqual(result.object_id, OBJECT_ID)
        for claims in rejected:
            with self.subTest(rejected=claims):
                self.assertRejected(
                    self._validator(clock_skew_seconds=60),
                    "Bearer " + _token(self.key_1, claims=claims),
                )

    def test_non_rs256_tampered_and_wrong_key_signatures_are_rejected(self) -> None:
        valid = _token(self.key_1)
        header, payload, signature = valid.split(".")
        tampered_payload = _b64url(json.dumps(_claims(oid="attacker")).encode())
        cases = (
            _token(self.key_1, algorithm="HS256"),
            f"{header}.{tampered_payload}.{signature}",
            _token(self.key_2),
            f"{header}.{payload}.{_b64url(b'invalid-signature')}",
        )
        for token in cases:
            with self.subTest(token_shape=tuple(len(part) for part in token.split("."))):
                self.assertRejected(self._validator(), "Bearer " + token)

    def test_malformed_jwt_jwks_and_fetch_failures_share_the_generic_error(self) -> None:
        for malformed_jwt in (
            "Bearer !!!!.!!!!.!!!!",
            "Bearer ++++.e30.AAAA",
            "Bearer e30=.e30.AAAA",
        ):
            self.assertRejected(self._validator(), malformed_jwt)

        invalid_sets = (
            {},
            {"keys": "not-a-list"},
            {"keys": []},
            {"keys": [{**_jwk(self.key_1, "key-1"), "kty": "EC"}]},
            {"keys": [{**_jwk(self.key_1, "key-1"), "use": "enc"}]},
            {"keys": [{**_jwk(self.key_1, "key-1"), "alg": "RS512"}]},
            {"keys": [{**_jwk(self.key_1, "key-1"), "n": "!"}]},
        )
        for jwks in invalid_sets:
            with self.subTest(jwks=jwks):
                self.assertRejected(
                    self._validator(_JwksFetcher(jwks)),
                    "Bearer " + _token(self.key_1),
                )
        self.assertRejected(
            self._validator(_JwksFetcher(RuntimeError("offline"))),
            "Bearer " + _token(self.key_1),
        )

    def test_default_jwks_fetch_rejects_redirect_without_following_it(self) -> None:
        redirect = urllib.error.HTTPError(
            JWKS_URI,
            302,
            "offline redirect",
            {"Location": "https://example.invalid/keys"},
            io.BytesIO(b"redirect body"),
        )
        opener = _HttpOpener(redirect)

        with patch(
            "nac_bff.entra_access_token.urllib.request.build_opener",
            return_value=opener,
        ) as build_opener:
            self.assertRejected(
                self._network_validator(),
                "Bearer " + _token(self.key_1),
            )

        self.assertEqual(len(opener.calls), 1)
        self.assertEqual(opener.calls[0][0].full_url, JWKS_URI)
        self.assertTrue(redirect.fp.closed)
        redirect_handler = build_opener.call_args.args[0]
        self.assertIsNone(
            redirect_handler.redirect_request(
                opener.calls[0][0], None, 302, "redirect", {}, "https://example.invalid"
            )
        )

    def test_default_jwks_fetch_uses_a_bounded_read(self) -> None:
        response = _HttpResponse(b"x" * (MAX_JWKS_RESPONSE_BYTES + 1))
        opener = _HttpOpener(response)

        with patch(
            "nac_bff.entra_access_token.urllib.request.build_opener",
            return_value=opener,
        ):
            self.assertRejected(
                self._network_validator(),
                "Bearer " + _token(self.key_1),
            )

        self.assertEqual(response.read_limits, [MAX_JWKS_RESPONSE_BYTES + 1])
        self.assertEqual(len(opener.calls), 1)

    def test_cached_jwks_is_reused_until_ttl_expires(self) -> None:
        clock = [float(NOW)]
        fetcher = _JwksFetcher(
            {"keys": [_jwk(self.key_1, "key-1")]},
            {"keys": [_jwk(self.key_1, "key-1")]},
        )
        validator = self._validator(fetcher, now=clock, cache_ttl_seconds=300)
        header = "Bearer " + _token(self.key_1, claims=_claims(exp=NOW + 1_000))

        validator.validate(header)
        clock[0] += 299
        validator.validate(header)
        self.assertEqual(len(fetcher.calls), 1)

        clock[0] += 1
        validator.validate(header)
        self.assertEqual(fetcher.calls, [JWKS_URI, JWKS_URI])

    def test_unknown_kid_forces_exactly_one_refresh_and_accepts_rotated_key(self) -> None:
        fetcher = _JwksFetcher(
            {"keys": [_jwk(self.key_1, "key-1")]},
            {"keys": [_jwk(self.key_2, "key-2")]},
        )
        validator = self._validator(fetcher)
        validator.validate("Bearer " + _token(self.key_1))

        result = validator.validate("Bearer " + _token(self.key_2, kid="key-2"))

        self.assertEqual(result.object_id, OBJECT_ID)
        self.assertEqual(fetcher.calls, [JWKS_URI, JWKS_URI])

    def test_unknown_kid_is_rejected_after_one_refresh(self) -> None:
        fetcher = _JwksFetcher(
            {"keys": [_jwk(self.key_1, "key-1")]},
            {"keys": [_jwk(self.key_1, "key-1")]},
            AssertionError("a second refresh must not happen"),
        )
        validator = self._validator(fetcher)
        validator.validate("Bearer " + _token(self.key_1))

        self.assertRejected(
            validator,
            "Bearer " + _token(self.key_2, kid="unknown-key"),
        )
        self.assertEqual(fetcher.calls, [JWKS_URI, JWKS_URI])

    def test_invalid_configuration_is_rejected_before_any_token_is_processed(self) -> None:
        base = {
            "expected_tenant_id": TENANT_ID,
            "expected_audience": AUDIENCE,
            "expected_issuer": ISSUER,
            "required_scopes": {REQUIRED_SCOPE},
            "jwks_uri": JWKS_URI,
            "jwks_fetcher": _JwksFetcher({"keys": [_jwk(self.key_1, "key-1")]}),
        }
        invalid_overrides = (
            {"expected_tenant_id": ""},
            {"expected_audience": ""},
            {"expected_issuer": ""},
            {"required_scopes": set()},
            {"required_scopes": {"bad scope"}},
            {"jwks_uri": ""},
            {"jwks_uri": "http://login.microsoftonline.com/common/keys"},
            {"jwks_uri": "https://login.microsoftonline.com:443/common/keys"},
            {"jwks_uri": "https://login.microsoftonline.com.example.invalid/keys"},
            {"jwks_uri": "https://login.windows.net/common/keys"},
            {"jwks_uri": "https://example.invalid/keys"},
            {"clock_skew_seconds": -1},
            {"clock_skew_seconds": 301},
            {"jwks_cache_ttl_seconds": 0},
        )
        for overrides in invalid_overrides:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    EntraAccessTokenValidator(**(base | overrides))


if __name__ == "__main__":
    unittest.main()
