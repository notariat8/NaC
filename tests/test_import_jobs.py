from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_cli.import_jobs import apply_import_job_result, create_import_job, import_job_status, process_import_job  # noqa: E402


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class ImportJobTests(unittest.TestCase):
    def make_tenant_with_proposal(self, temp_dir: str) -> tuple[Path, str]:
        tenant_repo = Path(temp_dir) / "tenant"
        write_json(
            tenant_repo / ".nac-tenant.json",
            {
                "schema_version": "nac.tenant/v0.2",
                "name": "tenant",
                "mode": "demo",
            },
        )
        proposal_id = "IMP-20260521-UNTERSCHRIFTSBEGLAUBIGUNG-ERIKA"
        source = tenant_repo / "eingang" / "dateien" / proposal_id / "personalausweis-erika.jpg"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b"synthetic-image")
        write_json(
            tenant_repo / "eingang" / "import-vorschlaege" / f"{proposal_id}.json",
            {
                "schema_version": "nac.import-proposal/v0.1",
                "proposal_id": proposal_id,
                "status": "pending",
                "created_at": "2026-05-21T10:00:00Z",
                "source": "operator_upload",
                "source_type": "scan_image",
                "summary": "Personalausweis zur Identitätsprüfung für Erika Mustermann",
                "synthetic_test_data": True,
                "matter_values": {
                    "title": "Unterschriftsbeglaubigung Erika Mustermann",
                    "usecase_slug": "unterschriftsbeglaubigung",
                    "usecase_title": "Unterschriftsbeglaubigung",
                    "client_name": "Erika Mustermann",
                    "participant_name": "Erika Mustermann",
                    "document_title": "Personalausweis zur Identitätsprüfung",
                    "document_type": "id_document_scan",
                    "media_type": "image/jpeg",
                    "data_classification": "synthetic_identity_document",
                    "status": "open",
                    "metadata": {
                        "document_kind": "Personalausweis",
                        "document_number": "LZ6311T47",
                        "family_name": "Mustermann",
                        "given_names": "Erika",
                        "extraction_source": "synthetic_demo_profile",
                    },
                },
                "source_files": [
                    {
                        "label": "Vorderseite",
                        "filename": "personalausweis-erika.jpg",
                        "media_type": "image/jpeg",
                        "staged_path": f"eingang/dateien/{proposal_id}/personalausweis-erika.jpg",
                    }
                ],
                "review": {"requires_human_confirmation": True},
                "guardrails": {
                    "real_mandate_data_allowed": False,
                    "pin_or_card_data_allowed": False,
                    "secrets_allowed": False,
                },
            },
        )
        return tenant_repo, proposal_id

    def test_create_job_records_bounded_file_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tenant_repo, proposal_id = self.make_tenant_with_proposal(temp_dir)

            created = create_import_job(tenant_repo, proposal_id=proposal_id, requested_by="nac-local-operator-webapp")

            self.assertEqual(created["schema_version"], "nac.import-job/v0.1")
            self.assertEqual(created["proposal_id"], proposal_id)
            self.assertEqual(created["status"], "queued")
            self.assertEqual(created["action"], "ocr_metadata_extract")
            self.assertEqual(created["requested_by"], "nac-local-operator-webapp")
            self.assertEqual(created["guardrails"]["human_review_required"], True)
            self.assertEqual(created["input_files"][0]["path"], f"eingang/dateien/{proposal_id}/personalausweis-erika.jpg")
            self.assertTrue((tenant_repo / "eingang" / "jobs" / f"{created['job_id']}.json").is_file())

    def test_process_job_writes_extraction_without_accepting_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tenant_repo, proposal_id = self.make_tenant_with_proposal(temp_dir)
            job = create_import_job(tenant_repo, proposal_id=proposal_id, requested_by="codex")

            processed = process_import_job(tenant_repo, job_id=job["job_id"], processed_by="codex")

            self.assertEqual(processed["job"]["status"], "completed")
            self.assertEqual(processed["extraction"]["proposal_id"], proposal_id)
            self.assertEqual(processed["extraction"]["status"], "ready_for_review")
            self.assertEqual(processed["extraction"]["metadata"]["document_number"], "LZ6311T47")
            self.assertIn("Synthetische OCR-Zusammenfassung", processed["extraction"]["ocr_text"])
            proposal = json.loads((tenant_repo / "eingang" / "import-vorschlaege" / f"{proposal_id}.json").read_text(encoding="utf-8"))
            self.assertEqual(proposal["status"], "pending")
            self.assertNotIn("latest_extraction_job_id", proposal)

    def test_apply_result_merges_metadata_into_proposal_for_human_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tenant_repo, proposal_id = self.make_tenant_with_proposal(temp_dir)
            job = create_import_job(tenant_repo, proposal_id=proposal_id, requested_by="codex")
            process_import_job(tenant_repo, job_id=job["job_id"], processed_by="codex")

            applied = apply_import_job_result(tenant_repo, job_id=job["job_id"], applied_by="nac-local-operator-webapp")

            self.assertEqual(applied["job"]["status"], "applied")
            self.assertEqual(applied["proposal"]["proposal_id"], proposal_id)
            self.assertEqual(applied["proposal"]["matter_values"]["metadata"]["document_number"], "LZ6311T47")
            self.assertEqual(applied["proposal"]["matter_values"]["metadata"]["ocr_review_status"], "ready_for_human_review")
            self.assertEqual(applied["proposal"]["status"], "pending")
            self.assertEqual(applied["proposal"]["review"]["requires_human_confirmation"], True)

    def test_status_lists_jobs_and_extraction_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tenant_repo, proposal_id = self.make_tenant_with_proposal(temp_dir)
            job = create_import_job(tenant_repo, proposal_id=proposal_id, requested_by="codex")
            process_import_job(tenant_repo, job_id=job["job_id"], processed_by="codex")

            status = import_job_status(tenant_repo)

            self.assertEqual(status["counts"]["completed"], 1)
            self.assertEqual(status["jobs"][0]["job_id"], job["job_id"])
            self.assertEqual(status["jobs"][0]["proposal_id"], proposal_id)
            self.assertEqual(status["jobs"][0]["extraction"]["status"], "ready_for_review")


if __name__ == "__main__":
    unittest.main()
