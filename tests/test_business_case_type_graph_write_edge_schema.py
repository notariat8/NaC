from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nac_m365_graph.business_case_type_write_dry_run import (
    WRITE_DRY_RUN_OPERATIONS,
    _contract_is_valid,
    _synthetic_mutation,
)
from notary_kg.business_case_type_mutation import (
    BusinessCaseTypeMutation,
    MutationValidationError,
    _BOOLEAN_FIELDS,
    _CHOICE_FIELDS_BY_LIST,
    _DATETIME_FIELDS,
    _TEXT_FIELDS,
)


SCHEMA_PATH = (
    ROOT / "deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json"
)
CONTRACT_PATH = (
    ROOT
    / "workflows/contracts/business-case-type-graph-write-edge-s4b.contract.json"
)


def _lists_by_name() -> dict[str, dict[str, Any]]:
    payload = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return {
        item["display_name"]: item
        for item in payload["sharepoint"]["lists"]
    }


def _columns(list_name: str) -> dict[str, dict[str, Any]]:
    return {
        column["name"]: column
        for column in _lists_by_name()[list_name]["columns"]
    }


def _valid_case_fields() -> dict[str, Any]:
    return {
        "NacCaseId": "synthetic-case-schema",
        "Aktenzeichen": "SYN-SCHEMA",
        "Vorgangstyp": "immobilienkaufvertrag",
        "VorgangstypId": "immobilienkaufvertrag",
        "Status": "Entwurf",
        "NotarTeam": "NaC-Notar-01",
        "Vertraulichkeitsstufe": "Normal",
        "NacWorkflowVersion": "workflow-v1",
        "KgVersion": "kg-v1",
    }


class ProvisionedSharePointSchemaValidationTests(unittest.TestCase):
    def test_validator_shape_matches_provisioned_mutation_columns(self) -> None:
        akten = _columns("Akten")
        aufgaben = _columns("AufgabenFristen")

        self.assertEqual(
            _CHOICE_FIELDS_BY_LIST,
            {
                "Akten": {
                    name: frozenset(akten[name]["choices"])
                    for name in (
                        "Vorgangstyp",
                        "Status",
                        "NotarTeam",
                        "Vertraulichkeitsstufe",
                    )
                },
                "AufgabenFristen": {
                    "Status": frozenset(aufgaben["Status"]["choices"])
                },
            },
        )
        provisioned_text_fields = {
            name
            for name in (
                "NacCaseId",
                "Aktenzeichen",
                "NacWorkflowVersion",
                "KgVersion",
            )
            if akten[name]["type"] == "text"
        } | {
            name
            for name in (
                "NacTaskId",
                "NacCaseId",
                "BpmnStepCode",
                "BlockedReason",
            )
            if aufgaben[name]["type"] == "text"
        }
        self.assertEqual(
            _TEXT_FIELDS,
            provisioned_text_fields | {"VorgangstypId"},
        )
        self.assertEqual(_DATETIME_FIELDS, {"DueDate"})
        self.assertEqual(aufgaben["DueDate"]["type"], "dateTime")
        self.assertEqual(_BOOLEAN_FIELDS, {"RequiresNotaryApproval"})
        self.assertEqual(
            aufgaben["RequiresNotaryApproval"]["type"], "boolean"
        )

    def test_case_choices_match_provisioned_akten_schema(self) -> None:
        columns = _columns("Akten")
        choice_fields = (
            "Vorgangstyp",
            "Status",
            "NotarTeam",
            "Vertraulichkeitsstufe",
        )
        fields = _valid_case_fields()

        for field in choice_fields:
            for choice in columns[field]["choices"]:
                candidate = dict(fields)
                candidate[field] = choice
                if field == "Vorgangstyp":
                    candidate["VorgangstypId"] = choice
                BusinessCaseTypeMutation.case_create(candidate)

            invalid = dict(fields)
            invalid[field] = "not-provisioned"
            if field == "Vorgangstyp":
                invalid["VorgangstypId"] = "not-provisioned"
            with self.assertRaises(MutationValidationError):
                BusinessCaseTypeMutation.case_create(invalid)

            boolean = dict(fields)
            boolean[field] = True
            with self.assertRaises(MutationValidationError):
                BusinessCaseTypeMutation.case_create(boolean)

    def test_status_choices_are_scoped_to_the_target_list(self) -> None:
        case_choices = _columns("Akten")["Status"]["choices"]
        task_choices = _columns("AufgabenFristen")["Status"]["choices"]

        for choice in case_choices:
            BusinessCaseTypeMutation.case_status_update(
                item_id="17",
                expected_etag="synthetic-etag",
                fields={"Status": choice},
            )
            with self.assertRaises(MutationValidationError):
                BusinessCaseTypeMutation.task_update(
                    item_id="17",
                    expected_etag="synthetic-etag",
                    fields={"Status": choice},
                )

        for choice in task_choices:
            BusinessCaseTypeMutation.task_update(
                item_id="17",
                expected_etag="synthetic-etag",
                fields={"Status": choice},
            )
            with self.assertRaises(MutationValidationError):
                BusinessCaseTypeMutation.case_status_update(
                    item_id="17",
                    expected_etag="synthetic-etag",
                    fields={"Status": choice},
                )

    def test_datetime_requires_valid_iso_8601_value_with_timezone(self) -> None:
        valid_values = (
            "2026-08-31T16:00Z",
            "2026-08-31T16:00:00Z",
            "2026-08-31T16:00:00.123456+02:00",
        )
        invalid_values = (
            True,
            1,
            "2026-08-31",
            "2026-08-31T16:00:00",
            "2026-02-30T16:00:00Z",
            "not-a-date",
        )

        for value in valid_values:
            BusinessCaseTypeMutation.task_update(
                item_id="23",
                expected_etag="synthetic-etag",
                fields={"DueDate": value},
            )
        for value in invalid_values:
            with self.assertRaises(MutationValidationError):
                BusinessCaseTypeMutation.task_update(
                    item_id="23",
                    expected_etag="synthetic-etag",
                    fields={"DueDate": value},
                )

    def test_boolean_and_text_fields_reject_substitute_types(self) -> None:
        for value in (1, 0, "true", "false"):
            with self.assertRaises(MutationValidationError):
                BusinessCaseTypeMutation.task_update(
                    item_id="23",
                    expected_etag="synthetic-etag",
                    fields={"RequiresNotaryApproval": value},
                )

        for field in (
            "NacCaseId",
            "Aktenzeichen",
            "NacWorkflowVersion",
            "KgVersion",
        ):
            fields = _valid_case_fields()
            fields[field] = True
            with self.assertRaises(MutationValidationError):
                BusinessCaseTypeMutation.case_create(fields)

    def test_dry_run_mutations_use_deployable_synthetic_values(self) -> None:
        for operation in WRITE_DRY_RUN_OPERATIONS:
            mutation = _synthetic_mutation(operation)
            list_name = (
                "AufgabenFristen"
                if operation in {"task_create", "task_update"}
                else "Akten"
            )
            columns = _columns(list_name)
            for field, value in mutation.fields.items():
                if field == "VorgangstypId":
                    self.assertEqual(
                        value, mutation.fields.get("Vorgangstyp", value)
                    )
                    continue
                column = columns[field]
                if column["type"] == "choice":
                    self.assertIn(value, column["choices"])
                elif column["type"] == "boolean":
                    self.assertIs(type(value), bool)
                else:
                    self.assertIs(type(value), str)

    def test_contract_gate_covers_complete_cli_safety_shape(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertTrue(_contract_is_valid(contract))

        drifts = (
            ("operations_exact", list(reversed(WRITE_DRY_RUN_OPERATIONS))),
            ("operations_exact", None),
            ("operations_exact", 1),
            ("resource_identifiers_or_urls_in_output_allowed", True),
            ("field_values_in_output_allowed", True),
        )
        for key, value in drifts:
            drifted = copy.deepcopy(contract)
            drifted["offline_cli"][key] = value
            with self.subTest(key=key):
                self.assertFalse(_contract_is_valid(drifted))


if __name__ == "__main__":
    unittest.main()
