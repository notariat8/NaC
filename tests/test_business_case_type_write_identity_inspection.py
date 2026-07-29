from __future__ import annotations

from dataclasses import FrozenInstanceError, asdict, replace
import json
from pathlib import Path
import sys
import unittest
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_m365_graph.business_case_type_write_identity_inspection import (  # noqa: E402
    BusinessCaseTypeWriteIdentityInspectionAdapter,
    BusinessCaseTypeWriteIdentitySnapshot,
    EntraPrincipalReference,
    EntraPrincipalSnapshot,
    IdentityInspectionError,
    SiteRoleAssignmentSnapshot,
    SnapshotIdentityInspectionPort,
    entra_principal_binding_sha256,
    validate_business_case_type_write_identity_snapshot,
)


PROVISIONER_APP_ID = "10000000-0000-0000-0000-000000000001"
PROVISIONER_OBJECT_ID = "20000000-0000-0000-0000-000000000001"
WRITER_APP_ID = "30000000-0000-0000-0000-000000000001"
WRITER_OBJECT_ID = "40000000-0000-0000-0000-000000000001"
BFF_APP_ID = "50000000-0000-0000-0000-000000000001"
BFF_OBJECT_ID = "60000000-0000-0000-0000-000000000001"
SITE_BINDING_SHA256 = "7" * 64


def _principal(
    app_id: str,
    object_id: str,
    graph_roles: tuple[str, ...],
) -> EntraPrincipalSnapshot:
    return EntraPrincipalSnapshot(
        app_id=app_id,
        service_principal_object_id=object_id,
        graph_application_roles=graph_roles,
    )


def _reference(app_id: str, object_id: str) -> EntraPrincipalReference:
    return EntraPrincipalReference(
        app_id=app_id,
        service_principal_object_id=object_id,
    )


def _snapshot(
    **overrides: Any,
) -> BusinessCaseTypeWriteIdentitySnapshot:
    values: dict[str, Any] = {
        "site_binding_sha256": SITE_BINDING_SHA256,
        "provisioner": _principal(
            PROVISIONER_APP_ID,
            PROVISIONER_OBJECT_ID,
            ("Sites.Manage.All",),
        ),
        "writer": _principal(
            WRITER_APP_ID,
            WRITER_OBJECT_ID,
            ("Sites.Selected",),
        ),
        "bff": _principal(
            BFF_APP_ID,
            BFF_OBJECT_ID,
            ("Sites.Selected",),
        ),
        "writer_site_assignment": SiteRoleAssignmentSnapshot(
            service_principal_object_id=WRITER_OBJECT_ID,
            roles=("write",),
        ),
        "bff_site_assignment": SiteRoleAssignmentSnapshot(
            service_principal_object_id=BFF_OBJECT_ID,
            roles=("read",),
        ),
        "business_writer": _reference(WRITER_APP_ID, WRITER_OBJECT_ID),
        "write_token_source": _reference(
            WRITER_APP_ID, WRITER_OBJECT_ID
        ),
    }
    values.update(overrides)
    return BusinessCaseTypeWriteIdentitySnapshot(**values)


class _TrackingPort:
    def __init__(
        self,
        snapshot: object | None = None,
        error: BaseException | None = None,
    ) -> None:
        self.snapshot = _snapshot() if snapshot is None else snapshot
        self.error = error
        self.calls = 0

    def readback(self) -> object:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.snapshot


class IdentityInspectionPositiveTests(unittest.TestCase):
    def test_validator_returns_deterministic_redacted_bindings(self) -> None:
        snapshot = _snapshot()

        first = validate_business_case_type_write_identity_snapshot(snapshot)
        second = validate_business_case_type_write_identity_snapshot(snapshot)

        self.assertEqual(first, second)
        self.assertEqual(first.schema_version, "nac.s4g-identity-inspection/v0.1")
        self.assertEqual(first.site_binding_sha256, SITE_BINDING_SHA256)
        self.assertEqual(
            first.provisioner_principal_binding_sha256,
            entra_principal_binding_sha256(snapshot.provisioner),
        )
        self.assertEqual(
            first.writer_principal_binding_sha256,
            entra_principal_binding_sha256(snapshot.writer),
        )
        self.assertEqual(
            first.bff_principal_binding_sha256,
            entra_principal_binding_sha256(snapshot.bff),
        )
        self.assertEqual(first.writer_graph_application_roles, ("Sites.Selected",))
        self.assertEqual(first.writer_site_roles, ("write",))
        self.assertEqual(first.bff_graph_application_roles, ("Sites.Selected",))
        self.assertEqual(first.bff_site_roles, ("read",))
        self.assertTrue(first.principals_pairwise_distinct)
        self.assertTrue(first.business_writer_is_writer)
        self.assertTrue(first.write_token_source_is_writer)

        serialized = json.dumps(asdict(first), sort_keys=True)
        for raw_identifier in (
            PROVISIONER_APP_ID,
            PROVISIONER_OBJECT_ID,
            WRITER_APP_ID,
            WRITER_OBJECT_ID,
            BFF_APP_ID,
            BFF_OBJECT_ID,
        ):
            self.assertNotIn(raw_identifier, serialized)

    def test_adapter_reads_injected_port_once(self) -> None:
        port = _TrackingPort()
        adapter = BusinessCaseTypeWriteIdentityInspectionAdapter(port)

        result = adapter.inspect()

        self.assertEqual(port.calls, 1)
        self.assertEqual(
            result.writer_principal_binding_sha256,
            entra_principal_binding_sha256(_snapshot().writer),
        )

    def test_readback_alias_uses_the_same_read_only_path(self) -> None:
        port = _TrackingPort()
        adapter = BusinessCaseTypeWriteIdentityInspectionAdapter(port)

        self.assertEqual(adapter.readback(), adapter.inspect())
        self.assertEqual(port.calls, 2)

    def test_static_snapshot_port_is_offline_and_deterministic(self) -> None:
        snapshot = _snapshot()
        port = SnapshotIdentityInspectionPort(snapshot)

        self.assertIs(port.readback(), snapshot)
        self.assertIs(port.readback(), snapshot)

    def test_validated_result_is_immutable(self) -> None:
        result = validate_business_case_type_write_identity_snapshot(
            _snapshot()
        )

        with self.assertRaises(FrozenInstanceError):
            result.site_binding_sha256 = "8" * 64  # type: ignore[misc]

    def test_provisioner_permissions_are_not_used_as_writer_permissions(
        self,
    ) -> None:
        snapshot = _snapshot(
            provisioner=_principal(
                PROVISIONER_APP_ID,
                PROVISIONER_OBJECT_ID,
                ("Sites.FullControl.All", "Sites.Manage.All"),
            )
        )

        result = validate_business_case_type_write_identity_snapshot(snapshot)

        self.assertEqual(result.writer_site_roles, ("write",))
        self.assertNotEqual(
            result.provisioner_principal_binding_sha256,
            result.writer_principal_binding_sha256,
        )


    def test_duplicate_provisioner_roles_are_rejected(self) -> None:
        base = _snapshot()
        snapshot = replace(
            base,
            provisioner=replace(
                base.provisioner,
                graph_application_roles=(
                    "Sites.Manage.All",
                    "Sites.Manage.All",
                ),
            ),
        )

        with self.assertRaises(IdentityInspectionError) as ctx:
            validate_business_case_type_write_identity_snapshot(snapshot)

        self.assertEqual(ctx.exception.code, "graph_application_roles_invalid")



class IdentityInspectionSeparationTests(unittest.TestCase):
    def test_all_app_ids_must_be_pairwise_distinct(self) -> None:
        base = _snapshot()
        cases = {
            "provisioner_writer": replace(
                base,
                writer=replace(base.writer, app_id=PROVISIONER_APP_ID),
                business_writer=replace(
                    base.business_writer, app_id=PROVISIONER_APP_ID
                ),
                write_token_source=replace(
                    base.write_token_source, app_id=PROVISIONER_APP_ID
                ),
            ),
            "provisioner_bff": replace(
                base,
                bff=replace(base.bff, app_id=PROVISIONER_APP_ID),
            ),
            "writer_bff": replace(
                base,
                bff=replace(base.bff, app_id=WRITER_APP_ID),
            ),
        }
        for name, snapshot in cases.items():
            with self.subTest(name=name):
                self._assert_code(
                    "entra_app_ids_not_pairwise_distinct", snapshot
                )

    def test_all_service_principal_ids_must_be_pairwise_distinct(
        self,
    ) -> None:
        base = _snapshot()
        cases = {
            "provisioner_writer": replace(
                base,
                writer=replace(
                    base.writer,
                    service_principal_object_id=PROVISIONER_OBJECT_ID,
                ),
                writer_site_assignment=replace(
                    base.writer_site_assignment,
                    service_principal_object_id=PROVISIONER_OBJECT_ID,
                ),
                business_writer=replace(
                    base.business_writer,
                    service_principal_object_id=PROVISIONER_OBJECT_ID,
                ),
                write_token_source=replace(
                    base.write_token_source,
                    service_principal_object_id=PROVISIONER_OBJECT_ID,
                ),
            ),
            "provisioner_bff": replace(
                base,
                bff=replace(
                    base.bff,
                    service_principal_object_id=PROVISIONER_OBJECT_ID,
                ),
                bff_site_assignment=replace(
                    base.bff_site_assignment,
                    service_principal_object_id=PROVISIONER_OBJECT_ID,
                ),
            ),
            "writer_bff": replace(
                base,
                bff=replace(
                    base.bff,
                    service_principal_object_id=WRITER_OBJECT_ID,
                ),
                bff_site_assignment=replace(
                    base.bff_site_assignment,
                    service_principal_object_id=WRITER_OBJECT_ID,
                ),
            ),
        }
        for name, snapshot in cases.items():
            with self.subTest(name=name):
                self._assert_code(
                    "service_principal_ids_not_pairwise_distinct", snapshot
                )

    def test_app_and_object_id_for_one_principal_must_differ(self) -> None:
        base = _snapshot()
        snapshot = replace(
            base,
            provisioner=replace(
                base.provisioner,
                service_principal_object_id=PROVISIONER_APP_ID,
            ),
        )

        self._assert_code("entra_identifier_namespace_collision", snapshot)

    def test_app_and_object_id_namespaces_are_globally_disjoint(self) -> None:
        base = _snapshot()
        snapshot = replace(
            base,
            writer=replace(
                base.writer,
                service_principal_object_id=BFF_APP_ID,
            ),
            writer_site_assignment=replace(
                base.writer_site_assignment,
                service_principal_object_id=BFF_APP_ID,
            ),
        )

        self._assert_code(
            "entra_identifier_namespace_collision", snapshot
        )

    def test_provisioner_cannot_be_the_business_writer(self) -> None:
        base = _snapshot()
        snapshot = replace(
            base,
            business_writer=_reference(
                PROVISIONER_APP_ID, PROVISIONER_OBJECT_ID
            ),
        )

        self._assert_code("business_writer_not_bound_to_writer", snapshot)

    def test_provisioner_cannot_be_the_write_token_source(self) -> None:
        base = _snapshot()
        snapshot = replace(
            base,
            write_token_source=_reference(
                PROVISIONER_APP_ID, PROVISIONER_OBJECT_ID
            ),
        )

        self._assert_code("write_token_source_not_bound_to_writer", snapshot)

    def test_bff_cannot_be_business_writer_or_token_source(self) -> None:
        base = _snapshot()
        for field in ("business_writer", "write_token_source"):
            with self.subTest(field=field):
                snapshot = replace(
                    base,
                    **{
                        field: _reference(BFF_APP_ID, BFF_OBJECT_ID),
                    },
                )
                expected = (
                    "business_writer_not_bound_to_writer"
                    if field == "business_writer"
                    else "write_token_source_not_bound_to_writer"
                )
                self._assert_code(expected, snapshot)

    def _assert_code(
        self,
        code: str,
        snapshot: BusinessCaseTypeWriteIdentitySnapshot,
    ) -> None:
        with self.assertRaisesRegex(IdentityInspectionError, f"^{code}$") as ctx:
            validate_business_case_type_write_identity_snapshot(snapshot)
        self.assertEqual(ctx.exception.code, code)


class IdentityInspectionPermissionTests(unittest.TestCase):
    def test_writer_graph_roles_must_be_exact(self) -> None:
        base = _snapshot()
        for roles in (
            (),
            ("Sites.Selected", "Sites.Read.All"),
            ("Sites.Selected", "Sites.Selected"),
            ("sites.selected",),
        ):
            with self.subTest(roles=roles):
                self._assert_drift(
                    "writer_graph_roles_not_exact",
                    replace(
                        base,
                        writer=replace(
                            base.writer, graph_application_roles=roles
                        ),
                    ),
                )

    def test_writer_site_role_must_be_exact(self) -> None:
        base = _snapshot()
        for roles in ((), ("read",), ("write", "read"), ("Write",)):
            with self.subTest(roles=roles):
                self._assert_drift(
                    "writer_site_role_not_exact",
                    replace(
                        base,
                        writer_site_assignment=replace(
                            base.writer_site_assignment, roles=roles
                        ),
                    ),
                )

    def test_bff_graph_roles_must_be_exact(self) -> None:
        base = _snapshot()
        for roles in (
            (),
            ("Sites.Selected", "Sites.Read.All"),
            ("Sites.Selected", "Sites.Selected"),
            ("sites.selected",),
        ):
            with self.subTest(roles=roles):
                self._assert_drift(
                    "bff_graph_roles_not_exact",
                    replace(base, bff=replace(base.bff, graph_application_roles=roles)),
                )

    def test_bff_site_role_must_be_exact(self) -> None:
        base = _snapshot()
        for roles in ((), ("write",), ("read", "write"), ("Read",)):
            with self.subTest(roles=roles):
                self._assert_drift(
                    "bff_site_role_not_exact",
                    replace(
                        base,
                        bff_site_assignment=replace(
                            base.bff_site_assignment, roles=roles
                        ),
                    ),
                )

    def test_site_assignments_must_target_the_matching_principal(self) -> None:
        base = _snapshot()
        cases = (
            (
                "writer_site_assignment_principal_mismatch",
                replace(
                    base,
                    writer_site_assignment=replace(
                        base.writer_site_assignment,
                        service_principal_object_id=BFF_OBJECT_ID,
                    ),
                ),
            ),
            (
                "bff_site_assignment_principal_mismatch",
                replace(
                    base,
                    bff_site_assignment=replace(
                        base.bff_site_assignment,
                        service_principal_object_id=WRITER_OBJECT_ID,
                    ),
                ),
            ),
        )
        for code, snapshot in cases:
            with self.subTest(code=code):
                self._assert_drift(code, snapshot)

    def _assert_drift(
        self,
        code: str,
        snapshot: BusinessCaseTypeWriteIdentitySnapshot,
    ) -> None:
        with self.assertRaises(IdentityInspectionError) as ctx:
            validate_business_case_type_write_identity_snapshot(snapshot)
        self.assertEqual(ctx.exception.code, code)


class IdentityInspectionInputAndRedactionTests(unittest.TestCase):
    def test_snapshot_and_nested_types_are_strict(self) -> None:
        base = _snapshot()
        cases = (
            ("identity_snapshot_type_invalid", object()),
            (
                "entra_principal_snapshot_type_invalid",
                replace(base, writer=object()),  # type: ignore[arg-type]
            ),
            (
                "site_role_assignment_snapshot_type_invalid",
                replace(
                    base,
                    writer_site_assignment=object(),  # type: ignore[arg-type]
                ),
            ),
            (
                "entra_principal_reference_type_invalid",
                replace(
                    base,
                    business_writer=object(),  # type: ignore[arg-type]
                ),
            ),
        )
        for code, snapshot in cases:
            with self.subTest(code=code):
                with self.assertRaises(IdentityInspectionError) as ctx:
                    validate_business_case_type_write_identity_snapshot(
                        snapshot  # type: ignore[arg-type]
                    )
                self.assertEqual(ctx.exception.code, code)

    def test_identifiers_must_be_canonical_uuid_strings(self) -> None:
        base = _snapshot()
        invalid_values: tuple[object, ...] = (
            "",
            "not-a-guid",
            "00000000-0000-0000-0000-000000000000",
            "AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA",
            f" {WRITER_APP_ID}",
            123,
        )
        for value in invalid_values:
            with self.subTest(value=value):
                snapshot = replace(
                    base,
                    writer=replace(base.writer, app_id=value),  # type: ignore[arg-type]
                )
                with self.assertRaises(IdentityInspectionError) as ctx:
                    validate_business_case_type_write_identity_snapshot(snapshot)
                self.assertEqual(ctx.exception.code, "entra_identifier_invalid")

    def test_site_binding_and_role_container_types_are_strict(self) -> None:
        base = _snapshot()
        cases = (
            (
                "site_binding_invalid",
                replace(base, site_binding_sha256="not-a-hash"),
            ),
            (
                "graph_application_roles_invalid",
                replace(
                    base,
                    provisioner=replace(
                        base.provisioner,
                        graph_application_roles=[  # type: ignore[arg-type]
                            "Sites.Manage.All"
                        ],
                    ),
                ),
            ),
            (
                "site_roles_invalid",
                replace(
                    base,
                    writer_site_assignment=replace(
                        base.writer_site_assignment,
                        roles=["write"],  # type: ignore[arg-type]
                    ),
                ),
            ),
        )
        for code, snapshot in cases:
            with self.subTest(code=code):
                with self.assertRaises(IdentityInspectionError) as ctx:
                    validate_business_case_type_write_identity_snapshot(snapshot)
                self.assertEqual(ctx.exception.code, code)

    def test_port_failure_is_stable_and_redacted(self) -> None:
        secret = "tenant-id=raw-tenant token=raw-bearer"
        port = _TrackingPort(error=RuntimeError(secret))
        adapter = BusinessCaseTypeWriteIdentityInspectionAdapter(port)

        with self.assertRaises(IdentityInspectionError) as ctx:
            adapter.inspect()

        self.assertEqual(ctx.exception.code, "identity_snapshot_unavailable")
        self.assertEqual(str(ctx.exception), "identity_snapshot_unavailable")
        self.assertNotIn(secret, repr(ctx.exception))
        self.assertIsNone(ctx.exception.__cause__)
        self.assertEqual(port.calls, 1)

    def test_invalid_port_snapshot_does_not_leak_raw_identifiers(self) -> None:
        raw = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        base = _snapshot()
        invalid = replace(
            base,
            business_writer=_reference(raw, PROVISIONER_OBJECT_ID),
        )
        adapter = BusinessCaseTypeWriteIdentityInspectionAdapter(
            _TrackingPort(invalid)
        )

        with self.assertRaises(IdentityInspectionError) as ctx:
            adapter.inspect()

        self.assertEqual(
            ctx.exception.code, "business_writer_not_bound_to_writer"
        )
        self.assertNotIn(raw, str(ctx.exception))

    def test_missing_readback_method_is_reported_as_unavailable(self) -> None:
        adapter = BusinessCaseTypeWriteIdentityInspectionAdapter(object())

        with self.assertRaises(IdentityInspectionError) as ctx:
            adapter.inspect()

        self.assertEqual(ctx.exception.code, "identity_snapshot_unavailable")


if __name__ == "__main__":
    unittest.main()
