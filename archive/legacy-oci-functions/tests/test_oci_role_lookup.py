from __future__ import annotations

import unittest
import sys
from pathlib import Path
from urllib.error import HTTPError

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_identity.oci_role_lookup import build_oci_identity_domain_role_membership_resolver


class OciRoleLookupTests(unittest.TestCase):
    def test_rejects_placeholder_identity_domain_url(self) -> None:
        resolver = build_oci_identity_domain_role_membership_resolver(
            identity_domain_url="https://idcs.example.identity.oraclecloud.com:443",
            fetcher=lambda _url: {},
        )

        self.assertIsNone(resolver)

    def test_confirms_role_from_identity_domain_group_membership(self) -> None:
        seen_urls: list[str] = []

        def fetcher(url: str):
            seen_urls.append(url)
            if "/Users?" in url:
                return {
                    "Resources": [
                        {
                            "id": "user-123",
                            "userName": "admin@example.test",
                        }
                    ]
                }
            if "/Groups?" in url:
                return {
                    "Resources": [
                        {
                            "displayName": "nac-tenant-admin",
                            "members": [{"value": "user-123"}],
                        }
                    ]
                }
            return {}

        resolver = build_oci_identity_domain_role_membership_resolver(
            identity_domain_url="https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
            fetcher=fetcher,
        )

        result = resolver(
            claims={"sub": "user-123", "email": "admin@example.test"},
            required_role="nac-tenant-admin",
        )

        self.assertEqual(result["status"], "confirmed")
        self.assertEqual(result["role"], "nac-tenant-admin")
        self.assertEqual(result["source"], "oci_identity_domain_server_lookup")
        self.assertFalse(result["contains_credentials"])
        self.assertFalse(result["tokens_returned"])
        self.assertFalse(result["claims_exposed"])
        self.assertTrue(any("/Users?" in url for url in seen_urls))
        self.assertTrue(any("/Groups?" in url for url in seen_urls))
        serialized_urls = "\n".join(seen_urls)
        self.assertIn("filter=", serialized_urls)
        self.assertNotIn("admin@example.test", str(result))

    def test_confirms_role_from_user_groups_requested_explicitly(self) -> None:
        seen_urls: list[str] = []

        def fetcher(url: str):
            seen_urls.append(url)
            if "/Users?" in url and "attributes=" in url and "groups" in url:
                return {
                    "Resources": [
                        {
                            "id": "user-123",
                            "userName": "admin@example.test",
                            "groups": [{"display": "nac-tenant-admin"}],
                        }
                    ]
                }
            if "/Users?" in url:
                return {"Resources": [{"id": "user-123", "userName": "admin@example.test"}]}
            if "/Groups?" in url:
                return {"Resources": []}
            return {}

        resolver = build_oci_identity_domain_role_membership_resolver(
            identity_domain_url="https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
            fetcher=fetcher,
        )

        result = resolver(
            claims={"sub": "provider-subject", "email": "admin@example.test"},
            required_role="nac-tenant-admin",
        )

        self.assertEqual(result["status"], "confirmed")
        serialized_urls = "\n".join(seen_urls)
        self.assertIn("attributes=", serialized_urls)
        self.assertIn("groups", serialized_urls)
        self.assertNotIn("provider-subject", str(result))
        self.assertNotIn("admin@example.test", str(result))

    def test_confirms_role_when_subject_is_oci_user_ocid(self) -> None:
        seen_urls: list[str] = []

        def fetcher(url: str):
            seen_urls.append(url)
            if "filter=id+eq" in url:
                return {"Resources": []}
            if "filter=ocid+eq" in url:
                return {
                    "Resources": [
                        {
                            "id": "user-123",
                            "ocid": "ocid1.user.oc1..tenantadmin",
                            "groups": [{"display": "nac-tenant-admin"}],
                        }
                    ]
                }
            return {}

        resolver = build_oci_identity_domain_role_membership_resolver(
            identity_domain_url="https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
            fetcher=fetcher,
        )

        result = resolver(
            claims={"sub": "ocid1.user.oc1..tenantadmin"},
            required_role="nac-tenant-admin",
        )

        self.assertEqual(result["status"], "confirmed")
        self.assertEqual(result["role"], "nac-tenant-admin")
        serialized_urls = "\n".join(seen_urls)
        self.assertIn("filter=id+eq", serialized_urls)
        self.assertIn("filter=ocid+eq", serialized_urls)
        self.assertNotIn("ocid1.user", str(result))

    def test_confirms_role_from_group_detail_when_search_omits_members(self) -> None:
        seen_urls: list[str] = []

        def fetcher(url: str):
            seen_urls.append(url)
            if "/Users?" in url:
                return {
                    "Resources": [
                        {
                            "id": "user-123",
                            "userName": "admin@example.test",
                        }
                    ]
                }
            if "/Groups?" in url:
                return {
                    "Resources": [
                        {
                            "id": "group-123",
                            "displayName": "nac-tenant-admin",
                            "members": None,
                        }
                    ]
                }
            if "/Groups/group-123" in url:
                return {
                    "id": "group-123",
                    "displayName": "nac-tenant-admin",
                    "members": [{"value": "user-123"}],
                }
            return {}

        resolver = build_oci_identity_domain_role_membership_resolver(
            identity_domain_url="https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
            fetcher=fetcher,
        )

        result = resolver(
            claims={"sub": "provider-subject", "email": "admin@example.test"},
            required_role="nac-tenant-admin",
        )

        self.assertEqual(result["status"], "confirmed")
        self.assertTrue(any("/Groups/group-123" in url for url in seen_urls))
        self.assertNotIn("group-123", str(result))

    def test_confirms_role_from_user_app_roles_without_exposing_claims(self) -> None:
        def fetcher(url: str):
            if "/Users?" in url:
                return {
                    "Resources": [
                        {
                            "id": "user-123",
                            "urn:ietf:params:scim:schemas:oracle:idcs:extension:user:User": {
                                "appRoles": [{"display": "nac-tenant-admin"}],
                            },
                        }
                    ]
                }
            return {}

        resolver = build_oci_identity_domain_role_membership_resolver(
            identity_domain_url="https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
            fetcher=fetcher,
        )

        result = resolver(
            claims={"sub": "user-123", "email": "admin@example.test"},
            required_role="nac-tenant-admin",
        )

        self.assertEqual(result["status"], "confirmed")
        self.assertNotIn("user-123", str(result))
        self.assertNotIn("admin@example.test", str(result))

    def test_fails_closed_when_identity_domain_lookup_is_unavailable(self) -> None:
        def fetcher(_url: str):
            raise RuntimeError("network detail should not escape")

        resolver = build_oci_identity_domain_role_membership_resolver(
            identity_domain_url="https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
            fetcher=fetcher,
        )

        result = resolver(
            claims={"sub": "user-123", "email": "admin@example.test"},
            required_role="nac-tenant-admin",
        )

        self.assertEqual(result["status"], "unavailable")
        self.assertFalse(result["contains_credentials"])
        self.assertNotIn("network detail", str(result))
        self.assertNotIn("user-123", str(result))
        self.assertNotIn("admin@example.test", str(result))

    def test_reports_redacted_http_failure_class_when_identity_domain_forbidden(self) -> None:
        def fetcher(_url: str):
            raise HTTPError(
                "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com/admin/v1/Users",
                403,
                "forbidden detail should not escape",
                hdrs=None,
                fp=None,
            )

        resolver = build_oci_identity_domain_role_membership_resolver(
            identity_domain_url="https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
            fetcher=fetcher,
        )

        result = resolver(
            claims={"sub": "user-123", "email": "admin@example.test"},
            required_role="nac-tenant-admin",
        )

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["failure_class"], "identity_domain_forbidden")
        self.assertNotIn("forbidden detail", str(result))
        self.assertNotIn("idcs.example", str(result))
        self.assertNotIn("user-123", str(result))
        self.assertNotIn("admin@example.test", str(result))

    def test_rejects_non_identity_domain_url(self) -> None:
        resolver = build_oci_identity_domain_role_membership_resolver(
            identity_domain_url="https://example.test",
            fetcher=lambda _url: {},
        )

        self.assertIsNone(resolver)


if __name__ == "__main__":
    unittest.main()
