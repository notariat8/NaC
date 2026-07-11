from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from notary_kg.business_case_inventory import (  # noqa: E402
    build_business_case_inventory,
    validate_business_case_inventory,
)
from notary_kg.process_ontology_contract import (  # noqa: E402
    build_process_ontology_contract,
    validate_process_ontology_contract,
)


class BusinessCaseTypeIdContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.inventory = build_business_case_inventory(REPO_ROOT)

    def _inventory_entry(self, slug: str) -> dict:
        return next(item for item in self.inventory["business_cases"] if item["slug"] == slug)

    def _assert_inventory_rejected(self, *messages: str) -> None:
        validation = validate_business_case_inventory(self.inventory)
        self.assertEqual(validation.status, "FAILED")
        joined = "\n".join(validation.errors)
        for message in messages:
            self.assertIn(message, joined)

    def test_inventory_distinguishes_20_canonical_types_and_2_direct_aliases(self) -> None:
        validation = validate_business_case_inventory(self.inventory)
        self.assertEqual(self.inventory["schema_version"], "nac.notarial-business-case-inventory/v0.2")
        self.assertEqual(validation.status, "PASSED")
        self.assertEqual(self.inventory["summary"]["business_case_count"], 22)
        self.assertEqual(self.inventory["summary"]["canonical_business_case_type_count"], 20)
        self.assertEqual(self.inventory["summary"]["legacy_alias_count"], 2)

        canonical = [item for item in self.inventory["business_cases"] if item["catalog_entry_kind"] == "canonical"]
        aliases = [item for item in self.inventory["business_cases"] if item["catalog_entry_kind"] == "legacy_alias"]
        self.assertTrue(all(item["business_case_type_id"] == item["slug"] for item in canonical))
        self.assertTrue(all("business_case_type_id" not in item for item in aliases))
        self.assertEqual(
            self._inventory_entry("grundstueckskaufvertrag")["legacy_alias"]["target"]["business_case_type_id"],
            "immobilienkaufvertrag",
        )
        self.assertEqual(
            self._inventory_entry("testament")["legacy_alias"]["target"]["business_case_type_id"],
            "testament-erbvertrag",
        )

    def test_rejects_non_exact_and_overlength_canonical_ids(self) -> None:
        entry = self._inventory_entry("immobilienkaufvertrag")
        for invalid in ("Immobilienkaufvertrag", " immobilienkaufvertrag", "a" * 129):
            with self.subTest(invalid=invalid):
                mutated = copy.deepcopy(self.inventory)
                self.inventory = mutated
                self._inventory_entry("immobilienkaufvertrag")["business_case_type_id"] = invalid
                self._assert_inventory_rejected("canonical business_case_type_id")
                self.inventory = build_business_case_inventory(REPO_ROOT)
        self.assertEqual(entry["business_case_type_id"], "immobilienkaufvertrag")

    def test_rejects_alias_canonical_id_and_malformed_target(self) -> None:
        alias = self._inventory_entry("testament")
        alias["business_case_type_id"] = "testament"
        alias["legacy_alias"] = {"target": ["testament-erbvertrag"]}
        self._assert_inventory_rejected(
            "alias must not have a canonical business_case_type_id",
            "alias target must contain exactly business_case_type_id",
        )

    def test_rejects_unknown_chain_cycle_and_self_target(self) -> None:
        cases = (
            ("unknown-target", {"testament": "nicht-bekannt"}, "unknown canonical alias target"),
            ("chain", {"testament": "grundstueckskaufvertrag"}, "alias chains are not allowed"),
            (
                "cycle",
                {"testament": "grundstueckskaufvertrag", "grundstueckskaufvertrag": "testament"},
                "alias cycle detected",
            ),
            ("self", {"testament": "testament"}, "alias target must not reference itself"),
        )
        for name, targets, expected in cases:
            with self.subTest(name=name):
                self.inventory = build_business_case_inventory(REPO_ROOT)
                for alias_slug, target in targets.items():
                    self._inventory_entry(alias_slug)["legacy_alias"]["target"]["business_case_type_id"] = target
                self._assert_inventory_rejected(expected)

    def test_rejects_alias_collision_and_duplicate_catalog_entry(self) -> None:
        alias = self._inventory_entry("testament")
        alias["slug"] = "testament-erbvertrag"
        duplicate = copy.deepcopy(self._inventory_entry("grundstueckskaufvertrag"))
        self.inventory["business_cases"].append(duplicate)
        self._assert_inventory_rejected("alias/canonical ID collisions", "duplicate catalog slug")


    def test_rejects_type_validity_dependency_drift(self) -> None:
        self.inventory["type_validity_dependencies"]["bpmn_model_required"] = True
        self._assert_inventory_rejected("validity dependency contract mismatch")


    def test_rejects_non_object_catalog_entry_without_crashing(self) -> None:
        self.inventory["business_cases"][0] = None
        self._assert_inventory_rejected("business_cases[0] must be an object")


class ProcessOntologyTypeValidityContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = build_process_ontology_contract(REPO_ROOT)

    def _assert_contract_rejected(self, message: str) -> None:
        validation = validate_process_ontology_contract(self.payload)
        self.assertEqual(validation.status, "FAILED")
        self.assertIn(message, "\n".join(validation.errors))

    def test_rejects_non_object_contract_without_crashing(self) -> None:
        self.payload["contract"] = []
        self._assert_contract_rejected("contract must be an object")

    def test_contract_is_viewer_independent_and_process_bpmn_optional(self) -> None:
        validation = validate_process_ontology_contract(self.payload)
        self.assertEqual(self.payload["schema_version"], "nac.notarial-process-ontology/v2")
        self.assertEqual(validation.status, "PASSED")
        derived = self.payload["evaluation"]["derived_decision"]
        self.assertTrue(derived["type_validity_requires_vorgangsartenregister"])
        self.assertFalse(derived["type_validity_requires_process_register"])
        self.assertFalse(derived["type_validity_requires_bpmn_model"])
        self.assertFalse(derived["type_validity_requires_viewer"])

    def test_rejects_runtime_dependency_drift(self) -> None:
        runtime = self.payload["contract"]["runtime_type_validity"]
        runtime["required_dependencies"].append("Prozessregister")
        self._assert_contract_rejected("type validity must depend exactly")

    def test_rejects_missing_required_type_registry(self) -> None:
        rules = self.payload["contract"]["sharepoint_projection_rules"]
        rules["required_lists_or_libraries"].remove("Vorgangsartenregister")
        self._assert_contract_rejected("Vorgangsartenregister must be a required projection")

    def test_rejects_process_key_equivalence_drift(self) -> None:
        process_key = self.payload["contract"]["sharepoint_projection_rules"]["projection_contracts"]["Prozessregister"]["process_key"]
        process_key["equals_business_case_type_id_when_present"] = False
        self._assert_contract_rejected("equals_business_case_type_id_when_present")

    def test_rejects_required_process_or_bpmn_projection(self) -> None:
        projections = self.payload["contract"]["sharepoint_projection_rules"]["projection_contracts"]
        projections["Prozessregister"]["required_for_type_validity"] = True
        projections["BPMN Models"]["required_for_type_validity"] = True
        self._assert_contract_rejected("Prozessregister must not be required for type validity")
        self._assert_contract_rejected("BPMN Models must not be required for type validity")

    def test_rejects_non_nullable_bpmn_link_contract(self) -> None:
        process = self.payload["contract"]["sharepoint_projection_rules"]["projection_contracts"]["Prozessregister"]
        process["nullable_bpmn_link_fields"].remove("NacBpmnModelId")
        self._assert_contract_rejected("all Prozessregister BPMN link fields must be nullable")


if __name__ == "__main__":
    unittest.main()
