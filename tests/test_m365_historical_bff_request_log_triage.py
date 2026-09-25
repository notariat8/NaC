from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from contextlib import redirect_stdout

from src.nac_bff.bff_request_log_triage import (
    TriageBlocked,
    classify_synthetic_rows,
    load_triage_contract,
    run_offline_preflight,
    verify_receipt_pair,
)
from src.nac_cli.cli import main as nac_main


ROOT = Path(__file__).resolve().parents[1]
WINDOW_START = "2026-09-25T10:42:03.397Z"
WINDOW_END = "2026-09-25T10:42:10.487Z"


def _raw(value: dict[str, object]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _receipts() -> tuple[bytes, bytes]:
    base_core: dict[str, object] = {
        "end_utc": WINDOW_END,
        "request_correlation_binding_sha256": hashlib.sha256(b"synthetic-only").hexdigest(),
        "spfx_subject_available": True,
        "start_utc": WINDOW_START,
        "ui_state": "no_access",
    }
    base = _raw({**base_core, "window_binding_sha256": hashlib.sha256(_raw(base_core)).hexdigest()})
    http_core: dict[str, object] = {
        "base_receipt_sha256": hashlib.sha256(base).hexdigest(),
        "client_http_class": "403",
        "schema_version": "nac.client-http-observation/v0.1",
    }
    http = _raw({**http_core, "observation_binding_sha256": hashlib.sha256(_raw(http_core)).hexdigest()})
    return base, http


def _synthetic_contract(base: bytes, http: bytes) -> dict[str, object]:
    return {
        "base_receipt_sha256": hashlib.sha256(base).hexdigest(),
        "http_receipt_sha256": hashlib.sha256(http).hexdigest(),
        "window_start_utc": WINDOW_START,
        "window_end_utc": WINDOW_END,
    }


class BffRequestLogTriageTests(unittest.TestCase):
    def test_contract_is_offline_and_historical_contracts_remain_bound(self) -> None:
        contract = load_triage_contract(ROOT)
        self.assertEqual(contract["schema_version"], "nac.m365-bff-request-log-triage/v0.1")
        self.assertFalse(contract["provider_read_authorized"])
        self.assertFalse(contract["target_binding_proven"])
        self.assertFalse(contract["query_projection_proven"])
        self.assertFalse(contract["no_refresh_capability_proven"])
        self.assertEqual(contract["resource"]["method"], "GET")
        self.assertEqual(contract["resource"]["fixed_path_template"], "/v1/apps/{app_id}/query")
        self.assertEqual(contract["resource"]["maximum_reads"], 1)
        self.assertEqual(contract["resource"]["automatic_retries"], 0)
        self.assertEqual(contract["resource"]["follow_redirects"], False)

    def test_contract_rejects_receipt_or_historical_digest_drift(self) -> None:
        original = load_triage_contract(ROOT)
        relative_files = [
            "workflows/verification-contracts/m365-bff-request-log-triage.verification.json",
            *original["historical_contract_bindings"],
            *original["specifications"].values(),
            *original["plans"].values(),
            "docs/de/README.md",
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in relative_files:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / relative).read_bytes())
            contract_path = root / relative_files[0]
            for mutation in (
                lambda item: item["receipts"].update({"base_receipt_sha256": "0" * 64}),
                lambda item: item["historical_contract_bindings"].update({
                    "workflows/contracts/m365-current-state-read-driver-resources.contract.json": "0" * 64,
                }),
                lambda item: item["resource"].update({"automatic_retries": 1}),
                lambda item: item.update({"provider_read_authorized": True}),
                lambda item: item.update({"unreviewed_provider_port": "GET"}),
                lambda item: item["terminal_blockers"].remove("BLOCKED_TARGET_UNBOUND"),
                lambda item: item["specifications"].update({"de": "docs/de/README.md"}),
            ):
                with self.subTest(mutation=mutation):
                    changed = json.loads((ROOT / relative_files[0]).read_text(encoding="utf-8"))
                    mutation(changed)
                    contract_path.write_text(json.dumps(changed), encoding="utf-8")
                    with self.assertRaisesRegex(TriageBlocked, "BLOCKED_CONTRACT_INVALID"):
                        load_triage_contract(root)

    def test_receipt_pair_requires_exact_hashes_window_and_companion(self) -> None:
        base, http = _receipts()
        contract = _synthetic_contract(base, http)
        self.assertEqual(
            verify_receipt_pair(base, http, contract),
            hashlib.sha256(b"synthetic-only").hexdigest(),
        )
        for changed_base, changed_http, changed_contract in (
            (base + b" ", http, contract),
            (base, http + b" ", contract),
            (base, http, {**contract, "window_end_utc": "2026-09-25T10:42:10.488Z"}),
            (base, http, {**contract, "base_receipt_sha256": "0" * 64}),
        ):
            with self.subTest(changed_contract=changed_contract, changed_base=changed_base[-1:]):
                with self.assertRaises(TriageBlocked):
                    verify_receipt_pair(changed_base, changed_http, changed_contract)

    def test_synthetic_unique_403_is_narrow_and_ambiguous_matches_block(self) -> None:
        correlation = hashlib.sha256(b"synthetic-only").hexdigest()
        row = {
            "request_correlation_binding_sha256": correlation,
            "http_class": "403",
            "method": "GET",
            "path_class": "workbench_snapshot",
            "timestamp_utc": "2026-09-25T10:42:05.000Z",
        }
        result = classify_synthetic_rows([row], expected_correlation_sha256=correlation)
        self.assertEqual(result, {
            "request_observed": True,
            "http_class": "403",
            "request_correlation_binding_sha256": correlation,
        })
        for rows in (
            [],
            [row, row],
            [{**row, "request_correlation_binding_sha256": "0" * 64}],
            [{**row, "http_class": "401"}],
            [{**row, "method": "POST"}],
            [{**row, "raw_url": "synthetic-forbidden"}],
            [{**row, "path_class": "other"}],
            [{**row, "timestamp_utc": "2026-09-25T10:42:10.488Z"}],
        ):
            with self.subTest(rows=rows):
                with self.assertRaises(TriageBlocked):
                    classify_synthetic_rows(rows, expected_correlation_sha256=correlation)

    def test_offline_preflight_never_constructs_provider_or_credentials(self) -> None:
        credential_provider = Mock(side_effect=AssertionError("credential access"))
        transport_provider = Mock(side_effect=AssertionError("network access"))
        result = run_offline_preflight(
            repo_root=ROOT,
            input_root=None,
            credential_provider=credential_provider,
            transport_provider=transport_provider,
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason_code"], "BLOCKED_INPUTS_REQUIRED")
        self.assertEqual(result["network_reads"], 0)
        self.assertEqual(result["credential_reads"], 0)
        self.assertFalse(result["provider_read_authorized"])
        credential_provider.assert_not_called()
        transport_provider.assert_not_called()

    def test_protected_receipts_still_stop_at_unproven_target(self) -> None:
        base, http = _receipts()
        session = Mock()
        session.read_bounded.side_effect = [base, http]
        backend = Mock()
        backend.open_secure_directory.return_value = session
        credential_provider = Mock(side_effect=AssertionError("credential access"))
        transport_provider = Mock(side_effect=AssertionError("network access"))
        with tempfile.TemporaryDirectory() as directory:
            with patch(
                "src.nac_bff.bff_request_log_triage.load_triage_contract",
                return_value={"receipts": _synthetic_contract(base, http)},
            ):
                result = run_offline_preflight(
                    repo_root=ROOT,
                    input_root=Path(directory),
                    backend=backend,
                    credential_provider=credential_provider,
                    transport_provider=transport_provider,
                )
        self.assertEqual(result["reason_code"], "BLOCKED_TARGET_UNBOUND")
        self.assertEqual(session.read_bounded.call_count, 2)
        session.read_bounded.assert_any_call("client-observation-receipt.json", 16 * 1024)
        session.read_bounded.assert_any_call("client-http-observation.json", 1024)
        session.close.assert_called_once()
        credential_provider.assert_not_called()
        transport_provider.assert_not_called()

    def test_cli_exposes_only_offline_triage_preflight(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            code = nac_main([
                "--repo-root", str(ROOT), "m365", "teams-sharepoint",
                "bff-request-log-triage-preflight", "--format", "json",
            ])
        self.assertEqual(code, 2)
        result = json.loads(output.getvalue())
        self.assertEqual(result["reason_code"], "BLOCKED_INPUTS_REQUIRED")
        self.assertFalse(result["provider_read_authorized"])
        self.assertEqual(result["network_reads"], 0)
        self.assertEqual(result["credential_reads"], 0)

        forbidden = "https://synthetic.example.invalid/private"
        output = io.StringIO()
        with redirect_stdout(output):
            code = nac_main([
                "--repo-root", str(ROOT), "m365", "teams-sharepoint",
                "bff-request-log-triage-preflight", "--format", "json",
                "--bff-triage-query", forbidden,
            ])
        self.assertEqual(code, 2)
        self.assertNotIn(forbidden, output.getvalue())
        blocked = json.loads(output.getvalue())
        self.assertEqual(blocked["status"], "BLOCKED")
        self.assertEqual(blocked["reason_code"], "BLOCKED_ARGUMENTS")
        self.assertEqual(blocked["schema_version"], "nac.m365-bff-request-log-triage-preflight/v0.1")


if __name__ == "__main__":
    unittest.main()
