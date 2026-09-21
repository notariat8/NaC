from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
import hashlib
import hmac
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nac_bff.current_state_access_diagnostic import (
    BFF_AUTHENTICATION_REJECTED_401,
    BFF_AUTHORIZATION_REJECTED_403,
    BFF_REQUEST_NOT_OBSERVED,
    SPFX_SUBJECT_MISSING,
    AcquisitionEnvelope,
    DiagnosticBlockedError,
    build_decision_projection,
    build_snapshot,
    classify_observations,
    compare_snapshots,
)
from nac_bff.current_state_access_adapters import (
    AzureFunctionMetadataReadAdapter,
    AzureFunctionRequestLogReadAdapter,
    ClientObservationReceiptAdapter,
    EntraApiPermissionReadAdapter,
    SharePointAccessDecisionReadAdapter,
    SharePointAppCatalogReadAdapter,
    TeamsTabMetadataReadAdapter,
    TransportPolicy,
)
from nac_bff.current_state_access_composition import (
    run_current_state_access_diagnostic_from_protected_inputs,
    run_double_snapshot_diagnostic,
)
from nac_bff.current_state_access_gate import (
    GateInput,
    authorize_synthetic_current_state_run,
)
from nac_bff.current_state_access_ports import CurrentStateAccessPorts


def _observations(**overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "spfx_subject_available": True,
        "matching_bff_request_observed": False,
        "bff_http_class": "none",
        "delegated_scope_contract_matches": True,
        "access_decision_evidence_matches": True,
    }
    result.update(overrides)
    return result


def _projection(observations: dict[str, object]):
    network_reads = 2 if observations["spfx_subject_available"] is False else 6
    return build_decision_projection(
        target={"workspace_id": "notary_team_01", "app_id": "nac-vorgangsansicht"},
        bindings={
            "final_head_sha256": "a" * 64,
            "final_tree_sha256": "b" * 64,
            "contract_sha256": "c" * 64,
            "resolver_sha256": "d" * 64,
            "account_run_binding": "opaque-account",
            "principal_run_binding": "opaque-principal",
            "dpa_avv_binding_sha256": "e" * 64,
        },
        observation_window={
            "start_utc": "2026-09-20T08:00:00Z",
            "end_utc": "2026-09-20T08:05:00Z",
            "window_binding_sha256": "f" * 64,
            "client_receipt_sha256": "1" * 64,
            "request_correlation_binding_sha256": "2" * 64,
        },
        observations=observations,
        side_effect_counters={
            "port_factory": 1,
            "network_read": network_reads,
            "run_gate_consume_write": 1,
            "result_evidence_write": 1,
            "login": 0,
            "device_code": 0,
            "browser_authentication": 0,
            "token_refresh": 0,
            "token_import": 0,
            "credential_export": 0,
            "credential_write": 0,
            "cache_write": 0,
            "configuration_write": 0,
            "redirect_follow": 0,
            "retry": 0,
            "second_real_run": 0,
            "tenant_write": 0,
            "provider_write": 0,
            "deployment": 0,
            "issue_739_release": 0,
            "issue_632_authorization": 0,
        },
    )


def _port_receipts(prefix: int) -> tuple[str, ...]:
    return tuple(f"{prefix + index:064x}" for index in range(7))


class CurrentStateAccessDiagnosticTests(unittest.TestCase):
    def test_scope_filter_ignores_only_generated_egg_info_worktree_paths(self) -> None:
        scripts_path = str(Path(__file__).resolve().parents[1] / "scripts")
        if scripts_path not in sys.path:
            sys.path.insert(0, scripts_path)
        import validate_m365_current_state_access_diagnostic as validator

        filtered = validator._filter_generated_worktree_artifacts(
            {
                "src/nac.egg-info/PKG-INFO",
                "src/nac.egg-info/SOURCES.txt",
                "src/nac.egg-info/unexpected.txt",
                "src/nac_bff/current_state_access_gate.py",
                "unexpected.txt",
            }
        )

        self.assertEqual(
            filtered,
            {
                "src/nac.egg-info/unexpected.txt",
                "src/nac_bff/current_state_access_gate.py",
                "unexpected.txt",
            },
        )

    def test_exact_four_classifications(self) -> None:
        cases = (
            (_observations(spfx_subject_available=False), SPFX_SUBJECT_MISSING),
            (_observations(), BFF_REQUEST_NOT_OBSERVED),
            (_observations(matching_bff_request_observed=True, bff_http_class="401"), BFF_AUTHENTICATION_REJECTED_401),
            (_observations(matching_bff_request_observed=True, bff_http_class="403"), BFF_AUTHORIZATION_REJECTED_403),
        )
        for observations, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(classify_observations(observations), expected)

    def test_unknown_ambiguous_and_success_states_block(self) -> None:
        invalid = (
            _observations(extra=True),
            _observations(matching_bff_request_observed=True, bff_http_class="none"),
            _observations(matching_bff_request_observed=False, bff_http_class="401"),
            _observations(matching_bff_request_observed=True, bff_http_class="2xx"),
        )
        for observations in invalid:
            with self.subTest(observations=observations):
                with self.assertRaises(DiagnosticBlockedError):
                    classify_observations(observations)

    def test_projection_rejects_unknown_or_nonzero_forbidden_counter(self) -> None:
        projection = _projection(_observations())
        self.assertEqual(projection.classification, BFF_REQUEST_NOT_OBSERVED)
        counters = dict(projection.side_effect_counters)
        counters["login"] = 1
        with self.assertRaises(DiagnosticBlockedError):
            build_decision_projection(
                target=projection.target,
                bindings=projection.bindings,
                observation_window=projection.observation_window,
                observations=projection.observations,
                side_effect_counters=counters,
            )

    def test_two_independent_snapshots_compare_by_decision_projection(self) -> None:
        projection = _projection(_observations())
        first = build_snapshot(
            envelope=AcquisitionEnvelope(1, "2026-09-20T08:06:00Z", "3" * 64, _port_receipts(10)),
            projection=projection,
        )
        second = build_snapshot(
            envelope=AcquisitionEnvelope(2, "2026-09-20T08:06:01Z", "4" * 64, _port_receipts(30)),
            projection=projection,
        )
        self.assertEqual(compare_snapshots(first, second), BFF_REQUEST_NOT_OBSERVED)

    def test_reused_receipt_wrong_sequence_or_projection_drift_blocks(self) -> None:
        projection = _projection(_observations())
        first = build_snapshot(
            envelope=AcquisitionEnvelope(1, "2026-09-20T08:06:00Z", "3" * 64, _port_receipts(10)),
            projection=projection,
        )
        candidates = (
            build_snapshot(envelope=AcquisitionEnvelope(2, "2026-09-20T08:06:01Z", "3" * 64, _port_receipts(30)), projection=projection),
            build_snapshot(envelope=AcquisitionEnvelope(1, "2026-09-20T08:06:01Z", "4" * 64, _port_receipts(30)), projection=projection),
            build_snapshot(envelope=AcquisitionEnvelope(2, "2026-09-20T08:06:01Z", "4" * 64, _port_receipts(30)), projection=_projection(_observations(matching_bff_request_observed=True, bff_http_class="401"))),
            build_snapshot(envelope=AcquisitionEnvelope(2, "2026-09-20T08:06:01Z", "4" * 64, _port_receipts(10)), projection=projection),
            build_snapshot(envelope=AcquisitionEnvelope(2, "2026-09-20T08:06:00Z", "4" * 64, _port_receipts(30)), projection=projection),
        )
        for second in candidates:
            with self.subTest(second=second):
                with self.assertRaises(DiagnosticBlockedError):
                    compare_snapshots(first, second)

    def test_production_adapters_are_injected_closed_and_reauthorize_each_read(self) -> None:
        authorization = authorize_synthetic_current_state_run(_gate_input())
        transport = _ScriptedTransport()
        revalidations: list[int] = []
        ports = _ports(
            transport, authorization,
            evidence_verifier=lambda: revalidations.append(1),
        )
        classification, first, second = run_double_snapshot_diagnostic(
            authorization=authorization,
            ports=ports,
            bindings=_projection(_observations()).bindings,
            observation_window=_projection(_observations()).observation_window,
            clock=_IncreasingClock(),
        )
        self.assertEqual(classification, BFF_REQUEST_NOT_OBSERVED)
        self.assertEqual(len(transport.calls), 14)
        self.assertEqual(len(revalidations), 14)
        self.assertNotEqual(
            first.acquisition_envelope.provider_read_receipt_sha256,
            second.acquisition_envelope.provider_read_receipt_sha256,
        )

    def test_adapter_rejects_redirect_retry_and_unknown_provider_field(self) -> None:
        authorization = authorize_synthetic_current_state_run(_gate_input())
        with self.assertRaises(RuntimeError):
            _ports(
                _ScriptedTransport(),
                authorization,
                policy=TransportPolicy(follow_redirects=True),
            )
        transport = _ScriptedTransport(extra_field=True)
        ports = _ports(transport, authorization)
        with self.assertRaises(RuntimeError):
            ports.teams_tab.read(authorization)
        with self.assertRaises(Exception):
            _ports(
                _ScriptedTransport(), authorization,
                target={"opaque": "different"},
            ).teams_tab.read(authorization)

    def test_protected_production_composition_reaches_redacted_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_root = root / "input"
            evidence_root = root / "evidence"
            input_root.mkdir()
            evidence_root.mkdir()
            driver = root / "bound-reader.exe"
            driver.write_bytes(b"synthetic-attested-driver")
            driver_sha = hashlib.sha256(driver.read_bytes()).hexdigest()
            target = {"workspace_id": "notary_team_01", "app_id": "nac-vorgangsansicht"}
            payloads = _protected_payloads(driver, driver_sha, target)
            for name, value in payloads.items():
                (input_root / name).write_text(
                    json.dumps(value, sort_keys=True, separators=(",", ":")),
                    encoding="utf-8",
                )
            backend = _ScriptedSecurityBackend(evidence_root, input_root)

            classification, first, second = (
                run_current_state_access_diagnostic_from_protected_inputs(
                    input_root=input_root,
                    evidence_root=evidence_root,
                    repo_root=Path(__file__).resolve().parents[1],
                    backend=backend,
                )
            )

            self.assertEqual(classification, BFF_REQUEST_NOT_OBSERVED)
            self.assertEqual(first.decision_projection_sha256, second.decision_projection_sha256)
            self.assertEqual(backend.operations.count("github_gate"), 15)
            self.assertEqual(backend.operations.count("local_git_gate"), 15)
            self.assertTrue(any(name.endswith(".result.json") for name in backend.session.files))
            provider_reads = [
                operation for operation in backend.operations
                if operation not in {"github_gate", "local_git_gate"}
            ]
            with self.assertRaises(Exception):
                run_current_state_access_diagnostic_from_protected_inputs(
                    input_root=input_root,
                    evidence_root=evidence_root,
                    repo_root=Path(__file__).resolve().parents[1],
                    backend=backend,
                )
            self.assertEqual(
                [operation for operation in backend.operations
                 if operation not in {"github_gate", "local_git_gate"}],
                provider_reads,
            )
            second_evidence_root = root / "evidence-two"
            second_evidence_root.mkdir()
            second_backend = _ScriptedSecurityBackend(second_evidence_root, input_root)
            with self.assertRaises(DiagnosticBlockedError) as raised:
                run_current_state_access_diagnostic_from_protected_inputs(
                    input_root=input_root,
                    evidence_root=second_evidence_root,
                    repo_root=Path(__file__).resolve().parents[1],
                    backend=second_backend,
                )
            self.assertEqual(raised.exception.code, "BLOCKED_APPROVAL_BINDING")
            self.assertEqual(second_backend.operations, [])

    def test_target_scope_and_derived_binding_are_closed(self) -> None:
        for mutation in ("workspace", "extra", "digest"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                input_root = root / "input"
                evidence_root = root / "evidence"
                input_root.mkdir()
                evidence_root.mkdir()
                driver = root / "bound-reader.exe"
                driver.write_bytes(b"synthetic-attested-driver")
                payloads = _protected_payloads(
                    driver, hashlib.sha256(driver.read_bytes()).hexdigest(),
                    {"workspace_id": "notary_team_01", "app_id": "nac-vorgangsansicht"},
                )
                if mutation == "workspace":
                    payloads["target.json"]["target"]["workspace_id"] = "other"
                elif mutation == "extra":
                    payloads["target.json"]["target"]["site_id"] = "other"
                else:
                    payloads["target.json"]["target_binding_sha256"] = "0" * 64
                for name, value in payloads.items():
                    (input_root / name).write_text(
                        json.dumps(value, sort_keys=True, separators=(",", ":")),
                        encoding="utf-8",
                    )
                backend = _ScriptedSecurityBackend(evidence_root, input_root)
                with self.assertRaises(DiagnosticBlockedError):
                    run_current_state_access_diagnostic_from_protected_inputs(
                        input_root=input_root, evidence_root=evidence_root,
                        repo_root=Path(__file__).resolve().parents[1], backend=backend,
                    )
                self.assertEqual(backend.operations, [])

    def test_dpa_scope_retention_and_approval_core_are_derived(self) -> None:
        for field in (
            "permitted_data_scope", "retention_days", "approval_core_sha256",
            "policy_sha256", "agreement_evidence_sha256",
        ):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                input_root = root / "input"
                evidence_root = root / "evidence"
                input_root.mkdir()
                evidence_root.mkdir()
                driver = root / "bound-reader.exe"
                driver.write_bytes(b"synthetic-attested-driver")
                payloads = _protected_payloads(
                    driver, hashlib.sha256(driver.read_bytes()).hexdigest(),
                    {"workspace_id": "notary_team_01", "app_id": "nac-vorgangsansicht"},
                )
                if field == "permitted_data_scope":
                    payloads["dpa-avv-receipt.json"][field] = ["raw_request_payload"]
                elif field == "retention_days":
                    payloads["dpa-avv-receipt.json"][field] = 365
                else:
                    payloads["dpa-avv-receipt.json"][field] = "0" * 64
                for name, value in payloads.items():
                    (input_root / name).write_text(
                        json.dumps(value, sort_keys=True, separators=(",", ":")),
                        encoding="utf-8",
                    )
                backend = _ScriptedSecurityBackend(evidence_root, input_root)
                with self.assertRaises(DiagnosticBlockedError):
                    run_current_state_access_diagnostic_from_protected_inputs(
                        input_root=input_root, evidence_root=evidence_root,
                        repo_root=Path(__file__).resolve().parents[1], backend=backend,
                    )
                self.assertEqual(backend.operations, [])

    def test_dpa_agreement_evidence_is_provider_tenant_and_target_bound(self) -> None:
        for field in ("provider", "tenant_binding_sha256", "target_payload_sha256"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                input_root = root / "input"
                evidence_root = root / "evidence"
                input_root.mkdir()
                evidence_root.mkdir()
                driver = root / "bound-reader.exe"
                driver.write_bytes(b"synthetic-attested-driver")
                payloads = _protected_payloads(
                    driver, hashlib.sha256(driver.read_bytes()).hexdigest(),
                    {"workspace_id": "notary_team_01", "app_id": "nac-vorgangsansicht"},
                )
                payloads["dpa-avv-agreement-evidence.json"][field] = (
                    "github" if field == "provider" else "0" * 64
                )
                for name, value in payloads.items():
                    (input_root / name).write_text(
                        json.dumps(value, sort_keys=True, separators=(",", ":")),
                        encoding="utf-8",
                    )
                backend = _ScriptedSecurityBackend(evidence_root, input_root)
                with self.assertRaises(DiagnosticBlockedError):
                    run_current_state_access_diagnostic_from_protected_inputs(
                        input_root=input_root, evidence_root=evidence_root,
                        repo_root=Path(__file__).resolve().parents[1], backend=backend,
                    )
                self.assertEqual(backend.operations, [])

    def test_approval_nonce_drift_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_root = root / "input"
            evidence_root = root / "evidence"
            input_root.mkdir()
            evidence_root.mkdir()
            driver = root / "bound-reader.exe"
            driver.write_bytes(b"synthetic-attested-driver")
            payloads = _protected_payloads(
                driver, hashlib.sha256(driver.read_bytes()).hexdigest(),
                {"workspace_id": "notary_team_01", "app_id": "nac-vorgangsansicht"},
            )
            payloads["owner-approval.json"]["run_nonce_sha256"] = "9" * 64
            for name, value in payloads.items():
                (input_root / name).write_text(
                    json.dumps(value, sort_keys=True, separators=(",", ":")),
                    encoding="utf-8",
                )
            backend = _ScriptedSecurityBackend(evidence_root, input_root)
            with self.assertRaises(DiagnosticBlockedError):
                run_current_state_access_diagnostic_from_protected_inputs(
                    input_root=input_root, evidence_root=evidence_root,
                    repo_root=Path(__file__).resolve().parents[1], backend=backend,
                )

    def test_client_and_request_correlation_drift_block(self) -> None:
        for drift in ("protected-client", "provider-request", "provider-client"):
            with self.subTest(drift=drift), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                input_root = root / "input"
                evidence_root = root / "evidence"
                input_root.mkdir()
                evidence_root.mkdir()
                driver = root / "bound-reader.exe"
                driver.write_bytes(b"synthetic-attested-driver")
                payloads = _protected_payloads(
                    driver, hashlib.sha256(driver.read_bytes()).hexdigest(),
                    {"workspace_id": "notary_team_01", "app_id": "nac-vorgangsansicht"},
                )
                if drift == "protected-client":
                    payloads["client-observation-receipt.json"][
                        "request_correlation_binding_sha256"
                    ] = "8" * 64
                for name, value in payloads.items():
                    (input_root / name).write_text(
                        json.dumps(value, sort_keys=True, separators=(",", ":")),
                        encoding="utf-8",
                    )
                backend = _ScriptedSecurityBackend(
                    evidence_root, input_root,
                    provider_request_correlation=("8" * 64 if drift == "provider-request" else None),
                    provider_client_subject=(False if drift == "provider-client" else None),
                )
                with self.assertRaises(DiagnosticBlockedError):
                    run_current_state_access_diagnostic_from_protected_inputs(
                        input_root=input_root, evidence_root=evidence_root,
                        repo_root=Path(__file__).resolve().parents[1], backend=backend,
                    )
                self.assertFalse(
                    any(name.endswith(".result.json") for name in backend.session.files)
                )

    def test_per_read_local_and_github_gate_drift_suppresses_provider_read(self) -> None:
        for gate in ("local_git_gate", "github_gate"):
            with self.subTest(gate=gate), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                input_root = root / "input"
                evidence_root = root / "evidence"
                input_root.mkdir()
                evidence_root.mkdir()
                driver = root / "bound-reader.exe"
                driver.write_bytes(b"synthetic-attested-driver")
                for name, value in _protected_payloads(
                    driver, hashlib.sha256(driver.read_bytes()).hexdigest(),
                    {"workspace_id": "notary_team_01", "app_id": "nac-vorgangsansicht"},
                ).items():
                    (input_root / name).write_text(
                        json.dumps(value, sort_keys=True, separators=(",", ":")),
                        encoding="utf-8",
                    )
                backend = _ScriptedSecurityBackend(
                    evidence_root, input_root, drift_gate=gate
                )
                with self.assertRaises(DiagnosticBlockedError) as raised:
                    run_current_state_access_diagnostic_from_protected_inputs(
                        input_root=input_root, evidence_root=evidence_root,
                        repo_root=Path(__file__).resolve().parents[1], backend=backend,
                    )
                self.assertEqual(
                    raised.exception.code,
                    "BLOCKED_GIT_GATE_DRIFT" if gate == "local_git_gate"
                    else "BLOCKED_GITHUB_GATE_DRIFT",
                )
                self.assertEqual(
                    [operation for operation in backend.operations
                     if operation not in {"local_git_gate", "github_gate"}],
                    [],
                )

    def test_consumed_marker_drift_suppresses_provider_read(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_root = root / "input"
            evidence_root = root / "evidence"
            input_root.mkdir()
            evidence_root.mkdir()
            driver = root / "bound-reader.exe"
            driver.write_bytes(b"synthetic-attested-driver")
            for name, value in _protected_payloads(
                driver, hashlib.sha256(driver.read_bytes()).hexdigest(),
                {"workspace_id": "notary_team_01", "app_id": "nac-vorgangsansicht"},
            ).items():
                (input_root / name).write_text(
                    json.dumps(value, sort_keys=True, separators=(",", ":")),
                    encoding="utf-8",
                )
            backend = _ScriptedSecurityBackend(
                evidence_root, input_root, marker_drift=True
            )
            with self.assertRaises(Exception):
                run_current_state_access_diagnostic_from_protected_inputs(
                    input_root=input_root, evidence_root=evidence_root,
                    repo_root=Path(__file__).resolve().parents[1], backend=backend,
                )
            self.assertEqual(backend.operations, ["local_git_gate"])
            self.assertEqual(
                [operation for operation in backend.operations
                 if operation not in {"local_git_gate", "github_gate"}],
                [],
            )

    def test_dpa_expiry_between_gate_reads_suppresses_github_and_provider(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_root = root / "input"
            evidence_root = root / "evidence"
            input_root.mkdir()
            evidence_root.mkdir()
            driver = root / "bound-reader.exe"
            driver.write_bytes(b"synthetic-attested-driver")
            for name, value in _protected_payloads(
                driver, hashlib.sha256(driver.read_bytes()).hexdigest(),
                {"workspace_id": "notary_team_01", "app_id": "nac-vorgangsansicht"},
            ).items():
                (input_root / name).write_text(
                    json.dumps(value, sort_keys=True, separators=(",", ":")),
                    encoding="utf-8",
                )
            backend = _ScriptedSecurityBackend(evidence_root, input_root)
            with patch(
                "nac_bff.current_state_access_composition._utc_now",
                side_effect=[
                    datetime(2026, 1, 2, tzinfo=UTC),
                    datetime(2026, 1, 2, tzinfo=UTC),
                    datetime(2100, 1, 2, tzinfo=UTC),
                ],
            ):
                with self.assertRaises(DiagnosticBlockedError) as raised:
                    run_current_state_access_diagnostic_from_protected_inputs(
                        input_root=input_root, evidence_root=evidence_root,
                        repo_root=Path(__file__).resolve().parents[1], backend=backend,
                    )
            self.assertEqual(raised.exception.code, "BLOCKED_DPA_AVV_BINDING")
            self.assertEqual(backend.operations, ["local_git_gate"])

    def test_dpa_expiry_after_revalidation_gates_suppresses_provider_read(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_root = root / "input"
            evidence_root = root / "evidence"
            input_root.mkdir()
            evidence_root.mkdir()
            driver = root / "bound-reader.exe"
            driver.write_bytes(b"synthetic-attested-driver")
            for name, value in _protected_payloads(
                driver, hashlib.sha256(driver.read_bytes()).hexdigest(),
                {"workspace_id": "notary_team_01", "app_id": "nac-vorgangsansicht"},
            ).items():
                (input_root / name).write_text(
                    json.dumps(value, sort_keys=True, separators=(",", ":")),
                    encoding="utf-8",
                )
            backend = _ScriptedSecurityBackend(evidence_root, input_root)
            valid = datetime(2026, 1, 2, tzinfo=UTC)
            with patch(
                "nac_bff.current_state_access_composition._utc_now",
                side_effect=[valid] * 6 + [datetime(2100, 1, 2, tzinfo=UTC)],
            ):
                with self.assertRaises(DiagnosticBlockedError) as raised:
                    run_current_state_access_diagnostic_from_protected_inputs(
                        input_root=input_root, evidence_root=evidence_root,
                        repo_root=Path(__file__).resolve().parents[1], backend=backend,
                    )
            self.assertEqual(raised.exception.code, "BLOCKED_DPA_AVV_BINDING")
            self.assertEqual(
                [operation for operation in backend.operations
                 if operation not in {"local_git_gate", "github_gate"}],
                [],
            )

def _gate_input() -> GateInput:
    return GateInput(
        issue=748, pr=749, base_pr=747,
        base_merge_commit="80bf813375d7fc2ab292dfdbcc1db447fdb6684a",
        base_tree="007e277ca5643f7cb63355961fd0422d92fd4b87",
        head="a" * 40, tree="b" * 40, head_descends_from_base=True,
        resolver_sha256="c" * 64,
        operator_account_id="microsoft:owner-primary",
        operator_principal_id="person:owner",
        authorized_account_id="microsoft:owner-primary",
        authorized_principal_id="person:owner",
        provider="microsoft", tenant_binding_sha256="d" * 64,
        account_permission_sha256="4" * 64,
        target_binding_sha256="e" * 64,
        target_payload_sha256=hashlib.sha256(
            json.dumps({"opaque": "bound"}, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        dpa_avv_binding_sha256="f" * 64,
        contract_sha256="1" * 64, toolchain_sha256="2" * 64,
        approval_sha256="3" * 64, approval_mode="OWNER_SOLO_APPROVAL",
        run_nonce_sha256="6" * 64,
        four_eyes_satisfied=False, external_two_person_required=False,
        external_requirement_citation=None, required_checks_successful=True,
        required_checks_sha256="5" * 64,
        worktree_clean=True, credential_write_guard_active=True,
        evidence_root_binding_sha256=hashlib.sha256(
            str(Path("C:/protected/issue748").resolve()).encode("utf-8")
        ).hexdigest(),
    )


class _ScriptedTransport:
    def __init__(self, *, extra_field: bool = False) -> None:
        self.calls: list[str] = []
        self.extra_field = extra_field

    def read(self, *, operation, target):
        self.calls.append(operation)
        values = {
            "client_observation_receipt": {"ui_state": "no_access", "spfx_subject_available": True, "client_receipt_sha256": "1" * 64},
            "teams_tab_metadata": {"contract_matches": True, "version_binding": "opaque-version"},
            "sharepoint_app_catalog": {"package_version": "1.0.0", "package_digest": "2" * 64, "api_permission_match": True},
            "entra_api_permission": {"tenant_match": True, "audience_match": True, "scope_match": True, "preauthorization_match": True},
            "azure_function_metadata": {"deployment_class": "deployed", "configuration_digest": "3" * 64},
            "azure_function_request_log": {"request_observed": False, "http_class": "none", "request_correlation_binding_sha256": "2" * 64},
            "sharepoint_access_decision": {"evidence_matches": True},
        }
        data = dict(values[operation])
        if self.extra_field and operation == "teams_tab_metadata":
            data["raw"] = "forbidden"
        return {
            "data": data,
            "receipt_sha256": f"{len(self.calls):064x}",
        }


def _ports(
    transport, authorization, *, policy=TransportPolicy(),
    target=None, evidence_verifier=None,
):
    common = {
        "transport": transport,
        "target": target or {"opaque": "bound"},
        "account_id": authorization.account_id,
        "principal_id": authorization.principal_id,
        "target_binding_sha256": authorization.target_binding_sha256,
        "evidence_verifier": evidence_verifier or (lambda: None),
        "policy": policy,
    }
    return CurrentStateAccessPorts(
        ClientObservationReceiptAdapter(**common),
        TeamsTabMetadataReadAdapter(**common),
        SharePointAppCatalogReadAdapter(**common),
        EntraApiPermissionReadAdapter(**common),
        AzureFunctionMetadataReadAdapter(**common),
        AzureFunctionRequestLogReadAdapter(**common),
        SharePointAccessDecisionReadAdapter(**common),
    )


class _MemorySession:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def create_exclusive(self, name, payload):
        if name in self.files:
            raise FileExistsError(name)
        self.files[name] = payload
        return SimpleNamespace(sha256=hashlib.sha256(payload).hexdigest())

    def close(self):
        pass


class _MemorySecurityBackend:
    def __init__(self) -> None:
        self.session = _MemorySession()

    def open_secure_directory(self, path, *, create, **kwargs):
        return self.session

    def acquire_run_lock(self, target_binding):
        return SimpleNamespace(close=lambda: None)


class _FailingSecurityBackend:
    def open_secure_directory(self, path, *, create, **kwargs):
        raise OSError("synthetic protected-directory failure")


class _IncreasingClock:
    def __init__(self) -> None:
        self.second = 0

    def __call__(self) -> datetime:
        self.second += 1
        return datetime(2026, 9, 20, 8, 6, self.second, tzinfo=UTC)


def _protected_payloads(driver: Path, driver_sha: str, target: dict[str, str]):
    target_sha = hashlib.sha256(
        json.dumps(target, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    account_permission_sha = hashlib.sha256(
        json.dumps(
            {"account_id": "microsoft:owner-primary", "provider": "microsoft",
             "tenant_binding_sha256": "d" * 64,
             "target_payload_sha256": target_sha,
             "operations": [
                 "client_observation_receipt", "teams_tab_metadata",
                 "sharepoint_app_catalog", "entra_api_permission",
                 "azure_function_metadata", "azure_function_request_log",
                 "sharepoint_access_decision",
             ]},
            sort_keys=True, separators=(",", ":"),
        ).encode()
    ).hexdigest()
    request_correlation = "7" * 64
    client_receipt = {
        "schema_version": "v1", "target_payload_sha256": target_sha,
        "window_binding_sha256": "f" * 64,
        "request_correlation_binding_sha256": request_correlation,
        "start_utc": "2026-01-20T08:00:00Z",
        "end_utc": "2026-01-20T08:05:00Z",
        "ui_state": "no_access",
        "spfx_subject_available": True,
    }
    client_receipt_sha = hashlib.sha256(
        json.dumps(client_receipt, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    observation_window = {
        "start_utc": "2026-01-20T08:00:00Z",
        "end_utc": "2026-01-20T08:05:00Z",
        "window_binding_sha256": "f" * 64,
        "client_receipt_sha256": client_receipt_sha,
        "request_correlation_binding_sha256": request_correlation,
    }
    contract = {
        "schema_version": "v1", "issue": 748, "pr": 749, "base_pr": 747,
        "base_merge_commit": "80bf813375d7fc2ab292dfdbcc1db447fdb6684a",
        "base_tree": "007e277ca5643f7cb63355961fd0422d92fd4b87",
        "final_head": "a" * 40, "final_tree": "b" * 40,
        "required_checks_sha256": "5" * 64,
    }
    toolchain = {
        "schema_version": "v1", "read_driver_path": str(driver),
        "read_driver_sha256": driver_sha,
    }
    run_nonce = "6" * 64
    approval_core = {
        "schema_version": "v1", "approval_mode": "OWNER_SOLO_APPROVAL",
        "four_eyes_satisfied": False, "external_two_person_required": False,
        "external_requirement_citation": None, "run_nonce_sha256": run_nonce,
        "head": "a" * 40, "tree": "b" * 40,
        "target_payload_sha256": target_sha,
        "operator_account_binding_sha256": hmac.new(
            bytes.fromhex(run_nonce), b"microsoft:owner-primary", hashlib.sha256
        ).hexdigest(),
        "operator_principal_binding_sha256": hmac.new(
            bytes.fromhex(run_nonce), b"person:owner", hashlib.sha256
        ).hexdigest(),
        "contract_sha256": hashlib.sha256(
            json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "toolchain_sha256": hashlib.sha256(
            json.dumps(toolchain, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "evidence_root_binding_sha256": hashlib.sha256(
            str((driver.parent / "evidence").resolve()).encode("utf-8")
        ).hexdigest(),
        "client_receipt_sha256": client_receipt_sha,
        "observation_window_sha256": hashlib.sha256(
            json.dumps(
                observation_window, sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest(),
        "request_correlation_binding_sha256": request_correlation,
    }
    permitted_data_scope = [
        "redacted_client_state", "deployment_metadata",
        "redacted_request_class", "access_decision_evidence",
    ]
    dpa_agreement_evidence = {
        "schema_version": "v1", "provider": "microsoft",
        "tenant_binding_sha256": "d" * 64,
        "target_payload_sha256": target_sha,
        "agreement_status": "effective",
        "agreement_identifier_sha256": "9" * 64,
        "effective_from_utc": "2026-01-01T00:00:00Z",
        "expires_at_utc": "2099-01-01T00:00:00Z",
    }
    dpa = {
        "schema_version": "v1", "status": "valid",
        "basis": "applicable_dpa",
        "purpose": "issue748_current_state_access_read_only",
        "scope_binding_sha256": hashlib.sha256(
            json.dumps(
                {"provider": "microsoft", "tenant_binding_sha256": "d" * 64,
                 "target_payload_sha256": target_sha},
                sort_keys=True, separators=(",", ":"),
            ).encode()
        ).hexdigest(),
        "policy_reference": "policies/data-protection-policy.yaml",
        "policy_sha256": hashlib.sha256(
            (Path(__file__).resolve().parents[1] / "policies/data-protection-policy.yaml")
            .read_bytes()
        ).hexdigest(),
        "agreement_evidence_sha256": hashlib.sha256(
            json.dumps(
                dpa_agreement_evidence, sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest(),
        "permitted_data_scope": permitted_data_scope,
        "retention_days": 30,
        "deletion_mode": "protected_evidence_expiry",
        "retention_binding_sha256": hashlib.sha256(
            json.dumps(
                {"permitted_data_scope": permitted_data_scope, "retention_days": 30,
                 "deletion_mode": "protected_evidence_expiry",
                 "purpose": "issue748_current_state_access_read_only"},
                sort_keys=True, separators=(",", ":"),
            ).encode()
        ).hexdigest(),
        "approval_core_sha256": hashlib.sha256(
            json.dumps(approval_core, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "run_nonce_sha256": run_nonce,
    }
    resolver = {
        "schema_version": "v1", "operator_account_id": "microsoft:owner-primary",
        "operator_principal_id": "person:owner",
        "authorized_account_id": "microsoft:owner-primary",
        "authorized_principal_id": "person:owner", "provider": "microsoft",
    }
    common_bindings = {
        "final_head_sha256": hashlib.sha256(("a" * 40).encode()).hexdigest(),
        "final_tree_sha256": hashlib.sha256(("b" * 40).encode()).hexdigest(),
        "contract_sha256": hashlib.sha256(
            json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "resolver_sha256": hashlib.sha256(
            json.dumps(resolver, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "dpa_avv_binding_sha256": hashlib.sha256(
            json.dumps(dpa, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }
    approval = {
        **approval_core,
        "dpa_avv_binding_sha256": hashlib.sha256(
            json.dumps(dpa, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }
    return {
        "contract.json": contract,
        "resolver.json": resolver,
        "target.json": {
            "schema_version": "v1", "tenant_binding_sha256": "d" * 64,
            "target_binding_sha256": target_sha,
            "account_permission_sha256": account_permission_sha, "target": target,
            "bindings": common_bindings,
            "observation_window": observation_window,
        },
        "dpa-avv-agreement-evidence.json": dpa_agreement_evidence,
        "dpa-avv-receipt.json": dpa,
        "client-observation-receipt.json": client_receipt,
        "owner-approval.json": approval,
        "toolchain.json": toolchain,
    }


class _ScriptedSecurityBackend:
    def __init__(
        self, evidence_root: Path, input_root: Path, *,
        drift_gate: str | None = None,
        provider_request_correlation: str | None = None,
        marker_drift: bool = False,
        provider_client_subject: bool | None = None,
    ) -> None:
        self.session = _MemorySession()
        self.evidence_root = evidence_root
        self.input_root = input_root
        self.operations: list[str] = []
        self.sequence = 0
        self.drift_gate = drift_gate
        self.provider_request_correlation = provider_request_correlation
        self.marker_drift = marker_drift
        self.marker_inspections = 0
        self.provider_client_subject = provider_client_subject

    def inspect_private_path(self, path, purpose):
        if Path(path).parent == self.evidence_root and Path(path).name in self.session.files:
            raw = self.session.files[Path(path).name]
            self.marker_inspections += 1
            if self.marker_drift and self.marker_inspections > 1:
                return SimpleNamespace(size=len(raw), sha256="0" * 64)
            return SimpleNamespace(size=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        raw = Path(path).read_bytes()
        return SimpleNamespace(size=len(raw), sha256=hashlib.sha256(raw).hexdigest())

    def open_bound_read(self, path, snapshot):
        return open(path, "rb")

    def inspect_bound_input_path(self, path, purpose):
        return self.inspect_private_path(path, purpose)

    def open_bound_input_read(self, path, snapshot):
        return self.open_bound_read(path, snapshot)

    def open_secure_directory(self, path, *, create, **kwargs):
        return self.session

    def acquire_run_lock(self, target_binding):
        return SimpleNamespace(close=lambda: None)

    def launch_attested_process(self, spec):
        operation = spec.arguments[1]
        self.operations.append(operation)
        self.sequence += 1
        if operation == "local_git_gate":
            data = {
                "head": "a" * 40, "tree": "b" * 40,
                "head_descends_from_base": True, "worktree_clean": True,
            }
            if self.drift_gate == operation and self.operations.count(operation) > 1:
                data["worktree_clean"] = False
        elif operation == "github_gate":
            approval_sha = hashlib.sha256(
                (self.input_root / "owner-approval.json").read_bytes()
            ).hexdigest()
            data = {
                "repository": "notariat8/NaC", "pr": 749, "base_pr": 747,
                "base_merge_commit": "80bf813375d7fc2ab292dfdbcc1db447fdb6684a",
                "base_tree": "007e277ca5643f7cb63355961fd0422d92fd4b87",
                "head": "a" * 40, "required_checks_successful": True,
                "required_checks_sha256": "5" * 64,
                "approval_sha256": approval_sha,
            }
            if self.drift_gate == operation and self.operations.count(operation) > 1:
                data["required_checks_successful"] = False
        else:
            data = _ScriptedTransport().read(operation=operation, target={})["data"]
            if operation == "client_observation_receipt":
                data["client_receipt_sha256"] = hashlib.sha256(
                    (self.input_root / "client-observation-receipt.json").read_bytes()
                ).hexdigest()
                if self.provider_client_subject is not None:
                    data["spfx_subject_available"] = self.provider_client_subject
            elif operation == "azure_function_request_log":
                data["request_correlation_binding_sha256"] = (
                    self.provider_request_correlation or "7" * 64
                )
        payload = {
            "data": data,
            "receipt_sha256": f"{self.sequence:064x}",
        }
        if operation not in {"local_git_gate", "github_gate"}:
            context_index = spec.arguments.index("--authorization-context-sha256") + 1
            payload["authorization_context_sha256"] = spec.arguments[context_index]
        return SimpleNamespace(
            stdout=json.dumps(payload).encode("utf-8"),
            credential_write_guard_applied=True,
        )


if __name__ == "__main__":
    unittest.main()
