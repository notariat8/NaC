from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import xml.etree.ElementTree as ElementTree


CANONICAL_BPMN_MODEL_KEY = "Process_immobilienkaufvertrag"
CANONICAL_BPMN_MIME_TYPE = "application/xml"
CANONICAL_BPMN_SHA256 = (
    "02cc15850e7e828189214a75ad3edfa3a2e704d5a766b3aa2237f2445040dfa0"
)
MAX_BPMN_ASSET_BYTES = 48 * 1024
_BPMN_NAMESPACE = "http://www.omg.org/spec/BPMN/20100524/MODEL"
_ASSET_RELATIVE_PATH = Path("bpmn/immobilienkaufvertrag.bpmn")
_UNSAFE_DECLARATION = re.compile(br"<!\s*(?:DOCTYPE|ENTITY)\b", re.IGNORECASE)


class BpmnAssetError(ValueError):
    """The canonical BPMN runtime asset failed its fixed trust contract."""


@dataclass(frozen=True, slots=True)
class BpmnAsset:
    model_key: str
    mime_type: str
    sha256: str
    xml: str

    def __post_init__(self) -> None:
        if (
            self.model_key != CANONICAL_BPMN_MODEL_KEY
            or self.mime_type != CANONICAL_BPMN_MIME_TYPE
            or self.sha256 != CANONICAL_BPMN_SHA256
            or not isinstance(self.xml, str)
        ):
            raise BpmnAssetError("canonical BPMN asset metadata is invalid")
        try:
            content = self.xml.encode("utf-8")
        except UnicodeEncodeError:
            raise BpmnAssetError("canonical BPMN asset is not UTF-8") from None
        if not content or len(content) > MAX_BPMN_ASSET_BYTES:
            raise BpmnAssetError("canonical BPMN asset size is invalid")
        if _UNSAFE_DECLARATION.search(content):
            raise BpmnAssetError(
                "canonical BPMN asset contains an unsafe declaration"
            )
        try:
            root = ElementTree.fromstring(self.xml)
        except ElementTree.ParseError:
            raise BpmnAssetError("canonical BPMN asset is not valid XML") from None
        processes = root.findall(f".//{{{_BPMN_NAMESPACE}}}process")
        if (
            len(processes) != 1
            or processes[0].get("id") != CANONICAL_BPMN_MODEL_KEY
        ):
            raise BpmnAssetError("canonical BPMN process ID is invalid")
        if hashlib.sha256(content).hexdigest() != self.sha256:
            raise BpmnAssetError("canonical BPMN asset hash is invalid")

    def as_dict(self) -> dict[str, str]:
        return {
            "modelKey": self.model_key,
            "mimeType": self.mime_type,
            "sha256": self.sha256,
            "xml": self.xml,
        }


class CanonicalBpmnAssetFilePort:
    """Read the single package-bound Immobilienkaufvertrag BPMN model."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = _default_asset_path() if path is None else Path(path)

    def read_canonical_bpmn(self) -> BpmnAsset:
        try:
            content = self._path.read_bytes()
        except OSError:
            raise BpmnAssetError("canonical BPMN asset is unavailable") from None

        if not content or len(content) > MAX_BPMN_ASSET_BYTES:
            raise BpmnAssetError("canonical BPMN asset size is invalid")
        if _UNSAFE_DECLARATION.search(content):
            raise BpmnAssetError("canonical BPMN asset contains an unsafe declaration")
        try:
            xml = content.decode("utf-8")
        except UnicodeDecodeError:
            raise BpmnAssetError("canonical BPMN asset is not UTF-8") from None
        try:
            root = ElementTree.fromstring(xml)
        except ElementTree.ParseError:
            raise BpmnAssetError("canonical BPMN asset is not valid XML") from None

        processes = root.findall(f".//{{{_BPMN_NAMESPACE}}}process")
        if (
            len(processes) != 1
            or processes[0].get("id") != CANONICAL_BPMN_MODEL_KEY
        ):
            raise BpmnAssetError("canonical BPMN process ID is invalid")

        digest = hashlib.sha256(content).hexdigest()
        if digest != CANONICAL_BPMN_SHA256:
            raise BpmnAssetError("canonical BPMN asset hash is invalid")
        return BpmnAsset(
            model_key=CANONICAL_BPMN_MODEL_KEY,
            mime_type=CANONICAL_BPMN_MIME_TYPE,
            sha256=digest,
            xml=xml,
        )


def _default_asset_path() -> Path:
    package_root = Path(__file__).resolve().parents[1]
    packaged_path = package_root / _ASSET_RELATIVE_PATH
    if packaged_path.is_file():
        return packaged_path

    repository_path = Path(__file__).resolve().parents[2] / _ASSET_RELATIVE_PATH
    if repository_path.is_file():
        return repository_path
    return packaged_path
