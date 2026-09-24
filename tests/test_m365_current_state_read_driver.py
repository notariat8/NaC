from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from scripts import validate_m365_current_state_read_driver
from nac_bff import current_state_read_driver_release
from nac_bff.current_state_read_driver import (
    ReadDriverBlocked,
    create_production_microsoft_port,
    verify_bundle_files,
    validate_redacted_projection,
)


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_CONTRACT = ROOT / "workflows/contracts/m365-current-state-read-driver-resources.contract.json"
RELEASE_CONTRACT = ROOT / "workflows/verification-contracts/m365-current-state-read-driver.verification.json"
HISTORICAL_CONTRACT = ROOT / "workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml"


class ReadDriverContractTests(unittest.TestCase):
    def test_candidate_validator_checks_real_files_source_and_license_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "bundle").mkdir()
            (root / "bundle/reader.exe").write_bytes(b"synthetic-reader")
            license_text = b"AGPL-3.0-or-later synthetic license"
            notice_text = b"NaC synthetic notice"
            catalog = {
                "schema_version": "nac.m365-current-state-read-driver-license-catalog/v0.1",
                "status": "APPROVED",
                "reviewed_preparation": None,
                "components": [{
                    "id": "nac", "name": "NaC", "version": "test",
                    "license": "AGPL-3.0-or-later", "license_text_path": "LICENSE",
                    "license_text_sha256": hashlib.sha256(license_text).hexdigest(),
                    "source_uri": "git:HEAD", "source_sha256": "BOUND_SOURCE_TREE",
                }],
                "files": [{"path": "reader.exe", "component_ids": ["nac"]}],
            }
            catalog_bytes = json.dumps(catalog).encode()
            source_stream = io.BytesIO()
            with tarfile.open(fileobj=source_stream, mode="w") as archive:
                for name, content in (
                    ("LICENSE", license_text), ("NOTICE", notice_text),
                    ("src/nac_bff/current_state_read_driver.py", b"synthetic-driver"),
                    ("workflows/contracts/m365-current-state-read-driver-license-catalog.json",
                     catalog_bytes),
                ):
                    info = tarfile.TarInfo(name)
                    info.size = len(content)
                    archive.addfile(info, io.BytesIO(content))
            source_bytes = source_stream.getvalue()
            (root / "source.tar").write_bytes(source_bytes)
            (root / "LICENSE").write_bytes(license_text)
            (root / "NOTICE").write_bytes(notice_text)
            (root / "license-catalog.json").write_bytes(catalog_bytes)
            (root / "cyclonedx.json").write_text(json.dumps({
                "bomFormat": "CycloneDX", "components": [{
                    "bom-ref": "1111222233334444", "name": "NaC", "version": "test",
                    "properties": [{"name": "syft:location:0:path", "value": "\\reader.exe"}],
                }],
            }), encoding="utf-8")
            (root / "spdx.json").write_text(json.dumps({
                "spdxVersion": "SPDX-2.3", "packages": [
                    {"SPDXID": "SPDXRef-DocumentRoot-Directory-0", "name": "bundle"},
                    {"SPDXID": "SPDXRef-Package-NaC-1111222233334444",
                     "name": "NaC", "versionInfo": "test"},
                ],
                "files": [{"SPDXID": "SPDXRef-File-reader", "fileName": "\\reader.exe"}],
                "relationships": [
                    {"spdxElementId": "SPDXRef-Package-NaC-1111222233334444",
                      "relatedSpdxElement": "SPDXRef-File-reader", "relationshipType": "OTHER"},
                    {"spdxElementId": "SPDXRef-DocumentRoot-Directory-0",
                     "relatedSpdxElement": "SPDXRef-Package-NaC-1111222233334444",
                     "relationshipType": "CONTAINS"},
                    {"spdxElementId": "SPDXRef-DOCUMENT",
                     "relatedSpdxElement": "SPDXRef-DocumentRoot-Directory-0",
                     "relationshipType": "DESCRIBES"},
                ],
            }), encoding="utf-8")
            component = {
                "id": "nac", "name": "NaC", "version": "test",
                "license": "AGPL-3.0-or-later", "license_text_path": "LICENSE",
                "license_text_sha256": hashlib.sha256((root / "LICENSE").read_bytes()).hexdigest(),
                "cyclonedx_ref": "1111222233334444",
                "spdx_id": "SPDXRef-Package-NaC-1111222233334444",
            }
            inventory = {
                "schema_version": "nac.m365-current-state-read-driver-license-inventory/v0.1",
                "components": [component],
                "files": [{"path": "reader.exe", "component_ids": ["nac"]}],
            }
            (root / "license-inventory.json").write_text(
                json.dumps(inventory), encoding="utf-8"
            )
            resource_sha = hashlib.sha256(RESOURCE_CONTRACT.read_bytes()).hexdigest()
            build_tool = {
                "name": "PyInstaller", "version": "6.22.3", "python_version": "3.13.4",
                "python": {"path": str(root / "python.exe"), "sha256": "a" * 64},
                "pyinstaller": {"module_path": str(root / "PyInstaller/__main__.py"),
                                "module_sha256": "b" * 64,
                                "package_tree_sha256": "c" * 64},
                "syft": {"version": "1.52.0", "path": str(root / "syft.exe"),
                         "sha256": "d" * 64},
            }
            artifacts = {
                name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                for name in (
                    "source.tar", "cyclonedx.json", "spdx.json", "LICENSE",
                    "NOTICE", "license-inventory.json", "license-catalog.json",
                )
            }
            entry = {
                "path": "reader.exe", "sha256": hashlib.sha256(b"synthetic-reader").hexdigest(),
                "size": len(b"synthetic-reader"), "volume_serial": 1,
                "file_id": 42, "owner_sid_sha256": "a" * 64,
                "dacl_sha256": "b" * 64, "security_descriptor_sha256": "c" * 64,
                "path_sha256": "d" * 64,
            }
            build_command = [
                build_tool["python"]["path"], "-m", "PyInstaller", "--onedir",
                "--name", "reader", "--distpath", str(root / "bundle-stage"),
                "--workpath", str(root / "work"), "--specpath", str(root / "work"),
                "--paths", str(ROOT / "src"),
                str(ROOT / "src/nac_bff/current_state_read_driver.py"),
            ]
            sbom_commands = {
                "cyclonedx": [build_tool["syft"]["path"], f"dir:{root / 'bundle'}",
                              "-o", f"cyclonedx-json={root / 'cyclonedx.json'}"],
                "spdx": [build_tool["syft"]["path"], f"dir:{root / 'bundle'}",
                         "-o", f"spdx-json={root / 'spdx.json'}"],
            }
            preparation = {
                "schema_version": "nac.m365-current-state-read-driver-preparation/v0.1",
                "status": "AWAITING_INDEPENDENT_LICENSE_EVIDENCE",
                "source_commit": "1" * 40, "source_tree": "2" * 40,
                "build_tool": build_tool, "build_command": build_command,
                "sbom_commands": sbom_commands,
                "artifacts": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                              for name in ("source.tar", "cyclonedx.json", "spdx.json",
                                           "LICENSE", "NOTICE")},
                "bundle_files": [{"path": "reader.exe", "sha256": entry["sha256"]}],
            }
            (root / "preparation.json").write_text(json.dumps(preparation), encoding="utf-8")
            catalog["reviewed_preparation"] = {
                "driver_source_sha256": hashlib.sha256(b"synthetic-driver").hexdigest(),
                "resource_contract_sha256": resource_sha,
                "build_tool": build_tool,
                "bundle_files": preparation["bundle_files"],
                "cyclonedx_sha256": artifacts["cyclonedx.json"],
                "spdx_sha256": artifacts["spdx.json"],
                "notice_sha256": artifacts["NOTICE"],
            }
            catalog_bytes = json.dumps(catalog).encode()
            (root / "license-catalog.json").write_bytes(catalog_bytes)
            source_stream = io.BytesIO()
            with tarfile.open(fileobj=source_stream, mode="w") as archive:
                for name, content in (
                    ("LICENSE", license_text), ("NOTICE", notice_text),
                    ("src/nac_bff/current_state_read_driver.py", b"synthetic-driver"),
                    ("workflows/contracts/m365-current-state-read-driver-license-catalog.json",
                     catalog_bytes),
                ):
                    info = tarfile.TarInfo(name)
                    info.size = len(content)
                    archive.addfile(info, io.BytesIO(content))
            source_bytes = source_stream.getvalue()
            (root / "source.tar").write_bytes(source_bytes)
            artifacts["source.tar"] = hashlib.sha256(source_bytes).hexdigest()
            artifacts["license-catalog.json"] = hashlib.sha256(catalog_bytes).hexdigest()
            preparation["artifacts"]["source.tar"] = artifacts["source.tar"]
            (root / "preparation.json").write_text(json.dumps(preparation), encoding="utf-8")
            artifacts["preparation.json"] = hashlib.sha256(
                (root / "preparation.json").read_bytes()
            ).hexdigest()
            inputs = {
                "source_archive_sha256": artifacts["source.tar"],
                "resource_contract_sha256": resource_sha, "build_tool": build_tool,
            }
            release = {
                "schema_version": "nac.m365-current-state-read-driver-candidate/v0.2",
                "status": "CANDIDATE_BUILT", "source_commit": "1" * 40,
                "source_tree": "2" * 40, "resource_contract_sha256": resource_sha,
                "entrypoint": "reader.exe", "bundle_files": [entry],
                "artifacts": artifacts, "build_tool": build_tool,
                "byte_reproducibility_claim": False,
                "build_command": build_command,
                "sbom_commands": sbom_commands,
                "build_inputs_sha256": hashlib.sha256(json.dumps(
                    inputs, sort_keys=True, separators=(",", ":")
                ).encode()).hexdigest(),
            }
            (root / "release.json").write_text(json.dumps(release), encoding="utf-8")

            class Backend:
                def current_operator_binding(self):
                    return SimpleNamespace(sid_sha256="a" * 64)

                def validate_current_user_only_directory(self, _path):
                    return None

                def inspect_private_path(self, path, purpose):
                    if purpose != "issue748-read-driver-bundle-current-user-only":
                        raise AssertionError("wrong security purpose")
                    return SimpleNamespace(**{**entry, "sha256": hashlib.sha256(
                        path.read_bytes()).hexdigest(), "reparse_point": False})

            def check() -> list[str]:
                with patch(
                    "nac_bff.current_state_read_driver_release._validate_build_tool",
                    return_value=True,
                ):
                    return validate_m365_current_state_read_driver.validate_candidate_release(
                        root, Backend(), source_commit="1" * 40,
                        source_tree="2" * 40, source_archive=source_bytes,
                    )

            self.assertEqual(check(), [])
            self.assertTrue(current_state_read_driver_release._reviewed_catalog_matches(
                catalog, inventory, {"reader.exe"}, "2" * 40,
                catalog["reviewed_preparation"],
            ))
            drifted_review = {**catalog["reviewed_preparation"],
                              "cyclonedx_sha256": "0" * 64}
            self.assertFalse(current_state_read_driver_release._reviewed_catalog_matches(
                catalog, inventory, {"reader.exe"}, "2" * 40,
                drifted_review,
            ))
            (root / "NOTICE").write_bytes(notice_text + b"\nforged attribution")
            release["artifacts"]["NOTICE"] = hashlib.sha256(
                (root / "NOTICE").read_bytes()
            ).hexdigest()
            (root / "release.json").write_text(json.dumps(release), encoding="utf-8")
            self.assertIn("DRIVER_RELEASE_BINDING", check())
            (root / "NOTICE").write_bytes(notice_text)
            release["artifacts"]["NOTICE"] = hashlib.sha256(notice_text).hexdigest()
            (root / "release.json").write_text(json.dumps(release), encoding="utf-8")
            valid_cyclonedx = (root / "cyclonedx.json").read_bytes()
            altered_cyclonedx = json.loads(valid_cyclonedx)
            altered_cyclonedx["components"][0]["properties"][0]["value"] = "other.exe"
            (root / "cyclonedx.json").write_text(json.dumps(altered_cyclonedx), encoding="utf-8")
            release["artifacts"]["cyclonedx.json"] = hashlib.sha256(
                (root / "cyclonedx.json").read_bytes()
            ).hexdigest()
            (root / "release.json").write_text(json.dumps(release), encoding="utf-8")
            self.assertIn("DRIVER_RELEASE_BINDING", check())
            (root / "cyclonedx.json").write_bytes(valid_cyclonedx)
            release["artifacts"]["cyclonedx.json"] = hashlib.sha256(valid_cyclonedx).hexdigest()
            (root / "release.json").write_text(json.dumps(release), encoding="utf-8")
            (root / "source.tar").write_bytes(b"wrong-source")
            self.assertIn("DRIVER_RELEASE_BINDING", check())
            (root / "source.tar").write_bytes(source_bytes)
            (root / "LICENSE").write_bytes(b"mismatched license")
            release["artifacts"]["LICENSE"] = hashlib.sha256(
                (root / "LICENSE").read_bytes()
            ).hexdigest()
            (root / "release.json").write_text(json.dumps(release), encoding="utf-8")
            self.assertIn("DRIVER_RELEASE_BINDING", check())
            (root / "LICENSE").write_bytes(license_text)
            release["artifacts"]["LICENSE"] = hashlib.sha256(license_text).hexdigest()
            (root / "release.json").write_text(json.dumps(release), encoding="utf-8")
            inventory["files"] = []
            (root / "license-inventory.json").write_text(
                json.dumps(inventory), encoding="utf-8"
            )
            self.assertIn("DRIVER_RELEASE_BINDING", check())
            inventory["files"] = [{"path": "reader.exe", "component_ids": ["nac", "nac"]}]
            (root / "license-inventory.json").write_text(
                json.dumps(inventory), encoding="utf-8"
            )
            release["artifacts"]["license-inventory.json"] = hashlib.sha256(
                (root / "license-inventory.json").read_bytes()
            ).hexdigest()
            (root / "release.json").write_text(json.dumps(release), encoding="utf-8")
            self.assertIn("DRIVER_RELEASE_BINDING", check())

    def test_build_tool_attestation_detects_binary_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            python = root / "python.exe"
            syft = root / "syft.exe"
            module = root / "PyInstaller" / "__main__.py"
            module.parent.mkdir()
            for path in (python, syft, module):
                path.write_bytes(path.name.encode())
            tool = {
                "name": "PyInstaller", "version": "6.22.3", "python_version": "3.13.4",
                "python": {"path": str(python), "sha256": hashlib.sha256(python.read_bytes()).hexdigest()},
                "pyinstaller": {
                    "module_path": str(module),
                    "module_sha256": hashlib.sha256(module.read_bytes()).hexdigest(),
                    "package_tree_sha256": current_state_read_driver_release._tool_tree_digest(module.parent),
                },
                "syft": {"version": "1.52.0", "path": str(syft),
                         "sha256": hashlib.sha256(syft.read_bytes()).hexdigest()},
            }
            class Backend:
                def inspect_private_path(self, _path, *, purpose):
                    self_purpose = purpose
                    if self_purpose != "toolchain-executable":
                        raise AssertionError("wrong toolchain purpose")
            self.assertTrue(current_state_read_driver_release._validate_build_tool(tool, Backend()))
            syft.write_bytes(b"tampered")
            self.assertFalse(current_state_read_driver_release._validate_build_tool(tool, Backend()))

    def test_resource_contract_is_closed_to_six_single_get_ports(self) -> None:
        contract = json.loads(RESOURCE_CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["schema_version"], "nac.m365-current-state-read-driver-resources/v0.1")
        self.assertEqual(
            set(contract["operations"]),
            {
                "teams_tab_metadata",
                "sharepoint_app_catalog",
                "entra_api_permission",
                "azure_function_metadata",
                "azure_function_request_log",
                "sharepoint_access_decision",
            },
        )
        for operation in contract["operations"].values():
            self.assertEqual(operation["method"], "GET")
            self.assertEqual(operation["maximum_reads_per_acquisition"], 1)
            self.assertFalse(operation["follow_redirects"])
            self.assertEqual(operation["automatic_retries"], 0)
            self.assertFalse(operation["pagination"])
            self.assertFalse(operation["request_body"])
            self.assertTrue(operation["fixed_path_template"])
            self.assertIsInstance(operation["allowed_query"], dict)
            self.assertTrue(operation["allowed_response_fields"])
        self.assertEqual(contract["maximum_microsoft_reads_per_full_acquisition"], 6)

    def test_release_contract_binds_historical_digest_and_distinct_states(self) -> None:
        contract = json.loads(RELEASE_CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["schema_version"], "nac.m365-current-state-read-driver-release/v0.1")
        self.assertEqual(contract["leading_issue"], "https://github.com/notariat8/NaC/issues/748")
        self.assertEqual(
            contract["historical_contract_sha256"],
            hashlib.sha256(HISTORICAL_CONTRACT.read_bytes()).hexdigest(),
        )
        self.assertEqual(set(contract["states"]), {"OFFLINE_REVIEWABLE", "LIVE_CAPABLE"})
        self.assertFalse(contract["states"]["OFFLINE_REVIEWABLE"]["provider_access"])
        self.assertTrue(contract["states"]["LIVE_CAPABLE"]["requires_no_refresh_proof"])
        self.assertTrue(contract["states"]["LIVE_CAPABLE"]["requires_separate_real_read_approval"])
        self.assertEqual(contract["forbidden_effect_counters"]["login"], 0)
        self.assertEqual(contract["forbidden_effect_counters"]["token_refresh"], 0)
        self.assertEqual(contract["forbidden_effect_counters"]["provider_write"], 0)

    def test_resource_validator_rejects_forged_origin_and_extra_operation(self) -> None:
        contract = json.loads(RESOURCE_CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(validate_m365_current_state_read_driver.validate_resources(contract), [])
        contract["operations"]["teams_tab_metadata"]["origin_template"] = "https://example.invalid"
        self.assertIn(
            "RESOURCE_CONTRACT_DRIFT",
            validate_m365_current_state_read_driver.validate_resources(contract),
        )
        contract = json.loads(RESOURCE_CONTRACT.read_text(encoding="utf-8"))
        contract["operations"]["directory_search"] = contract["operations"]["teams_tab_metadata"]
        self.assertIn(
            "RESOURCE_CONTRACT_DRIFT",
            validate_m365_current_state_read_driver.validate_resources(contract),
        )

    def test_release_validator_rejects_historical_digest_and_live_unlock(self) -> None:
        contract = json.loads(RELEASE_CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(
            validate_m365_current_state_read_driver.validate_release_contract(
                contract, HISTORICAL_CONTRACT.read_bytes()
            ),
            [],
        )
        contract["historical_contract_sha256"] = "0" * 64
        self.assertIn(
            "HISTORICAL_CONTRACT_DRIFT",
            validate_m365_current_state_read_driver.validate_release_contract(
                contract, HISTORICAL_CONTRACT.read_bytes()
            ),
        )
        contract = json.loads(RELEASE_CONTRACT.read_text(encoding="utf-8"))
        contract["states"]["LIVE_CAPABLE"]["enabled_by_this_contract"] = True
        self.assertIn(
            "LIVE_CAPABILITY_NOT_AUTHORIZED",
            validate_m365_current_state_read_driver.validate_release_contract(
                contract, HISTORICAL_CONTRACT.read_bytes()
            ),
        )

    def test_release_validator_rejects_malformed_lists_without_exception(self) -> None:
        contract = json.loads(RELEASE_CONTRACT.read_text(encoding="utf-8"))
        contract["acceptance_ids"] = 0
        self.assertIn(
            "RELEASE_CONTRACT_DRIFT",
            validate_m365_current_state_read_driver.validate_release_contract(
                contract, HISTORICAL_CONTRACT.read_bytes()
            ),
        )
        for field, replacement in (
            ("required_remote_checks", {"checks": []}),
            ("release_artifacts", []),
            ("side_effects_allowed_offline", {"microsoft_provider_read": True}),
        ):
            with self.subTest(field=field):
                contract = json.loads(RELEASE_CONTRACT.read_text(encoding="utf-8"))
                contract[field] = replacement
                self.assertIn(
                    "RELEASE_CONTRACT_DRIFT",
                    validate_m365_current_state_read_driver.validate_release_contract(
                        contract, HISTORICAL_CONTRACT.read_bytes()
                    ),
                )

    def test_resource_validator_rejects_unrecognised_contract_field(self) -> None:
        contract = json.loads(RESOURCE_CONTRACT.read_text(encoding="utf-8"))
        contract["unrestricted_read"] = True
        self.assertIn(
            "RESOURCE_CONTRACT_DRIFT",
            validate_m365_current_state_read_driver.validate_resources(contract),
        )

    def test_production_factory_blocks_before_credential_or_network_access(self) -> None:
        calls: list[str] = []

        def credential_provider() -> object:
            calls.append("credential")
            return object()

        def transport_provider() -> object:
            calls.append("network")
            return object()

        with self.assertRaises(ReadDriverBlocked) as raised:
            create_production_microsoft_port(
                credential_provider=credential_provider,
                transport_provider=transport_provider,
            )
        self.assertEqual(raised.exception.code, "BLOCKED_NO_REFRESH_CAPABILITY")
        self.assertEqual(calls, [])

    def test_redacted_projection_rejects_extra_fields_and_unsafe_values(self) -> None:
        accepted = {
            "request_observed": False,
            "http_class": "none",
            "request_correlation_binding_sha256": "a" * 64,
        }
        self.assertEqual(
            validate_redacted_projection("azure_function_request_log", accepted),
            accepted,
        )
        for data in (
            {**accepted, "raw_request": "secret"},
            {**accepted, "http_class": "2xx"},
            {**accepted, "http_class": ["401"]},
            {**accepted, "request_correlation_binding_sha256": "ofunk@example.invalid"},
        ):
            with self.subTest(data=data):
                with self.assertRaises(ReadDriverBlocked) as raised:
                    validate_redacted_projection("azure_function_request_log", data)
                self.assertEqual(raised.exception.code, "BLOCKED_RESPONSE_REDACTION")

    def test_unknown_operation_does_not_infer_new_permission(self) -> None:
        with self.assertRaises(ReadDriverBlocked) as raised:
            validate_redacted_projection("directory_search", {})
        self.assertEqual(raised.exception.code, "BLOCKED_RESOURCE_NOT_ALLOWLISTED")

    def test_bundle_attestation_rejects_extra_tampered_and_unbound_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "reader.exe").write_bytes(b"synthetic-reader")
            recorded = {
                "path": "reader.exe",
                "sha256": hashlib.sha256(b"synthetic-reader").hexdigest(),
                "size": len(b"synthetic-reader"),
                "volume_serial": 1,
                "file_id": 42,
                "owner_sid_sha256": "a" * 64,
                "dacl_sha256": "b" * 64,
                "security_descriptor_sha256": "c" * 64,
                "path_sha256": "d" * 64,
            }

            class Backend:
                def current_operator_binding(self):
                    return SimpleNamespace(sid_sha256="a" * 64)

                def validate_current_user_only_directory(self, path):
                    if path != root:
                        raise AssertionError("unexpected release directory")

                def inspect_private_path(self, path, purpose):
                    self_purpose = purpose
                    if self_purpose != "issue748-read-driver-bundle-current-user-only":
                        raise AssertionError("strict Windows file policy not requested")
                    return SimpleNamespace(
                        **{**recorded, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                           "reparse_point": False}
                    )

            backend = Backend()
            self.assertEqual(verify_bundle_files(root, [recorded], backend), recorded["sha256"])
            for field, value in (
                ("file_id", 43), ("volume_serial", 2),
                ("owner_sid_sha256", "f" * 64),
                ("dacl_sha256", "e" * 64),
                ("path_sha256", "0" * 64),
            ):
                with self.subTest(field=field), self.assertRaises(ReadDriverBlocked):
                    verify_bundle_files(root, [{**recorded, field: value}], backend)
            (root / "extra.dll").write_bytes(b"extra")
            with self.assertRaises(ReadDriverBlocked):
                verify_bundle_files(root, [recorded], backend)
            (root / "extra.dll").unlink()
            (root / "reader.exe").write_bytes(b"tampered")
            with self.assertRaises(ReadDriverBlocked):
                verify_bundle_files(root, [recorded], backend)
            with self.assertRaises(ReadDriverBlocked):
                verify_bundle_files(root, [{**recorded, "path": "../reader.exe"}], backend)


if __name__ == "__main__":
    unittest.main()
