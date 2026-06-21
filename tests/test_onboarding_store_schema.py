from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "deploy" / "database" / "atp-onboarding-request-store.sql"


class OnboardingStoreSchemaTests(unittest.TestCase):
    def read_schema(self) -> str:
        self.assertTrue(SCHEMA_PATH.exists(), f"missing schema artifact: {SCHEMA_PATH}")
        return SCHEMA_PATH.read_text(encoding="utf-8")

    def test_atp_onboarding_request_schema_matches_request_contract(self) -> None:
        sql = self.read_schema()
        normalized = " ".join(sql.lower().split())

        required_terms = [
            "create table onboarding_requests",
            "request_id varchar2(96)",
            "tenant_id varchar2(128)",
            "tenant_slug varchar2(64)",
            "domain varchar2(253)",
            "admin_email varchar2(254)",
            "dns_status varchar2(32)",
            "request_status varchar2(32)",
            "invitation_status varchar2(32)",
            "created_at varchar2(32)",
            "updated_at varchar2(32)",
            "created_by_surface varchar2(128)",
            "constraint onboarding_requests_pk primary key (request_id)",
            "constraint onboarding_requests_dns_status_ck",
            "constraint onboarding_requests_request_status_ck",
            "constraint onboarding_requests_invitation_status_ck",
            "create index onboarding_requests_tenant_slug_i",
            "create index onboarding_requests_domain_i",
            "create index onboarding_requests_created_at_i",
        ]

        for term in required_terms:
            self.assertIn(term, normalized)

    def test_atp_session_schema_matches_multi_tenant_session_contract(self) -> None:
        sql = self.read_schema()
        normalized = " ".join(sql.lower().split())

        required_terms = [
            "create table nac_sessions",
            "session_id_hash varchar2(64)",
            "tenant_slug varchar2(80)",
            "subject_hash varchar2(128)",
            "role_class varchar2(80)",
            "usecase_slug varchar2(120)",
            "purpose varchar2(80)",
            "issued_at number(19)",
            "expires_at number(19)",
            "revoked_at number(19)",
            "audit_event_id varchar2(120)",
            "contains_credentials number(1)",
            "tokens_stored number(1)",
            "claims_stored number(1)",
            "constraint nac_sessions_pk primary key (session_id_hash)",
            "constraint nac_sessions_guardrails_ck",
            "create index nac_sessions_tenant_i",
            "create index nac_sessions_subject_i",
            "create index nac_sessions_expiry_i",
        ]

        for term in required_terms:
            self.assertIn(term, normalized)

    def test_schema_artifact_contains_no_secret_material(self) -> None:
        sql = self.read_schema().lower()

        forbidden_terms = [
            "password",
            "client_secret",
            "private key",
            "ocid1.user",
            "ocid1.tenancy",
            "begin rsa",
            "begin private key",
        ]

        for term in forbidden_terms:
            self.assertNotIn(term, sql)


if __name__ == "__main__":
    unittest.main()
