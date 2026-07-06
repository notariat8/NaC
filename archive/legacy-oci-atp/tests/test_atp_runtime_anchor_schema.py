from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "deploy" / "database" / "atp-runtime-anchor-schema.sql"


class AtpRuntimeAnchorSchemaTests(unittest.TestCase):
    def read_schema(self) -> str:
        self.assertTrue(SCHEMA_PATH.exists(), f"missing schema artifact: {SCHEMA_PATH}")
        return SCHEMA_PATH.read_text(encoding="utf-8")

    def test_anchor_schema_defines_runtime_metadata_tables(self) -> None:
        normalized = " ".join(self.read_schema().lower().split())

        required_terms = [
            "create table nac_tenants",
            "create table nac_user_bindings",
            "create table nac_matters",
            "create table nac_process_templates",
            "create table nac_process_instances",
            "create table nac_process_events",
            "create table nac_audit_events",
            "tenant_id varchar2(128)",
            "subject_hash varchar2(128)",
            "matter_id varchar2(128)",
            "process_template_id varchar2(128)",
            "process_instance_id varchar2(128)",
            "process_event_id varchar2(128)",
            "audit_event_id varchar2(128)",
            "payload_json clob check (payload_json is json)",
            "git_reference varchar2(240)",
            "duration_band varchar2(80)",
            "critical_path_status varchar2(80)",
        ]

        for term in required_terms:
            self.assertIn(term, normalized)

    def test_anchor_schema_preserves_tenant_boundary_and_append_events(self) -> None:
        normalized = " ".join(self.read_schema().lower().split())

        required_terms = [
            "constraint nac_user_bindings_tenant_fk foreign key (tenant_id)",
            "constraint nac_matters_tenant_fk foreign key (tenant_id)",
            "constraint nac_process_instances_tenant_fk foreign key (tenant_id)",
            "constraint nac_process_events_tenant_fk foreign key (tenant_id)",
            "constraint nac_audit_events_tenant_fk foreign key (tenant_id)",
            "create index nac_process_events_instance_i",
            "created_at varchar2(32) not null",
        ]

        for term in required_terms:
            self.assertIn(term, normalized)

        self.assertNotIn("updated_at varchar2(32) not null constraint nac_process_events", normalized)

    def test_anchor_schema_is_non_destructive_and_contains_no_sensitive_material(self) -> None:
        sql = self.read_schema().lower()

        forbidden_terms = [
            "drop table",
            "truncate",
            "delete from",
            "insert into",
            "password",
            "client_secret",
            "private key",
            "id_token",
            "access_token",
            "document_full_text",
            "raw_mandate",
            "personalausweis",
            "grundbuchdaten",
        ]

        for term in forbidden_terms:
            self.assertNotIn(term, sql)


if __name__ == "__main__":
    unittest.main()
