"""Hermetic fail-closed checks for the Issue #748 offline candidate builder."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/build_m365_current_state_read_driver.py"
SPEC = importlib.util.spec_from_file_location("read_driver_builder", SCRIPT)
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class CandidateBuilderBoundaryTests(unittest.TestCase):
    def test_sbom_component_locations_must_cover_exact_bundle_files(self) -> None:
        cdx = {
            "bomFormat": "CycloneDX",
            "metadata": {"component": {"bom-ref": "scan-root"}},
            "components": [{"bom-ref": "pkg:nac", "evidence": {
                "occurrences": [{"location": "reader.exe"}]
            }}],
        }
        spdx = {
            "spdxVersion": "SPDX-2.3",
            "packages": [{"SPDXID": "SPDXRef-nac"}],
            "files": [{"SPDXID": "SPDXRef-File-reader", "fileName": "./reader.exe"}],
            "relationships": [{"spdxElementId": "SPDXRef-nac",
                               "relationshipType": "CONTAINS",
                               "relatedSpdxElement": "SPDXRef-File-reader"}],
        }
        mappings = builder.validate_sbom_bundle_mapping(cdx, spdx, {"reader.exe"})
        self.assertEqual(mappings["reader.exe"], ({"pkg:nac"}, {"SPDXRef-nac"}))
        with self.assertRaisesRegex(builder.BuildBlocked, "BLOCKED_SBOM_BUNDLE_MAPPING"):
            builder.validate_sbom_bundle_mapping(cdx, spdx, {"reader.exe", "runtime.dll"})
        cdx["components"][0]["evidence"]["occurrences"] = []
        with self.assertRaisesRegex(builder.BuildBlocked, "BLOCKED_SBOM_BUNDLE_MAPPING"):
            builder.validate_sbom_bundle_mapping(cdx, spdx, {"reader.exe"})

    def test_inventory_component_assignment_must_match_both_sbom_locations(self) -> None:
        inventory = {
            "components": [
                {"id": "nac", "cyclonedx_ref": "pkg:nac", "spdx_id": "SPDXRef-nac"},
                {"id": "python", "cyclonedx_ref": "pkg:python", "spdx_id": "SPDXRef-python"},
            ],
            "files": [
                {"path": "reader.exe", "component_ids": ["nac", "python"]},
            ],
        }
        binding = {"reader.exe": ({"pkg:nac", "pkg:python"},
                                  {"SPDXRef-nac", "SPDXRef-python"})}
        builder.validate_inventory_bundle_mapping(inventory, binding)
        with self.assertRaisesRegex(builder.BuildBlocked, "BLOCKED_LICENSE_SBOM_FILE_MISMATCH"):
            builder.validate_inventory_bundle_mapping(
                inventory, {"reader.exe": ({"pkg:nac"},
                                          {"SPDXRef-nac", "SPDXRef-python"})},
            )

    def test_package_tree_digest_changes_with_executed_tool_source(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            package = Path(folder) / "package"
            package.mkdir()
            source = package / "__main__.py"
            source.write_text("print('one')", encoding="utf-8")
            before = builder._package_tree_digest(package)
            source.write_text("print('two')", encoding="utf-8")
            self.assertNotEqual(before, builder._package_tree_digest(package))

    def test_tool_identity_binds_paths_and_rejects_midcheck_drift(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            syft = Path(folder) / "syft.exe"
            syft.write_bytes(b"syft-one")
            package = Path(folder) / "PyInstaller"
            package.mkdir()
            main = package / "__main__.py"
            main.write_bytes(b"build tool source")
            spec = SimpleNamespace(origin=str(main),
                                   submodule_search_locations=[str(package)])
            backend = SimpleNamespace(inspect_private_path=lambda *_args, **_kwargs: None)
            version = ".".join(str(part) for part in builder.sys.version_info[:3])
            completed = SimpleNamespace(returncode=0, stdout="Version: 1.52.0")
            with (
                mock.patch.object(builder, "PYTHON_VERSION", version),
                mock.patch.object(builder, "require_windows_security", return_value=(backend, None)),
                mock.patch.object(builder.importlib.metadata, "version", return_value="6.22.3"),
                mock.patch.object(builder.importlib.util, "find_spec", return_value=spec),
                mock.patch.object(builder.subprocess, "run", return_value=completed),
            ):
                identity = builder._tool_versions(str(syft))
                self.assertEqual(identity["syft"]["path"], str(syft))
                self.assertEqual(identity["syft"]["sha256"], builder._sha256(syft))
                self.assertEqual(identity["pyinstaller"]["module_sha256"], builder._sha256(main))
                self.assertEqual(identity["python"]["sha256"], builder._sha256(Path(builder.sys.executable)))

                def mutate_syft(*_args, **_kwargs):
                    syft.write_bytes(b"syft-two")
                    return completed

                with mock.patch.object(builder.subprocess, "run", side_effect=mutate_syft):
                    with self.assertRaisesRegex(builder.BuildBlocked, "BLOCKED_BUILD_TOOL_DRIFT"):
                        builder._tool_versions(str(syft))

    def test_output_must_be_new_and_outside_repository(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "repo"
            root.mkdir()
            with self.assertRaisesRegex(builder.BuildBlocked, "BLOCKED_OUTPUT_INSIDE_REPOSITORY"):
                builder.validate_output_path(root, root / "candidate")
            external = Path(folder) / "candidate"
            external.mkdir()
            with self.assertRaisesRegex(builder.BuildBlocked, "BLOCKED_OUTPUT_ALREADY_EXISTS"):
                builder.validate_output_path(root, external)

    def test_clean_git_gate_rejects_any_untracked_file(self) -> None:
        calls = []

        def fake_git(*args):
            calls.append(args)
            return {
                ("rev-parse", "--show-toplevel"): "C:/repo\n",
                ("rev-parse", "HEAD"): "a" * 40 + "\n",
                ("rev-parse", "HEAD^{tree}"): "b" * 40 + "\n",
                ("status", "--porcelain=v1", "--untracked-files=all"): "?? extra.py\n",
            }[args]

        with self.assertRaisesRegex(builder.BuildBlocked, "BLOCKED_SOURCE_NOT_CLEAN"):
            builder.validate_source_state(
                Path("C:/repo"), "a" * 40, "b" * 40, git=fake_git
            )
        self.assertIn(("status", "--porcelain=v1", "--untracked-files=all"), calls)

    def test_wrong_head_blocks_before_any_build(self) -> None:
        def fake_git(*args):
            return {
                ("rev-parse", "--show-toplevel"): "C:/repo\n",
                ("rev-parse", "HEAD"): "c" * 40 + "\n",
                ("rev-parse", "HEAD^{tree}"): "b" * 40 + "\n",
            }[args]

        with self.assertRaisesRegex(builder.BuildBlocked, "BLOCKED_SOURCE_HEAD_MISMATCH"):
            builder.validate_source_state(
                Path("C:/repo"), "a" * 40, "b" * 40, git=fake_git
            )

    def test_license_inventory_requires_exact_file_coverage_and_sbom_refs(self) -> None:
        inventory = {
            "schema_version": "nac.m365-current-state-read-driver-license-inventory/v0.1",
            "components": [
                {
                    "id": "nac", "name": "NaC", "version": "1.0",
                    "license": "AGPL-3.0-or-later", "license_text_path": "LICENSE",
                    "license_text_sha256": "a" * 64,
                    "cyclonedx_ref": "pkg:nac", "spdx_id": "SPDXRef-nac",
                },
                {
                    "id": "bootloader", "name": "PyInstaller", "version": "6.22.3",
                    "license": "GPL-2.0-or-later-with-bootloader-exception",
                    "license_text_path": "licenses/pyinstaller.txt",
                    "license_text_sha256": "b" * 64,
                    "cyclonedx_ref": "pkg:pyinstaller",
                    "spdx_id": "SPDXRef-pyinstaller",
                },
            ],
            "files": [{"path": "reader.exe", "component_ids": ["nac", "bootloader"]}],
        }
        with self.assertRaisesRegex(builder.BuildBlocked, "BLOCKED_LICENSE_INVENTORY_INCOMPLETE"):
            builder.validate_license_inventory(
                inventory, {"reader.exe", "runtime.dll"},
                {"pkg:nac", "pkg:pyinstaller"},
                {"SPDXRef-nac", "SPDXRef-pyinstaller"},
                text_hashes={"LICENSE": "a" * 64,
                             "licenses/pyinstaller.txt": "b" * 64},
            )
        inventory["files"].append({"path": "runtime.dll", "component_ids": ["bootloader"]})
        with self.assertRaisesRegex(builder.BuildBlocked, "BLOCKED_LICENSE_SBOM_REFERENCE"):
            builder.validate_license_inventory(
                inventory, {"reader.exe", "runtime.dll"},
                {"pkg:nac"}, {"SPDXRef-nac", "SPDXRef-pyinstaller"},
                text_hashes={"LICENSE": "a" * 64,
                             "licenses/pyinstaller.txt": "b" * 64},
            )
        builder.validate_license_inventory(
            inventory, {"reader.exe", "runtime.dll"},
            {"pkg:nac", "pkg:pyinstaller"},
            {"SPDXRef-nac", "SPDXRef-pyinstaller"},
            text_hashes={"LICENSE": "a" * 64,
                         "licenses/pyinstaller.txt": "b" * 64},
        )
        with self.assertRaisesRegex(builder.BuildBlocked, "BLOCKED_LICENSE_SBOM_REFERENCE"):
            builder.validate_license_inventory(
                inventory, {"reader.exe", "runtime.dll"},
                {"pkg:nac", "pkg:pyinstaller", "pkg:unattributed"},
                {"SPDXRef-nac", "SPDXRef-pyinstaller"},
                text_hashes={"LICENSE": "a" * 64,
                             "licenses/pyinstaller.txt": "b" * 64},
            )
        with self.assertRaisesRegex(builder.BuildBlocked, "BLOCKED_LICENSE_SBOM_REFERENCE"):
            builder.validate_license_inventory(
                inventory, {"reader.exe", "runtime.dll"},
                {"pkg:nac", "pkg:pyinstaller"},
                {"SPDXRef-nac", "SPDXRef-pyinstaller", "SPDXRef-unattributed"},
                text_hashes={"LICENSE": "a" * 64,
                             "licenses/pyinstaller.txt": "b" * 64},
            )

    def test_license_inventory_rejects_empty_or_duplicate_component_ids(self) -> None:
        inventory = {
            "schema_version": "nac.m365-current-state-read-driver-license-inventory/v0.1",
            "components": [{
                "id": "nac", "name": "NaC", "version": "1.0",
                "license": "AGPL-3.0-or-later", "license_text_path": "LICENSE",
                "license_text_sha256": "a" * 64,
                "cyclonedx_ref": "pkg:nac", "spdx_id": "SPDXRef-nac",
            }],
            "files": [{"path": "reader.exe", "component_ids": []}],
        }
        for identifiers in ([], ["nac", "nac"]):
            inventory["files"][0]["component_ids"] = identifiers
            with self.subTest(identifiers=identifiers):
                with self.assertRaisesRegex(builder.BuildBlocked, "BLOCKED_LICENSE_INVENTORY_INVALID"):
                    builder.validate_license_inventory(
                        inventory, {"reader.exe"}, {"pkg:nac"},
                        {"SPDXRef-nac"}, text_hashes={"LICENSE": "a" * 64},
                    )

    def test_build_stops_before_output_without_windows_acl_backend(self) -> None:
        with mock.patch.object(builder.os, "name", "posix"):
            with self.assertRaisesRegex(builder.BuildBlocked, "BLOCKED_WINDOWS_SECURITY_BACKEND_UNAVAILABLE"):
                builder.require_windows_security()

    def test_git_child_environment_excludes_provider_and_git_overrides(self) -> None:
        with mock.patch.dict(builder.os.environ, {
            "GH_TOKEN": "must-not-pass", "GIT_CONFIG_COUNT": "1",
            "AZURE_ACCESS_TOKEN": "must-not-pass",
        }):
            environment = builder._git_environment()
        self.assertNotIn("GH_TOKEN", environment)
        self.assertNotIn("AZURE_ACCESS_TOKEN", environment)
        self.assertNotIn("GIT_CONFIG_COUNT", environment)
        self.assertEqual(environment["GIT_CONFIG_NOSYSTEM"], "1")
        self.assertEqual(environment["GIT_NO_REPLACE_OBJECTS"], "1")


if __name__ == "__main__":
    unittest.main()
