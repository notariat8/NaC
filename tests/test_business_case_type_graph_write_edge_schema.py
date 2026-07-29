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
    _TEXT_MAX_LENGTH_BY_LIST,
    _validate_sharepoint_fields,
)


MVP_SCHEMA_PATH = (
    ROOT / "deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json"
)
FOUNDATION_SCHEMA_PATH = (
    ROOT
    / "deploy/m365/teams-sharepoint/"
    "nac-business-case-type-foundation.notary-team-01.json"
)
CONTRACT_PATH = (
    ROOT
    / "workflows/contracts/business-case-type-graph-write-edge-s4b.contract.json"
)


def _lists_by_name() -> dict[str, dict[str, Any]]:
    payload = json.loads(MVP_SCHEMA_PATH.read_text(encoding="utf-8"))
    return {
        item["display_name"]: item
        for item in payload["sharepoint"]["lists"]
    }


def _columns(list_name: str) -> dict[str, dict[str, Any]]:
    columns = {
        column["name"]: dict(column)
        for column in _lists_by_name()[list_name]["columns"]
    }
    for column in columns.values():
        if column["type"] == "text":
            column["maxLength"] = column.get("text", {}).get(
                "maxLength", 255
            )
    if list_name == "Akten":
        foundation = json.loads(
            FOUNDATION_SCHEMA_PATH.read_text(encoding="utf-8")
        )
        legacy = foundation["schema"]["legacy_akten_column"]
        additive = foundation["schema"]["akten_additive_column"]
        additive_facets = {
            name
            for name in ("text", "choice", "boolean")
            if name in additive
        }
        if (
            legacy.get("name") != "Vorgangstyp"
            or legacy.get("type") != "choice"
            or legacy.get("choices") != columns["Vorgangstyp"]["choices"]
            or additive_facets != {"text"}
        ):
            raise AssertionError("foundation Akten schema does not match MVP")

        columns[additive["name"]] = {
            "name": additive["name"],
            "type": "text",
            "maxLength": additive["text"]["maxLength"],
        }
    return columns


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
        provisioned_text_max_lengths = {
            "Akten": {
                name: column["maxLength"]
                for name, column in akten.items()
                if column["type"] == "text"
            },
            "AufgabenFristen": {
                name: column["maxLength"]
                for name, column in aufgaben.items()
                if column["type"] == "text"
            },
        }
        self.assertEqual(
            _TEXT_MAX_LENGTH_BY_LIST, provisioned_text_max_lengths
        )
        self.assertEqual(
            _TEXT_FIELDS,
            frozenset(
                field
                for fields in provisioned_text_max_lengths.values()
                for field in fields
            ),
        )
        expected_field_schema = {
            "source_paths_exact": [
                "deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json",
                "deploy/m365/teams-sharepoint/"
                "nac-business-case-type-foundation.notary-team-01.json",
            ],
            "text_fields_by_list_exact": provisioned_text_max_lengths,
            "choice_fields_by_list_exact": {
                "Akten": {
                    name: akten[name]["choices"]
                    for name in (
                        "Vorgangstyp",
                        "Status",
                        "NotarTeam",
                        "Vertraulichkeitsstufe",
                    )
                },
                "AufgabenFristen": {
                    "Status": aufgaben["Status"]["choices"]
                },
            },
            "date_time_fields_by_list_exact": {
                "AufgabenFristen": ["DueDate"]
            },
            "boolean_fields_by_list_exact": {
                "AufgabenFristen": ["RequiresNotaryApproval"]
            },
            "boolean_as_text_or_integer_allowed": False,
            "date_time_format_exact": "ISO-8601 timezone-aware",
        }
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            contract["field_schema"], expected_field_schema
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

    def test_text_fields_enforce_provisioned_max_length_boundaries(self) -> None:
        for list_name, fields in _TEXT_MAX_LENGTH_BY_LIST.items():
            for field, max_length in fields.items():
                with self.subTest(list_name=list_name, field=field):
                    _validate_sharepoint_fields(
                        {field: "x" * max_length}, list_name=list_name
                    )
                    with self.assertRaises(MutationValidationError):
                        _validate_sharepoint_fields(
                            {field: "x" * (max_length + 1)},
                            list_name=list_name,
                        )

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
                column = columns[field]
                if column["type"] == "choice":
                    self.assertIn(value, column["choices"])
                elif column["type"] == "boolean":
                    self.assertIs(type(value), bool)
                elif column["type"] == "text":
                    self.assertIs(type(value), str)
                    self.assertLessEqual(len(value), column["maxLength"])
                else:
                    self.assertIs(type(value), str)

    def test_contract_gate_covers_complete_cli_safety_shape(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertTrue(_contract_is_valid(contract))

        checked_paths = [
            ("schema_version",),
            ("status",),
            ("operations",),
            ("binding", "graph_base_url_exact"),
            ("binding", "graph_beta_sdk_sharepoint_rest_pnp_allowed"),
        ]
        for section in (
            "slice",
            "identity_boundary",
            "offline_boundary",
            "offline_cli",
        ):
            checked_paths.extend((section, key) for key in contract[section])

        def drift(value: Any) -> Any:
            if type(value) is bool:
                return not value
            if type(value) is int:
                return value + 1
            if isinstance(value, str):
                return f"{value}-drift"
            if isinstance(value, list):
                return list(reversed(value))
            if isinstance(value, dict):
                return dict(reversed(tuple(value.items())))
            return None

        for path in checked_paths:
            drifted = copy.deepcopy(contract)
            target = drifted
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = drift(target[path[-1]])
            with self.subTest(path=".".join(path)):
                self.assertFalse(_contract_is_valid(drifted))


if __name__ == "__main__":
    unittest.main()
