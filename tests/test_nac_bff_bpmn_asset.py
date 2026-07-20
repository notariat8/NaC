from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_bff.bpmn_asset import (  # noqa: E402
    BpmnAsset,
    BpmnAssetError,
    CANONICAL_BPMN_MIME_TYPE,
    CANONICAL_BPMN_MODEL_KEY,
    CANONICAL_BPMN_SHA256,
    MAX_BPMN_ASSET_BYTES,
    CanonicalBpmnAssetFilePort,
)


CANONICAL_PATH = REPO_ROOT / "bpmn/immobilienkaufvertrag.bpmn"


class CanonicalBpmnAssetFilePortTests(unittest.TestCase):
    def _write(self, content: bytes) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "model.bpmn"
        path.write_bytes(content)
        return path

    def test_reads_only_the_canonical_hash_bound_model(self) -> None:
        content = CANONICAL_PATH.read_bytes()

        asset = CanonicalBpmnAssetFilePort(CANONICAL_PATH).read_canonical_bpmn()

        self.assertEqual(asset.model_key, CANONICAL_BPMN_MODEL_KEY)
        self.assertEqual(asset.mime_type, CANONICAL_BPMN_MIME_TYPE)
        self.assertEqual(asset.sha256, CANONICAL_BPMN_SHA256)
        self.assertEqual(asset.xml.encode("utf-8"), content)
        self.assertEqual(hashlib.sha256(content).hexdigest(), CANONICAL_BPMN_SHA256)
        self.assertLessEqual(len(content), MAX_BPMN_ASSET_BYTES)
        self.assertEqual(
            set(asset.as_dict()), {"modelKey", "mimeType", "sha256", "xml"}
        )

    def test_rejects_missing_empty_oversized_and_non_utf8_assets(self) -> None:
        cases = (
            Path("/definitely/missing/immobilienkaufvertrag.bpmn"),
            self._write(b""),
            self._write(b"x" * (MAX_BPMN_ASSET_BYTES + 1)),
            self._write(b"\xff\xfe"),
        )
        for path in cases:
            with self.subTest(path=path):
                with self.assertRaises(BpmnAssetError):
                    CanonicalBpmnAssetFilePort(path).read_canonical_bpmn()

    def test_rejects_doctype_entity_wrong_process_and_hash_drift(self) -> None:
        canonical = CANONICAL_PATH.read_bytes()
        cases = (
            b'<!DOCTYPE x><bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"><bpmn:process id="Process_immobilienkaufvertrag"/></bpmn:definitions>',
            b'<!ENTITY x "unsafe"><bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"><bpmn:process id="Process_immobilienkaufvertrag"/></bpmn:definitions>',
            canonical.replace(
                b'Process_immobilienkaufvertrag', b'Process_unerwartet', 1
            ),
            canonical.replace(b"Immobilienkaufvertrag", b"Immobilienkauf", 1),
        )
        for content in cases:
            with self.subTest(prefix=content[:40]):
                with self.assertRaises(BpmnAssetError):
                    CanonicalBpmnAssetFilePort(
                        self._write(content)
                    ).read_canonical_bpmn()

    def test_rejects_forged_asset_metadata_at_the_domain_boundary(self) -> None:
        canonical_xml = CANONICAL_PATH.read_text(encoding="utf-8")
        invalid_values = (
            {"model_key": "Process_other"},
            {"mime_type": "text/xml"},
            {"sha256": "0" * 64},
            {"xml": canonical_xml.replace("Immobilienkaufvertrag", "Abweichung", 1)},
        )
        baseline = {
            "model_key": CANONICAL_BPMN_MODEL_KEY,
            "mime_type": CANONICAL_BPMN_MIME_TYPE,
            "sha256": CANONICAL_BPMN_SHA256,
            "xml": canonical_xml,
        }
        for override in invalid_values:
            with self.subTest(override=next(iter(override))):
                with self.assertRaises(BpmnAssetError):
                    BpmnAsset(**(baseline | override))


if __name__ == "__main__":
    raise SystemExit(unittest.main())
