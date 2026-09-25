"""Offline mapping tests for Syft 1.52.0 directory-bundle SBOMs."""

from __future__ import annotations

import copy
import unittest

from nac_bff.current_state_read_driver_sbom import (
    SbomMappingError, parse_syft_sboms, require_inventory_file_attribution,
)


def _fixture() -> tuple[dict, dict, set[str]]:
    cdx = {
        "bomFormat": "CycloneDX",
        "metadata": {"component": {"bom-ref": "bundle-root"}},
        "components": [
            {
                "bom-ref": "a1b2c3d4e5f60708", "name": "Runtime Stub DLL",
                "version": "10.0.1", "properties": [
                    {"name": "syft:location:0:path", "value": "\\_internal\\api-ms-win-core-console.dll"},
                ],
            },
            {
                "bom-ref": "1111222233334444", "name": "VCRUNTIME140.dll",
                "version": "14.44.1", "properties": [
                    {"name": "syft:location:0:path", "value": "\\_internal\\VCRUNTIME140.dll"},
                ],
            },
        ],
    }
    spdx = {
        "spdxVersion": "SPDX-2.3",
        "packages": [
            {"SPDXID": "SPDXRef-DocumentRoot-Directory-0", "name": "bundle", "versionInfo": ""},
            {"SPDXID": "SPDXRef-Package-binary-runtime-a1b2c3d4e5f60708",
             "name": "Runtime Stub DLL", "versionInfo": "10.0.1"},
            {"SPDXID": "SPDXRef-Package-binary-vcruntime-1111222233334444",
             "name": "VCRUNTIME140.dll", "versionInfo": "14.44.1"},
        ],
        "files": [
            {"SPDXID": "SPDXRef-File-console", "fileName": "\\_internal\\api-ms-win-core-console.dll"},
            {"SPDXID": "SPDXRef-File-runtime", "fileName": "\\_internal\\VCRUNTIME140.dll"},
        ],
        "relationships": [
            {"spdxElementId": "SPDXRef-Package-binary-runtime-a1b2c3d4e5f60708",
             "relationshipType": "OTHER", "relatedSpdxElement": "SPDXRef-File-console"},
            {"spdxElementId": "SPDXRef-Package-binary-vcruntime-1111222233334444",
             "relationshipType": "OTHER", "relatedSpdxElement": "SPDXRef-File-runtime"},
            {"spdxElementId": "SPDXRef-DocumentRoot-Directory-0",
             "relationshipType": "CONTAINS",
             "relatedSpdxElement": "SPDXRef-Package-binary-runtime-a1b2c3d4e5f60708"},
            {"spdxElementId": "SPDXRef-DocumentRoot-Directory-0",
             "relationshipType": "CONTAINS",
             "relatedSpdxElement": "SPDXRef-Package-binary-vcruntime-1111222233334444"},
            {"spdxElementId": "SPDXRef-DOCUMENT", "relationshipType": "DESCRIBES",
             "relatedSpdxElement": "SPDXRef-DocumentRoot-Directory-0"},
        ],
    }
    paths = {
        "_internal/api-ms-win-core-console.dll", "_internal/VCRUNTIME140.dll",
        "_internal/base_library.zip",
    }
    return cdx, spdx, paths


class SyftSbomMappingTests(unittest.TestCase):
    def test_sanitized_observed_47_package_55_file_shape(self) -> None:
        cdx = {"bomFormat": "CycloneDX", "components": []}
        spdx = {
            "spdxVersion": "SPDX-2.3",
            "packages": [{"SPDXID": "SPDXRef-DocumentRoot-Directory-0", "name": "bundle"}],
            "files": [], "relationships": [],
        }
        paths = set()
        for number in range(47):
            ref = f"{number:016x}"
            path = f"_internal/binary-{number:02d}.dll"
            package_id = f"SPDXRef-Package-binary-{number:02d}-{ref}"
            file_id = f"SPDXRef-File-binary-{number:02d}"
            paths.add(path)
            cdx["components"].append({
                "bom-ref": ref, "name": f"Binary {number:02d}", "version": "1",
                "properties": [{"name": "syft:location:0:path",
                                "value": "\\" + path.replace("/", "\\")}],
            })
            spdx["packages"].append({
                "SPDXID": package_id, "name": f"Binary {number:02d}",
                "versionInfo": "1",
            })
            spdx["files"].append({"SPDXID": file_id, "fileName": "\\" + path})
            spdx["relationships"].append({
                "spdxElementId": package_id, "relationshipType": "OTHER",
                "relatedSpdxElement": file_id,
            })
            spdx["relationships"].append({
                "spdxElementId": "SPDXRef-DocumentRoot-Directory-0",
                "relationshipType": "CONTAINS", "relatedSpdxElement": package_id,
            })
        for number in range(7):
            path = f"_internal/unattributed-{number:02d}.dat"
            paths.add(path)
            spdx["files"].append({
                "SPDXID": f"SPDXRef-File-unattributed-{number:02d}",
                "fileName": "\\" + path,
            })
        paths.add("_internal/base_library.zip")  # Present in bundle; absent in SPDX files.
        spdx["relationships"].append({
            "spdxElementId": "SPDXRef-DOCUMENT", "relationshipType": "DESCRIBES",
            "relatedSpdxElement": "SPDXRef-DocumentRoot-Directory-0",
        })
        self.assertEqual(len(spdx["relationships"]), 95)
        result = parse_syft_sboms(cdx, spdx, paths)
        self.assertEqual(len(result.packages), 47)
        self.assertEqual(len(result.file_packages), 55)
        self.assertEqual(len(result.uncovered_files), 8)
        self.assertIn("_internal/base_library.zip", result.uncovered_files)

    def test_realistic_syft_properties_reconcile_without_whole_bundle_claim(self) -> None:
        cdx, spdx, paths = _fixture()
        result = parse_syft_sboms(cdx, spdx, paths)
        self.assertEqual(len(result.packages), 2)
        runtime = next(package for package in result.packages
                       if package["cyclonedx_ref"] == "a1b2c3d4e5f60708")
        self.assertEqual(runtime["spdx_id"],
                         "SPDXRef-Package-binary-runtime-a1b2c3d4e5f60708")
        self.assertEqual(runtime["name"], "Runtime Stub DLL")
        self.assertEqual(runtime["version"], "10.0.1")
        self.assertEqual(runtime["paths"],
                         ("_internal/api-ms-win-core-console.dll",))
        self.assertEqual(result.file_packages["_internal/VCRUNTIME140.dll"],
                         ("SPDXRef-Package-binary-vcruntime-1111222233334444",))
        self.assertEqual(result.file_packages["_internal/base_library.zip"], ())
        self.assertEqual(result.uncovered_files, ("_internal/base_library.zip",))

    def test_uncovered_file_needs_explicit_non_sbom_component(self) -> None:
        cdx, spdx, paths = _fixture()
        mapping = parse_syft_sboms(cdx, spdx, paths)
        components = {
            "runtime": {"spdx_id": "SPDXRef-Package-binary-runtime-a1b2c3d4e5f60708"},
            "vcruntime": {"spdx_id": "SPDXRef-Package-binary-vcruntime-1111222233334444"},
            "manual": {"spdx_id": None},
        }
        files = [
            {"path": "_internal/api-ms-win-core-console.dll", "component_ids": ["runtime"]},
            {"path": "_internal/VCRUNTIME140.dll", "component_ids": ["vcruntime"]},
            {"path": "_internal/base_library.zip", "component_ids": ["runtime"]},
        ]
        with self.assertRaisesRegex(SbomMappingError, "package-to-file attribution mismatch"):
            require_inventory_file_attribution(files, components, mapping)
        files[-1]["component_ids"] = ["manual"]
        require_inventory_file_attribution(files, components, mapping)

    def test_contained_by_relation_and_multiple_locations_are_supported(self) -> None:
        cdx, spdx, paths = _fixture()
        extra = "_internal/another.dll"
        paths.add(extra)
        cdx["components"][0]["properties"].append(
            {"name": "syft:location:1:path", "value": "\\_internal\\another.dll"})
        spdx["files"].append({"SPDXID": "SPDXRef-File-another", "fileName": "./" + extra})
        spdx["relationships"].append({
            "spdxElementId": "SPDXRef-File-another", "relationshipType": "CONTAINED_BY",
            "relatedSpdxElement": "SPDXRef-Package-binary-runtime-a1b2c3d4e5f60708",
        })
        result = parse_syft_sboms(cdx, spdx, paths)
        runtime = next(package for package in result.packages
                       if package["cyclonedx_ref"] == "a1b2c3d4e5f60708")
        self.assertEqual(runtime["paths"],
                         ("_internal/another.dll", "_internal/api-ms-win-core-console.dll"))

    def test_rejects_duplicate_refs_and_identity_mismatch(self) -> None:
        for mutation in ("cdx_ref", "spdx_id", "name", "version"):
            with self.subTest(mutation=mutation):
                cdx, spdx, paths = _fixture()
                if mutation == "cdx_ref":
                    cdx["components"][1]["bom-ref"] = cdx["components"][0]["bom-ref"]
                elif mutation == "spdx_id":
                    spdx["packages"][2]["SPDXID"] = spdx["packages"][1]["SPDXID"]
                elif mutation == "name":
                    spdx["packages"][1]["name"] = "different"
                else:
                    spdx["packages"][1]["versionInfo"] = "different"
                with self.assertRaises(SbomMappingError):
                    parse_syft_sboms(cdx, spdx, paths)

    def test_rejects_unsafe_and_out_of_bundle_locations(self) -> None:
        for location in (
            "\\..\\outside.dll", "\\\\server\\share\\outside.dll",
            "C:\\outside.dll", "\\_internal\\missing.dll", "\\_internal\\..\\reader.exe",
        ):
            with self.subTest(location=location):
                cdx, spdx, paths = _fixture()
                cdx["components"][0]["properties"][0]["value"] = location
                with self.assertRaises(SbomMappingError):
                    parse_syft_sboms(cdx, spdx, paths)

    def test_rejects_conflicting_locations_and_missing_relations(self) -> None:
        for mutation in ("wrong_file", "missing_relation", "unknown_file",
                         "root_relation", "missing_root_containment"):
            with self.subTest(mutation=mutation):
                cdx, spdx, paths = _fixture()
                if mutation == "wrong_file":
                    spdx["relationships"][0]["relatedSpdxElement"] = "SPDXRef-File-runtime"
                elif mutation == "missing_relation":
                    spdx["relationships"].pop(0)
                elif mutation == "unknown_file":
                    spdx["relationships"][0]["relatedSpdxElement"] = "SPDXRef-File-unknown"
                elif mutation == "root_relation":
                    spdx["relationships"][0]["spdxElementId"] = "SPDXRef-DocumentRoot-Directory-0"
                else:
                    spdx["relationships"].pop(2)
                with self.assertRaises(SbomMappingError):
                    parse_syft_sboms(cdx, spdx, paths)

    def test_rejects_ambiguous_suffix_and_unresolved_packages(self) -> None:
        for mutation in ("ambiguous", "unmatched", "missing_location", "extra_package"):
            with self.subTest(mutation=mutation):
                cdx, spdx, paths = _fixture()
                if mutation == "ambiguous":
                    spdx["packages"].append(copy.deepcopy(spdx["packages"][1]))
                    spdx["packages"][-1]["SPDXID"] = (
                        "SPDXRef-Package-other-a1b2c3d4e5f60708")
                elif mutation == "unmatched":
                    spdx["packages"][1]["SPDXID"] = "SPDXRef-Package-binary-runtime-deadbeef"
                elif mutation == "missing_location":
                    cdx["components"][0]["properties"] = []
                else:
                    spdx["packages"].append({
                        "SPDXID": "SPDXRef-Package-extra-deadbeef",
                        "name": "extra", "versionInfo": "1"})
                with self.assertRaises(SbomMappingError):
                    parse_syft_sboms(cdx, spdx, paths)

    def test_rejects_ambiguous_file_ids_and_duplicate_relationships(self) -> None:
        for mutation in ("duplicate_id", "duplicate_path", "duplicate_relation"):
            with self.subTest(mutation=mutation):
                cdx, spdx, paths = _fixture()
                if mutation == "duplicate_id":
                    spdx["files"][1]["SPDXID"] = spdx["files"][0]["SPDXID"]
                elif mutation == "duplicate_path":
                    spdx["files"][1]["fileName"] = spdx["files"][0]["fileName"]
                else:
                    spdx["relationships"].append(copy.deepcopy(spdx["relationships"][0]))
                with self.assertRaises(SbomMappingError):
                    parse_syft_sboms(cdx, spdx, paths)

    def test_rejects_extra_root_and_contradictory_occurrence(self) -> None:
        cdx, spdx, paths = _fixture()
        spdx["packages"].append({
            "SPDXID": "SPDXRef-DocumentRoot-Directory-1", "name": "other-root"})
        with self.assertRaises(SbomMappingError):
            parse_syft_sboms(cdx, spdx, paths)
        cdx, spdx, paths = _fixture()
        cdx["components"][0]["evidence"] = {
            "occurrences": [{"location": "\\_internal\\VCRUNTIME140.dll"}]}
        with self.assertRaises(SbomMappingError):
            parse_syft_sboms(cdx, spdx, paths)


if __name__ == "__main__":
    unittest.main()
