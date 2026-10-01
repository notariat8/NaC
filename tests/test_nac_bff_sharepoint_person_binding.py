from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_bff.composition import CompositionError, build_configured_app  # noqa: E402
from nac_bff.live_access_decision import LiveAccessDecisionAdapter  # noqa: E402
from nac_bff.live_synthetic_workspace import SYNTHETIC_LIVE_ACTOR_ID  # noqa: E402
from nac_bff.sharepoint_person_binding import (  # noqa: E402
    MAX_BINDINGS_JSON_BYTES,
    MAX_PERSON_BINDINGS,
    PERSON_BINDINGS_SCHEMA,
    SharePointPersonBindings,
    parse_person_bindings,
)
from nac_bff.synthetic_workspace_graph import GRAPH_BASE_URL, SYNTHETIC_SITE_ID  # noqa: E402
from nac_bff.test_environment import (  # noqa: E402
    ALLOWED_MATTER_ID, ALLOWED_PURPOSE, ALLOWED_WORKSPACE_ID, AccessMode,
)

TENANT = "00000000-0000-0000-0000-000000000001"
SUBJECT = "00000000-0000-0000-0000-00000000000a"
OTHER = "00000000-0000-0000-0000-00000000000b"


def _payload() -> dict:
    return {
        "schema_version": PERSON_BINDINGS_SCHEMA,
        "tenant_id": TENANT,
        "site_id": SYNTHETIC_SITE_ID,
        "subjects": [{"subject_id": SUBJECT, "lookup_id": "9"}],
    }


def _parse(payload: dict) -> SharePointPersonBindings:
    return parse_person_bindings(json.dumps(payload), expected_tenant_id=TENANT)


class _Graph:
    base_url = GRAPH_BASE_URL
    redirects_allowed = False
    retains_error_body = False

    def __init__(self, **fields) -> None:
        self.paths: list[str] = []
        self.fields = fields

    def get(self, path: str) -> dict:
        self.paths.append(path)
        return {"value": [{"id": "synthetic-case", "fields": {
            "NacCaseId": ALLOWED_MATTER_ID, "NotarTeam": "NaC-Notar-01",
            **self.fields,
        }}]}


def _decide(adapter: LiveAccessDecisionAdapter, actor: str = SUBJECT):
    return adapter.decide(
        actor_id=actor, tenant_id=TENANT, workspace_id=ALLOWED_WORKSPACE_ID,
        matter_id=ALLOWED_MATTER_ID, purpose=ALLOWED_PURPOSE,
    )


class SharePointPersonBindingTests(unittest.TestCase):
    def test_native_person_mapping_retains_entra_subject_not_lookup_id(self) -> None:
        graph = _Graph(FederfuehrenderNotarLookupId="9")
        adapter = LiveAccessDecisionAdapter(
            graph, expected_tenant_id=TENANT, person_bindings=_parse(_payload()),
            reference_time="2026-07-14T12:00:00Z",
        )
        decision = _decide(adapter, SUBJECT.upper())
        self.assertIs(decision.mode, AccessMode.ASSIGNED)
        self.assertEqual(decision.subject_id, SUBJECT.upper())
        self.assertEqual(len(graph.paths), 1)
        self.assertIn("FederfuehrenderNotarLookupId", graph.paths[0])

    def test_unbound_invalid_and_former_fixed_actor_deny_before_graph(self) -> None:
        for actor in (OTHER, "9", "actor-notary", "alias@example.com", SUBJECT + " ", SYNTHETIC_LIVE_ACTOR_ID):
            with self.subTest(actor=actor):
                graph = _Graph(FederfuehrenderNotarLookupId="9")
                adapter = LiveAccessDecisionAdapter(
                    graph, expected_tenant_id=TENANT, person_bindings=_parse(_payload()),
                )
                self.assertIs(_decide(adapter, actor).mode, AccessMode.DENY)
                self.assertEqual(graph.paths, [])
        graph = _Graph(FederfuehrenderNotarLookupId="9")
        adapter = LiveAccessDecisionAdapter(graph, expected_tenant_id=TENANT)
        self.assertIs(_decide(adapter, SYNTHETIC_LIVE_ACTOR_ID).mode, AccessMode.DENY)
        self.assertEqual(graph.paths, [])

    def test_legacy_names_and_entra_ids_in_person_fields_do_not_grant_access(self) -> None:
        for fields in (
            {"FederfuehrenderNotar": SUBJECT},
            {"FederfuehrenderNotarLookupId": SUBJECT},
            {"FederfuehrenderNotarLookupId": "alias@example.com"},
        ):
            with self.subTest(fields=fields):
                graph = _Graph(**fields)
                adapter = LiveAccessDecisionAdapter(
                    graph, expected_tenant_id=TENANT, person_bindings=_parse(_payload()),
                    reference_time="2026-07-14T12:00:00Z",
                )
                self.assertIs(_decide(adapter).mode, AccessMode.DENY)

    def test_scope_binding_and_immutable_snapshot(self) -> None:
        original = {SUBJECT: "9"}
        bindings = SharePointPersonBindings(TENANT, SYNTHETIC_SITE_ID, original)
        original[SUBJECT] = "10"
        self.assertEqual(bindings.resolve(tenant_id=TENANT, site_id=SYNTHETIC_SITE_ID, subject_id=SUBJECT), "9")
        self.assertIsNone(bindings.resolve(tenant_id=OTHER, site_id=SYNTHETIC_SITE_ID, subject_id=SUBJECT))
        self.assertIsNone(bindings.resolve(tenant_id=TENANT, site_id="other-site", subject_id=SUBJECT))
        with self.assertRaises(TypeError):
            bindings.subjects[SUBJECT] = "10"
        with self.assertRaises(FrozenInstanceError):
            bindings.tenant_id = OTHER
        self.assertNotIn(SUBJECT, repr(bindings))
        with self.assertRaisesRegex(ValueError, "^SharePoint person bindings are invalid$"):
            LiveAccessDecisionAdapter(_Graph(), expected_tenant_id=OTHER, person_bindings=bindings)

    def test_invalid_schema_and_identity_values_are_rejected_without_private_output(self) -> None:
        invalid = []
        for field, value in (
            ("schema_version", "unknown"), ("tenant_id", OTHER),
            ("site_id", "other-site"), ("subjects", []), ("subjects", {}),
        ):
            payload = _payload()
            payload[field] = value
            invalid.append(payload)
        invalid.append({**_payload(), "email": "private@example.com"})
        for value in (None, True, 9, "0", "-1", "+9", "09", "9 ", "2147483648", "9.0"):
            payload = _payload()
            payload["subjects"][0]["lookup_id"] = value
            invalid.append(payload)
        for value in (None, True, "private@example.com", "0" * 32, "00000000-0000-0000-0000-000000000000", SUBJECT + " "):
            payload = _payload()
            payload["subjects"][0]["subject_id"] = value
            invalid.append(payload)
        payload = _payload()
        payload["subjects"][0]["role"] = "notary"
        invalid.append(payload)
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaisesRegex(ValueError, "^SharePoint person bindings are invalid$"):
                _parse(payload)

    def test_duplicate_subject_person_and_json_keys_are_rejected(self) -> None:
        for entry in (
            {"subject_id": SUBJECT.upper(), "lookup_id": "10"},
            {"subject_id": OTHER, "lookup_id": "9"},
        ):
            payload = _payload()
            payload["subjects"].append(entry)
            with self.assertRaises(ValueError):
                _parse(payload)
        raw = json.dumps(_payload())
        for bad in (
            raw.replace('"tenant_id":', '"tenant_id": "private", "tenant_id":'),
            raw.replace('"lookup_id":', '"lookup_id": "private", "lookup_id":'),
        ):
            with self.assertRaisesRegex(ValueError, "^SharePoint person bindings are invalid$"):
                parse_person_bindings(bad, expected_tenant_id=TENANT)

    def test_bound_size_and_malformed_inputs_are_rejected(self) -> None:
        payload = _payload()
        payload["subjects"] = [{"subject_id": f"00000000-0000-0000-0000-{i:012x}", "lookup_id": str(i)} for i in range(1, MAX_PERSON_BINDINGS + 1)]
        self.assertEqual(len(_parse(payload).subjects), MAX_PERSON_BINDINGS)
        payload["subjects"].append({"subject_id": OTHER, "lookup_id": "999"})
        with self.assertRaises(ValueError):
            _parse(payload)
        for raw in (None, {}, "", "{", "null", " " * (MAX_BINDINGS_JSON_BYTES + 1)):
            with self.assertRaisesRegex(ValueError, "^SharePoint person bindings are invalid$"):
                parse_person_bindings(raw, expected_tenant_id=TENANT)

    def test_missing_invalid_config_stops_before_all_composition_factories(self) -> None:
        env = {
            "M365_TENANT_ID": TENANT, "NAC_BFF_TENANT_ID": TENANT,
            "NAC_BFF_AUDIENCE": "synthetic-audience", "NAC_BFF_REQUIRED_SCOPE": "Matter.Read",
        }
        calls = []

        def unexpected(*args, **kwargs):
            calls.append("factory")
            raise AssertionError("factory must not execute")

        for raw in (None, "private-invalid", json.dumps({**_payload(), "tenant_id": OTHER})):
            values = dict(env)
            if raw is not None:
                values["NAC_BFF_PERSON_BINDINGS_JSON"] = raw
            with self.assertRaisesRegex(CompositionError, "^SharePoint person bindings are invalid$"):
                build_configured_app(
                    values, validator_factory=unexpected, token_provider_factory=unexpected,
                    graph_client_factory=unexpected, access_port_factory=unexpected,
                    workspace_port_factory=unexpected,
                )
        self.assertEqual(calls, [])

    def test_composition_injects_binding_into_existing_access_port(self) -> None:
        env = {
            "M365_TENANT_ID": TENANT, "NAC_BFF_TENANT_ID": TENANT,
            "NAC_BFF_AUDIENCE": "synthetic-audience", "NAC_BFF_REQUIRED_SCOPE": "Matter.Read",
            "NAC_BFF_PERSON_BINDINGS_JSON": json.dumps(_payload()),
        }
        captured = []
        graph = _Graph(FederfuehrenderNotarLookupId="9")

        def access_factory(client, **kwargs):
            captured.append(LiveAccessDecisionAdapter(client, reference_time="2026-07-14T12:00:00Z", **kwargs))
            return captured[-1]

        with (
            patch("nac_bff.composition.create_fastapi_app", return_value=object()),
            patch("nac_bff.composition._claims_dependency", return_value=lambda: None),
        ):
            build_configured_app(
                env, validator_factory=lambda **_: lambda _: None,
                token_provider_factory=lambda _: object(), graph_client_factory=lambda _: graph,
                access_port_factory=access_factory,
            )
        self.assertEqual(len(captured), 1)
        self.assertIs(_decide(captured[0]).mode, AccessMode.ASSIGNED)


if __name__ == "__main__":
    unittest.main()
