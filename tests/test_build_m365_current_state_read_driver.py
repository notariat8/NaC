"""Hermetic fail-closed checks for the Issue #748 offline candidate builder."""

from __future__ import annotations

import importlib.util
import io
import json
from contextlib import redirect_stdout
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
    def test_current_contract_allows_preparation_but_blocks_release(self) -> None:
        builder.require_candidate_contract_gate(builder.ROOT, phase="prepare")
        with self.assertRaisesRegex(
            builder.BuildBlocked, "BLOCKED_RELEASE_CANDIDATE_NOT_AUTHORIZED",
        ):
            builder.require_candidate_contract_gate(builder.ROOT, phase="release")

    def test_preparation_needs_explicit_contract_flag(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "workflows" / "verification-contracts"
            path.mkdir(parents=True)
            (path / "m365-current-state-read-driver.verification.json").write_text(
                json.dumps({"side_effects_allowed_offline": {
                    "repository_external_preparation_candidate": False,
                    "repository_external_release_candidate": False,
                }}), encoding="utf-8",
            )
            with self.assertRaisesRegex(
                builder.BuildBlocked, "BLOCKED_RELEASE_CANDIDATE_NOT_AUTHORIZED",
            ):
                builder.require_candidate_contract_gate(root, phase="prepare")
            with self.assertRaisesRegex(
                builder.BuildBlocked, "BLOCKED_RELEASE_CANDIDATE_NOT_AUTHORIZED",
            ):
                builder.require_candidate_contract_gate(root, phase="unknown")

    def test_release_modes_block_without_creating_output_or_touching_toolchain(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            for mode in ("build", "finalize"):
                output = Path(folder) / mode
                arguments = [
                    "--mode", mode, "--output", str(output),
                    "--expected-head", "a" * 40, "--expected-tree", "b" * 40,
                ]
                arguments.extend(("--license-evidence-dir", folder))
                with self.subTest(mode=mode):
                    with mock.patch.object(builder, "require_windows_security") as security:
                        with mock.patch.object(builder, "_tool_versions") as tools:
                            self.assertEqual(builder.main(arguments), 1)
                            self.assertFalse(output.exists())
                            security.assert_not_called()
                            tools.assert_not_called()

    def test_preparation_still_rejects_wrong_source_before_toolchain_or_output(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "candidate"
            with mock.patch.object(
                builder, "require_windows_security",
                return_value=(mock.Mock(), mock.Mock()),
            ), mock.patch.object(
                builder, "validate_output_path", return_value=output,
            ), mock.patch.object(
                builder, "validate_source_state",
                side_effect=builder.BuildBlocked("BLOCKED_SOURCE_HEAD_MISMATCH"),
            ) as source, mock.patch.object(builder, "_tool_versions") as tools:
                status = io.StringIO()
                with redirect_stdout(status):
                    self.assertEqual(builder.main([
                        "--mode", "prepare", "--output", str(output),
                        "--expected-head", "a" * 40,
                        "--expected-tree", "b" * 40,
                    ]), 1)
                self.assertIn("BLOCKED_SOURCE_HEAD_MISMATCH", status.getvalue())
                source.assert_called_once()
                self.assertFalse(output.exists())
                tools.assert_not_called()

    def test_reviewed_catalog_is_independent_of_operator_inventory(self) -> None:
        component = {
            "id": "nac", "name": "NaC", "version": "test",
            "license": "AGPL-3.0-or-later", "license_text_path": "LICENSE",
            "license_text_sha256": "a" * 64,
        }
        catalog = {
            "schema_version": "nac.m365-current-state-read-driver-license-catalog/v0.1",
            "status": "APPROVED",
            "reviewed_preparation": {},
            "components": [{**component, "source_uri": "git:HEAD",
                            "source_sha256": "BOUND_SOURCE_TREE"}],
            "files": [{"path": "reader.exe", "component_ids": ["nac"]}],
        }
        inventory = {
            "schema_version": "nac.m365-current-state-read-driver-license-inventory/v0.1",
            "components": [{**component, "cyclonedx_ref": None, "spdx_id": None}],
            "files": [{"path": "reader.exe", "component_ids": ["nac"]}],
        }
        builder.validate_reviewed_license_catalog(
            catalog, inventory, {"reader.exe"}, expected_tree="b" * 40,
            reviewed_preparation={},
        )
        with self.assertRaisesRegex(builder.BuildBlocked, "BLOCKED_LICENSE_PROVENANCE"):
            builder.validate_reviewed_license_catalog(
                catalog, inventory, {"reader.exe"}, expected_tree="b" * 40,
                reviewed_preparation={"bundle_files": "drifted"},
            )
        inventory["components"][0]["license"] = "MIT"
        with self.assertRaisesRegex(builder.BuildBlocked, "BLOCKED_LICENSE_PROVENANCE"):
            builder.validate_reviewed_license_catalog(
                catalog, inventory, {"reader.exe"}, expected_tree="b" * 40,
                reviewed_preparation={},
            )
        inventory["components"][0]["license"] = "AGPL-3.0-or-later"
        catalog["status"] = "PENDING"
        with self.assertRaisesRegex(builder.BuildBlocked, "BLOCKED_LICENSE_PROVENANCE"):
            builder.validate_reviewed_license_catalog(
                catalog, inventory, {"reader.exe"}, expected_tree="b" * 40,
                reviewed_preparation={},
            )

    def test_reviewed_catalog_rejects_unmapped_file_and_unbound_source(self) -> None:
        catalog = {
            "schema_version": "nac.m365-current-state-read-driver-license-catalog/v0.1",
            "status": "APPROVED",
            "reviewed_preparation": {},
            "components": [{
                "id": "runtime", "name": "Runtime", "version": "1.0",
                "license": "MIT", "license_text_path": "licenses/runtime.txt",
                "license_text_sha256": "a" * 64,
                "source_uri": "https://example.org/runtime.zip",
                "source_sha256": "c" * 64,
            }],
            "files": [{"path": "runtime.dll", "component_ids": ["runtime"]}],
        }
        inventory = {
            "schema_version": "nac.m365-current-state-read-driver-license-inventory/v0.1",
            "components": [{
                **{key: value for key, value in catalog["components"][0].items()
                   if key not in {"source_uri", "source_sha256"}},
                "cyclonedx_ref": "c" * 16,
                "spdx_id": "SPDXRef-Package-runtime-" + "c" * 16,
            }],
            "files": [{"path": "runtime.dll", "component_ids": ["runtime"]}],
        }
        with self.assertRaisesRegex(builder.BuildBlocked, "BLOCKED_LICENSE_PROVENANCE"):
            builder.validate_reviewed_license_catalog(
                catalog, inventory, {"runtime.dll", "extra.dll"},
                expected_tree="b" * 40, reviewed_preparation={},
            )
        catalog["files"].append({"path": "extra.dll", "component_ids": ["runtime"]})
        inventory["files"].append({"path": "extra.dll", "component_ids": ["runtime"]})
        catalog["components"][0]["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(builder.BuildBlocked, "BLOCKED_LICENSE_PROVENANCE"):
            builder.validate_reviewed_license_catalog(
                catalog, inventory, {"runtime.dll", "extra.dll"},
                expected_tree="b" * 40, reviewed_preparation={},
            )
        catalog["components"][0]["source_sha256"] = "c" * 64
        catalog["components"][0]["license"] = "NOASSERTION"
        inventory["components"][0]["license"] = "NOASSERTION"
        with self.assertRaisesRegex(builder.BuildBlocked, "BLOCKED_LICENSE_PROVENANCE"):
            builder.validate_reviewed_license_catalog(
                catalog, inventory, {"runtime.dll", "extra.dll"},
                expected_tree="b" * 40, reviewed_preparation={},
            )
        catalog["components"][0]["license"] = "MIT"
        inventory["components"][0]["license"] = "MIT"
        inventory["files"][1]["component_ids"] = []
        with self.assertRaisesRegex(builder.BuildBlocked, "BLOCKED_LICENSE_PROVENANCE"):
            builder.validate_reviewed_license_catalog(
                catalog, inventory, {"runtime.dll", "extra.dll"},
                expected_tree="b" * 40, reviewed_preparation={},
            )
    def test_inventory_component_assignment_must_match_both_sbom_locations(self) -> None:
        inventory = {
            "components": [
                {"id": "nac", "name": "NaC", "version": "test",
                 "cyclonedx_ref": "pkg:nac", "spdx_id": "SPDXRef-nac"},
                {"id": "python", "name": "Python", "version": "3",
                 "cyclonedx_ref": "pkg:python", "spdx_id": "SPDXRef-python"},
            ],
            "files": [
                {"path": "reader.exe", "component_ids": ["nac", "python"]},
            ],
        }
        binding = SimpleNamespace(
            file_packages={"reader.exe": ("SPDXRef-nac", "SPDXRef-python")},
            packages=(
                {"spdx_id": "SPDXRef-nac", "cyclonedx_ref": "pkg:nac",
                 "name": "NaC", "version": "test"},
                {"spdx_id": "SPDXRef-python", "cyclonedx_ref": "pkg:python",
                 "name": "Python", "version": "3"},
            ),
        )
        builder.validate_inventory_bundle_mapping(inventory, binding)
        with self.assertRaisesRegex(builder.BuildBlocked, "BLOCKED_LICENSE_SBOM_FILE_MISMATCH"):
            builder.validate_inventory_bundle_mapping(
                inventory, SimpleNamespace(
                    file_packages={"reader.exe": ("SPDXRef-nac",)},
                    packages=binding.packages,
                ),
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
