from __future__ import annotations

from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from src.nac_bff.current_state_access_client_receipt import (
    ClientObservationReceiptError,
    stage_client_observation_receipt,
    validate_client_observation_receipt_bytes,
)


def _canonical_sha256(value: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _receipt() -> dict[str, object]:
    core: dict[str, object] = {
        "end_utc": "2026-09-21T08:00:01.000Z",
        "request_correlation_binding_sha256": "7" * 64,
        "spfx_subject_available": False,
        "start_utc": "2026-09-21T08:00:00.000Z",
        "ui_state": "no_access",
    }
    return {**core, "window_binding_sha256": _canonical_sha256(core)}


class _Session:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.closed = False

    def create_exclusive(self, name: str, payload: bytes):
        if name in self.files:
            raise FileExistsError(name)
        self.files[name] = payload
        return SimpleNamespace(sha256=hashlib.sha256(payload).hexdigest())

    def close(self) -> None:
        self.closed = True


class _Backend:
    def __init__(self, source: Path, *, read_payload: bytes | None = None) -> None:
        self.source = source
        self.read_payload = read_payload
        self.session = _Session()
        self.open_requests: list[tuple[Path, bool, dict[str, object]]] = []

    def inspect_bound_input_path(self, path: Path, purpose: str):
        self.assert_source(path)
        raw = self.source.read_bytes()
        return SimpleNamespace(size=len(raw), sha256=hashlib.sha256(raw).hexdigest())

    def assert_source(self, path: Path) -> None:
        if Path(path) != self.source:
            raise AssertionError("unexpected source")

    @contextmanager
    def open_bound_input_read(self, path: Path, snapshot):
        self.assert_source(path)
        yield io.BytesIO(
            self.source.read_bytes()
            if self.read_payload is None
            else self.read_payload
        )

    def open_secure_directory(self, path: Path, *, create: bool, **kwargs):
        self.open_requests.append((Path(path), create, dict(kwargs)))
        if create:
            raise AssertionError("input root must already exist")
        return self.session


class ClientObservationReceiptTest(unittest.TestCase):
    def test_accepts_only_the_six_field_privacy_allowlist(self) -> None:
        receipt = _receipt()
        raw = json.dumps(receipt, separators=(",", ":")).encode("utf-8")
        self.assertEqual(validate_client_observation_receipt_bytes(raw), receipt)

        for forbidden in (
            "object_id", "subject_id", "name", "email", "tenant_id", "token",
            "headers", "request_body", "correlation_id",
        ):
            with self.subTest(forbidden=forbidden):
                invalid = {**receipt, forbidden: "secret"}
                with self.assertRaises(ClientObservationReceiptError):
                    validate_client_observation_receipt_bytes(
                        json.dumps(invalid).encode("utf-8")
                    )

    def test_rejects_duplicate_keys_window_drift_and_invalid_boolean(self) -> None:
        receipt = _receipt()
        with self.assertRaises(ClientObservationReceiptError):
            validate_client_observation_receipt_bytes(
                b'{"ui_state":"no_access","ui_state":"no_access"}'
            )
        with self.assertRaises(ClientObservationReceiptError):
            validate_client_observation_receipt_bytes(
                json.dumps({**receipt, "window_binding_sha256": "0" * 64}).encode()
            )
        with self.assertRaises(ClientObservationReceiptError):
            validate_client_observation_receipt_bytes(
                json.dumps({**receipt, "spfx_subject_available": 1}).encode()
            )
        for raw in (b"", b"\xff", b"{" + b"x" * (16 * 1024) + b"}"):
            with self.subTest(raw_length=len(raw)):
                with self.assertRaises(ClientObservationReceiptError):
                    validate_client_observation_receipt_bytes(raw)

    def test_stages_canonical_receipt_exclusively_outside_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "repo"
            repository.mkdir()
            source = root / "nac-issue748-client-observation.json"
            source.write_text(json.dumps(_receipt()), encoding="utf-8")
            input_root = root / "protected-input"
            input_root.mkdir()
            backend = _Backend(source)

            wrong_name = root / "renamed.json"
            wrong_name.write_text(json.dumps(_receipt()), encoding="utf-8")
            with self.assertRaisesRegex(
                ClientObservationReceiptError, "CLIENT_RECEIPT_FILENAME_INVALID"
            ):
                stage_client_observation_receipt(
                    source_path=wrong_name,
                    input_root=input_root,
                    repo_root=repository,
                    backend=_Backend(wrong_name),
                )

            result = stage_client_observation_receipt(
                source_path=source,
                input_root=input_root,
                repo_root=repository,
                backend=backend,
            )

            self.assertEqual(result["status"], "PASSED")
            self.assertEqual(set(backend.session.files), {"client-observation-receipt.json"})
            staged = json.loads(backend.session.files["client-observation-receipt.json"])
            self.assertEqual(staged, _receipt())
            self.assertTrue(backend.session.closed)
            self.assertEqual(
                backend.open_requests,
                [(input_root, False, {
                    "require_current_owner": True,
                    "require_restrictive_dacl": True,
                })],
            )

            with self.assertRaisesRegex(
                ClientObservationReceiptError, "CLIENT_RECEIPT_ALREADY_EXISTS"
            ):
                stage_client_observation_receipt(
                    source_path=source,
                    input_root=input_root,
                    repo_root=repository,
                    backend=backend,
                )

            with self.assertRaisesRegex(
                ClientObservationReceiptError, "CLIENT_RECEIPT_SOURCE_BINDING_DRIFT"
            ):
                stage_client_observation_receipt(
                    source_path=source,
                    input_root=root / "other-input",
                    repo_root=repository,
                    backend=_Backend(source, read_payload=b"{}"),
                )

            for source_candidate, input_candidate, reason in (
                (Path("relative.json"), input_root, "ABSOLUTE_PATH_REQUIRED"),
                (source, Path("relative-input"), "ABSOLUTE_PATH_REQUIRED"),
                (repository / "nac-issue748-client-observation.json", input_root,
                 "REPOSITORY_EXTERNAL_REQUIRED"),
                (source, repository / "input", "REPOSITORY_EXTERNAL_REQUIRED"),
            ):
                with self.subTest(reason=reason):
                    with self.assertRaisesRegex(ClientObservationReceiptError, reason):
                        stage_client_observation_receipt(
                            source_path=source_candidate,
                            input_root=input_candidate,
                            repo_root=repository,
                            backend=_Backend(source),
                        )

    @unittest.skipUnless(os.name == "nt", "native Windows security contract")
    def test_real_windows_backend_binds_and_exclusively_stages_receipt(self) -> None:
        from src.nac_bff.activation_security_backend import (
            get_platform_security_backend,
        )

        backend = get_platform_security_backend()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source_root = root / "source"
            input_root = root / "input"
            with backend.open_secure_directory(source_root, create=True) as session:
                session.create_exclusive(
                    "nac-issue748-client-observation.json",
                    json.dumps(_receipt()).encode("utf-8"),
                )
            with backend.open_secure_directory(input_root, create=True):
                pass
            source = source_root / "nac-issue748-client-observation.json"

            result = stage_client_observation_receipt(
                source_path=source,
                input_root=input_root,
                repo_root=Path(__file__).resolve().parents[1],
            )

            self.assertEqual(result["status"], "PASSED")
            with backend.open_secure_directory(input_root, create=False) as session:
                staged = session.read_bounded(
                    "client-observation-receipt.json",
                    16 * 1024,
                )
            self.assertEqual(json.loads(staged), _receipt())
            with self.assertRaisesRegex(
                ClientObservationReceiptError, "CLIENT_RECEIPT_ALREADY_EXISTS"
            ):
                stage_client_observation_receipt(
                    source_path=source,
                    input_root=input_root,
                    repo_root=Path(__file__).resolve().parents[1],
                )


if __name__ == "__main__":
    unittest.main()
