from __future__ import annotations

import argparse
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "xnotar-xjustiz-package-boundary.contract.json"
INVENTORY_CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "notarial-application-interface-inventory.contract.json"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "xnotar-xjustiz" / "package-boundary.metadata.json"
CONTRACTS_README = REPO_ROOT / "workflows" / "contracts" / "README.md"
QUALITY_DE = REPO_ROOT / "docs" / "de" / "quality-gate.md"
QUALITY_EN = REPO_ROOT / "docs" / "en" / "quality-gate.md"
DOC_DE = REPO_ROOT / "docs" / "de" / "architecture" / "xnotar-xjustiz-package-boundary.md"
DOC_EN = REPO_ROOT / "docs" / "en" / "architecture" / "xnotar-xjustiz-package-boundary.md"

CONTRACT_ID = "workflow.xnotar_xjustiz_package_boundary"
MANIFEST_SCHEMA_VERSION = "nac.xnotar-xjustiz-package-boundary/v0.1"
INTERFACE_ID = "xnotar_xjustiz_package_boundary"
MODULE_TARGET = "xnotar_exchange_folder_readiness"
VERSION_PIN = "xjustiz_331"
MESSAGE_FILE_NAME = "xjustiz_nachricht.xml"
ATTACHMENTS_FOLDER = "attachments/"
CONTENT_STATUS = "not_stored"
ALLOWED_ATTACHMENT_EXTENSIONS = {".pdf", ".tif", ".tiff", ".p7s", ".p7m"}
ALLOWED_ATTACHMENT_MEDIA_TYPES = {
    "application/pdf",
    "image/tiff",
    "application/pkcs7-signature",
    "application/pkcs7-mime",
}
ALLOWED_HASH_STATUS = {"provided", "not_available_metadata_only"}
REQUIRED_FALSE_POLICY = {
    "xnotar_import_allowed",
    "ben_dispatch_allowed",
    "xsd_ingestion_allowed",
    "wsdl_ingestion_allowed",
    "xml_payload_ingestion_allowed",
    "package_archive_storage_allowed",
    "raw_package_storage_allowed",
    "matter_data_storage_allowed",
    "document_fulltext_storage_allowed",
    "absolute_paths_allowed",
    "live_connector_apply_allowed",
    "external_system_call_allowed",
}
REQUIRED_TRUE_POLICY = {
    "metadata_only",
    "redacted_evidence_only",
    "no_secret_attestation_required",
    "no_matter_data_attestation_required",
}
REQUIRED_SOURCE_DOCUMENTS = {
    "architecture_de",
    "architecture_en",
    "notarial_application_interface_inventory",
    "notarial_onprem_connector_boundaries",
    "matter_data_classification_redaction",
}
REQUIRED_EVIDENCE_FIELDS = {
    "status",
    "interface_id",
    "module_target",
    "version_pin",
    "message_file_count",
    "attachment_file_count",
    "referenced_attachment_count",
    "hash_status",
    "pointer_status",
    "no_secret_attestation",
    "no_matter_data_attestation",
}
BLOCKED_MANIFEST_FIELDS = {
    "body",
    "payload",
    "content",
    "raw_content",
    "xml_payload",
    "xsd_body",
    "wsdl_body",
    "document_full_text",
    "deed_content",
    "register_data",
    "land_register_data",
    "ben_message_content",
    "secret",
    "token",
    "private_key",
    "password",
    "pin",
}
BLOCKED_EVIDENCE_FIELDS = {
    "xml_payload",
    "xsd_body",
    "wsdl_body",
    "package_bytes",
    "document_full_text",
    "deed_content",
    "register_data",
    "land_register_data",
    "ben_message_content",
    "secret",
    "token",
    "private_key",
    "password",
    "pin",
}
REQUIRED_OWNER_GATES = {
    "xnotar_import",
    "productive_ben_send",
    "xml_payload_processing",
    "xsd_or_wsdl_raw_copy",
    "matter_payload_mapping",
    "real_document_storage",
    "register_or_land_register_raw_data_processing",
    "external_system_call",
    "credential_introduction",
}
PROHIBITED_TEXT_MARKERS = {
    "<?xml",
    "<xjustiz",
    "<xsd:",
    "<xs:schema",
    "<wsdl:",
    "<html",
    "BEGIN PRIVATE KEY",
    "BEGIN CERTIFICATE",
    "client_secret",
    "password=",
    "PIN:",
    "ghp_",
    "gho_",
}
FORBIDDEN_REPOSITORY_SUFFIXES = {".zip", ".xsd", ".wsdl", ".xml"}
FORBIDDEN_REPOSITORY_NAMES = {
    "Anwendungsschnittstellen _ Onlinehilfe der Bundesnotarkammer.html",
    "beN _ Onlinehilfe der Bundesnotarkammer.html",
    "xjustiz_0000_grunddatensatz_3_3.xsd",
    MESSAGE_FILE_NAME,
}
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validiert die metadata-only XNotar/XJustiz-Paketgrenze."
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=CONTRACT_PATH,
        help="Pfad zum Workflow-Vertrag.",
    )
    parser.add_argument(
        "--package-manifest",
        action="append",
        type=Path,
        default=[],
        help="Optionale metadata-only Manifestdatei fuer einen Exchange-Folder-Readiness-Check.",
    )
    parser.add_argument(
        "--skip-fixture",
        action="store_true",
        help="Synthetische Standard-Fixture nicht automatisch pruefen.",
    )
    return parser.parse_args()


def validate_contract(path: Path = CONTRACT_PATH) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"Pflichtvertrag fehlt: {_display_path(path)}"]

    text = path.read_text(encoding="utf-8")
    _reject_prohibited_text(path, text, errors)
    payload = _load_json(path, errors)
    if payload is None:
        return errors

    if payload.get("schema_version") != "nac.workflow-contract/v0.1":
        errors.append("schema_version muss nac.workflow-contract/v0.1 sein")
    if payload.get("contract_id") != CONTRACT_ID:
        errors.append(f"contract_id muss {CONTRACT_ID} sein")
    if payload.get("status") != "offline_metadata_only_readiness":
        errors.append("status muss offline_metadata_only_readiness sein")

    errors.extend(_validate_contract_source_documents(payload))
    errors.extend(_validate_contract_scope(payload))
    errors.extend(_validate_repository_policy(payload))
    errors.extend(_validate_package_structure(payload))
    errors.extend(_validate_evidence_shape(payload))
    errors.extend(_validate_owner_gates(payload))
    errors.extend(_validate_validation_commands(payload))
    errors.extend(_validate_inventory_binding())
    errors.extend(_validate_docs_and_repo_boundary())
    return errors


def validate_package_manifest(path_or_payload: Path | dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if isinstance(path_or_payload, Path):
        if not path_or_payload.is_file():
            return [f"Paketmetadaten-Fixture fehlt: {_display_path(path_or_payload)}"]
        text = path_or_payload.read_text(encoding="utf-8")
        _reject_prohibited_text(path_or_payload, text, errors)
        payload = _load_json(path_or_payload, errors)
        if payload is None:
            return errors
    else:
        payload = deepcopy(path_or_payload)
        _reject_prohibited_text(Path("<manifest>"), json.dumps(payload, sort_keys=True), errors)

    if not isinstance(payload, dict):
        return ["Paketmetadaten muessen ein JSON-Objekt sein"]

    errors.extend(_reject_blocked_fields(payload))
    errors.extend(_validate_no_absolute_paths(payload))
    errors.extend(_validate_manifest_identity(payload))
    errors.extend(_validate_manifest_folders(payload))
    errors.extend(_validate_message_file(payload))
    errors.extend(_validate_attachments(payload))
    errors.extend(_validate_counts(payload))
    errors.extend(_validate_manifest_evidence(payload))
    return errors


def _validate_contract_source_documents(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    source_documents = payload.get("source_documents")
    if not isinstance(source_documents, dict):
        return ["source_documents muss ein Objekt sein"]
    for key in sorted(REQUIRED_SOURCE_DOCUMENTS):
        value = source_documents.get(key)
        if not isinstance(value, str):
            errors.append(f"source_documents.{key} fehlt")
            continue
        if _is_unsafe_relative_path(value):
            errors.append(f"source_documents.{key} muss ein relativer Repo-Pfad sein")
            continue
        if not (REPO_ROOT / value).is_file():
            errors.append(f"source_documents.{key} zeigt auf fehlende Datei: {value}")
    return errors


def _validate_contract_scope(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    scope = payload.get("scope")
    if not isinstance(scope, dict):
        return ["scope muss ein Objekt sein"]
    expected = {
        "interface_id": INTERFACE_ID,
        "module_target": MODULE_TARGET,
        "version_pin": VERSION_PIN,
        "xjustiz_package_version": "3.3.1",
        "runtime_mode": "offline_metadata_only",
    }
    for key, expected_value in expected.items():
        if scope.get(key) != expected_value:
            errors.append(f"scope.{key} muss {expected_value} sein")
    if scope.get("offline_only") is not True:
        errors.append("scope.offline_only muss true sein")
    return errors


def _validate_repository_policy(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = payload.get("repository_policy")
    if not isinstance(policy, dict):
        return ["repository_policy muss ein Objekt sein"]
    for key in sorted(REQUIRED_TRUE_POLICY):
        if policy.get(key) is not True:
            errors.append(f"repository_policy.{key} muss true sein")
    for key in sorted(REQUIRED_FALSE_POLICY):
        if policy.get(key) is not False:
            errors.append(f"repository_policy.{key} muss false sein")
    return errors


def _validate_package_structure(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    structure = payload.get("package_structure")
    if not isinstance(structure, dict):
        return ["package_structure muss ein Objekt sein"]
    folders = set(_string_list(structure.get("required_folder_pointers")))
    if ATTACHMENTS_FOLDER not in folders:
        errors.append("package_structure.required_folder_pointers braucht attachments/")
    message = structure.get("message_file")
    if not isinstance(message, dict):
        errors.append("package_structure.message_file muss ein Objekt sein")
    else:
        if message.get("expected_name") != MESSAGE_FILE_NAME:
            errors.append("package_structure.message_file.expected_name muss xjustiz_nachricht.xml sein")
        if message.get("expected_pointer") != MESSAGE_FILE_NAME:
            errors.append("package_structure.message_file.expected_pointer muss xjustiz_nachricht.xml sein")
        if message.get("content_storage") != "forbidden":
            errors.append("package_structure.message_file.content_storage muss forbidden sein")
    attachment_rules = structure.get("attachment_rules")
    if not isinstance(attachment_rules, dict):
        errors.append("package_structure.attachment_rules muss ein Objekt sein")
    else:
        if attachment_rules.get("folder_pointer") != ATTACHMENTS_FOLDER:
            errors.append("package_structure.attachment_rules.folder_pointer muss attachments/ sein")
        if attachment_rules.get("references_must_match_declared_attachments") is not True:
            errors.append("package_structure.attachment_rules.references_must_match_declared_attachments muss true sein")
        extensions = set(_string_list(attachment_rules.get("allowed_extensions")))
        for extension in sorted(ALLOWED_ATTACHMENT_EXTENSIONS - extensions):
            errors.append(f"package_structure.attachment_rules.allowed_extensions fehlt: {extension}")
        media_types = set(_string_list(attachment_rules.get("allowed_media_types")))
        for media_type in sorted(ALLOWED_ATTACHMENT_MEDIA_TYPES - media_types):
            errors.append(f"package_structure.attachment_rules.allowed_media_types fehlt: {media_type}")
    manifest_schema = payload.get("manifest_schema")
    if not isinstance(manifest_schema, dict):
        errors.append("manifest_schema muss ein Objekt sein")
    else:
        if manifest_schema.get("schema_version") != MANIFEST_SCHEMA_VERSION:
            errors.append(f"manifest_schema.schema_version muss {MANIFEST_SCHEMA_VERSION} sein")
        fixture = manifest_schema.get("synthetic_fixture")
        if not isinstance(fixture, str) or _is_unsafe_relative_path(fixture):
            errors.append("manifest_schema.synthetic_fixture muss ein relativer Fixture-Pfad sein")
        elif not (REPO_ROOT / fixture).is_file():
            errors.append(f"manifest_schema.synthetic_fixture fehlt: {fixture}")
    return errors


def _validate_evidence_shape(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    evidence_shape = payload.get("evidence_shape")
    if not isinstance(evidence_shape, dict):
        return ["evidence_shape muss ein Objekt sein"]
    allowed = set(_string_list(evidence_shape.get("allowed_fields")))
    blocked = set(_string_list(evidence_shape.get("blocked_fields")))
    for field in sorted(REQUIRED_EVIDENCE_FIELDS - allowed):
        errors.append(f"evidence_shape.allowed_fields fehlt: {field}")
    for field in sorted(BLOCKED_EVIDENCE_FIELDS - blocked):
        errors.append(f"evidence_shape.blocked_fields fehlt: {field}")
    if allowed & blocked:
        errors.append("evidence_shape darf keine Felder zugleich erlauben und sperren")
    return errors


def _validate_owner_gates(payload: dict[str, Any]) -> list[str]:
    gates = set(_string_list(payload.get("owner_gates")))
    return [f"owner_gates fehlt: {gate}" for gate in sorted(REQUIRED_OWNER_GATES - gates)]


def _validate_validation_commands(payload: dict[str, Any]) -> list[str]:
    commands = set(_string_list(payload.get("validation_commands")))
    required = {
        "python scripts/validate_xnotar_xjustiz_package_boundary.py",
        "python -m unittest tests/test_xnotar_xjustiz_package_boundary.py",
    }
    return [f"validation_commands fehlt: {command}" for command in sorted(required - commands)]


def _validate_inventory_binding() -> list[str]:
    errors: list[str] = []
    inventory = _load_json(INVENTORY_CONTRACT_PATH, errors)
    if inventory is None:
        return errors
    interfaces = {
        item.get("id"): item
        for item in inventory.get("interfaces", [])
        if isinstance(item, dict)
    }
    row = interfaces.get(INTERFACE_ID)
    if not isinstance(row, dict):
        return [f"notarielles Anwendungsschnittstellen-Inventar fehlt: {INTERFACE_ID}"]
    expected = {
        "source": "xnotar_xjustiz_package_boundary_contract",
        "mvp_boundary": "package_boundary_metadata_only_no_import",
    }
    for key, expected_value in expected.items():
        if row.get(key) != expected_value:
            errors.append(f"Inventory-Zeile {INTERFACE_ID}.{key} muss {expected_value} sein")
    families = set(_string_list(row.get("families")))
    for family in ("exchange_folder_metadata", "xjustiz_message_pointer", "redacted_readiness_evidence"):
        if family not in families:
            errors.append(f"Inventory-Zeile {INTERFACE_ID}.families fehlt: {family}")
    source_documents = inventory.get("source_documents")
    source = source_documents.get("xnotar_xjustiz_package_boundary_contract") if isinstance(source_documents, dict) else None
    if not isinstance(source, dict):
        errors.append("Inventory-Quelle xnotar_xjustiz_package_boundary_contract fehlt")
    elif source.get("path") != "workflows/contracts/xnotar-xjustiz-package-boundary.contract.json":
        errors.append("Inventory-Quelle xnotar_xjustiz_package_boundary_contract.path zeigt nicht auf Boundary-Vertrag")
    return errors


def _validate_docs_and_repo_boundary() -> list[str]:
    errors: list[str] = []
    for path, marker in (
        (DOC_DE, "XNotar-/XJustiz-Paketgrenze"),
        (DOC_EN, "XNotar/XJustiz Package Boundary"),
        (CONTRACTS_README, "xnotar-xjustiz-package-boundary.contract.json"),
        (QUALITY_DE, "xnotar_xjustiz_package_boundary"),
        (QUALITY_EN, "xnotar_xjustiz_package_boundary"),
    ):
        if not path.is_file():
            errors.append(f"Pflichtdokument fehlt: {_display_path(path)}")
            continue
        if marker not in path.read_text(encoding="utf-8"):
            errors.append(f"{_display_path(path)} enthaelt Marker nicht: {marker}")

    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.lower() in FORBIDDEN_REPOSITORY_SUFFIXES:
            errors.append(f"Rohformat darf nicht im Repo liegen: {path.relative_to(REPO_ROOT)}")
        if path.name in FORBIDDEN_REPOSITORY_NAMES and path != CONTRACT_PATH:
            errors.append(f"Quell-/Payload-Artefakt darf nicht im Repo liegen: {path.relative_to(REPO_ROOT)}")
    return errors


def _validate_manifest_identity(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "interface_id": INTERFACE_ID,
        "module_target": MODULE_TARGET,
        "version_pin": VERSION_PIN,
    }
    for key, expected_value in expected.items():
        if payload.get(key) != expected_value:
            errors.append(f"{key} muss {expected_value} sein")
    if payload.get("status") not in {"READY_METADATA_ONLY", "NOT_READY_METADATA_ONLY"}:
        errors.append("status muss READY_METADATA_ONLY oder NOT_READY_METADATA_ONLY sein")
    return errors


def _validate_manifest_folders(payload: dict[str, Any]) -> list[str]:
    folders = payload.get("folders")
    if not isinstance(folders, list):
        return ["folders muss eine Liste sein"]
    has_attachments = False
    errors: list[str] = []
    for index, folder in enumerate(folders, start=1):
        if not isinstance(folder, dict):
            errors.append(f"folders[{index}] muss ein Objekt sein")
            continue
        if folder.get("path") == ATTACHMENTS_FOLDER and folder.get("kind") == "directory":
            has_attachments = True
        if folder.get("content_status") != CONTENT_STATUS:
            errors.append(f"folders[{index}].content_status muss {CONTENT_STATUS} sein")
    if not has_attachments:
        errors.append("folders muss attachments/ als directory enthalten")
    return errors


def _validate_message_file(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    message = payload.get("message_file")
    if not isinstance(message, dict):
        return ["message_file muss ein Objekt sein"]
    if message.get("name") != MESSAGE_FILE_NAME:
        errors.append("message_file.name muss xjustiz_nachricht.xml sein")
    if message.get("pointer") != MESSAGE_FILE_NAME:
        errors.append("message_file.pointer muss xjustiz_nachricht.xml sein")
    if message.get("content_status") != CONTENT_STATUS:
        errors.append(f"message_file.content_status muss {CONTENT_STATUS} sein")
    errors.extend(_validate_hash_metadata("message_file", message))
    return errors


def _validate_attachments(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    attachments = payload.get("attachments")
    references = payload.get("referenced_attachments")
    if not isinstance(attachments, list):
        return ["attachments muss eine Liste sein"]
    if not isinstance(references, list):
        return ["referenced_attachments muss eine Liste sein"]

    attachment_names: set[str] = set()
    attachment_pointers: set[str] = set()
    for index, attachment in enumerate(attachments, start=1):
        if not isinstance(attachment, dict):
            errors.append(f"attachments[{index}] muss ein Objekt sein")
            continue
        label = f"attachments[{index}]"
        name = attachment.get("name")
        pointer = attachment.get("pointer")
        if not isinstance(name, str) or not name:
            errors.append(f"{label}.name muss gesetzt sein")
            continue
        if name in attachment_names:
            errors.append(f"Attachment doppelt: {name}")
        attachment_names.add(name)
        if not isinstance(pointer, str) or not pointer:
            errors.append(f"{label}.pointer muss gesetzt sein")
            continue
        attachment_pointers.add(pointer)
        if not pointer.startswith(ATTACHMENTS_FOLDER):
            errors.append(f"{label}.pointer muss unter attachments/ liegen")
        if Path(pointer).name != name:
            errors.append(f"{label}.name muss zum Pointer-Dateinamen passen")
        if Path(name).suffix.lower() not in ALLOWED_ATTACHMENT_EXTENSIONS:
            errors.append(f"{label}.name hat unzulässigen Dateityp: {name}")
        media_type = attachment.get("media_type")
        if media_type not in ALLOWED_ATTACHMENT_MEDIA_TYPES:
            errors.append(f"{label}.media_type ist unzulässig: {media_type}")
        if attachment.get("content_status") != CONTENT_STATUS:
            errors.append(f"{label}.content_status muss {CONTENT_STATUS} sein")
        errors.extend(_validate_hash_metadata(label, attachment))

    referenced_names: set[str] = set()
    referenced_pointers: set[str] = set()
    for index, reference in enumerate(references, start=1):
        if not isinstance(reference, dict):
            errors.append(f"referenced_attachments[{index}] muss ein Objekt sein")
            continue
        name = reference.get("name")
        pointer = reference.get("pointer")
        if not isinstance(name, str) or not name:
            errors.append(f"referenced_attachments[{index}].name muss gesetzt sein")
            continue
        if not isinstance(pointer, str) or not pointer:
            errors.append(f"referenced_attachments[{index}].pointer muss gesetzt sein")
            continue
        referenced_names.add(name)
        referenced_pointers.add(pointer)
        if not pointer.startswith(ATTACHMENTS_FOLDER):
            errors.append(f"referenced_attachments[{index}].pointer muss unter attachments/ liegen")

    missing = referenced_names - attachment_names
    unreferenced = attachment_names - referenced_names
    if missing:
        errors.append(f"referenced_attachments verweist auf unbekannte Anlagen: {', '.join(sorted(missing))}")
    if unreferenced:
        errors.append(f"attachments enthaelt nicht referenzierte Anlagen: {', '.join(sorted(unreferenced))}")
    if referenced_pointers - attachment_pointers:
        errors.append("referenced_attachments.pointer muss deklarierten Attachment-Pointern entsprechen")
    return errors


def _validate_counts(payload: dict[str, Any]) -> list[str]:
    counts = payload.get("counts")
    if not isinstance(counts, dict):
        return ["counts muss ein Objekt sein"]
    attachments = payload.get("attachments") if isinstance(payload.get("attachments"), list) else []
    references = payload.get("referenced_attachments") if isinstance(payload.get("referenced_attachments"), list) else []
    expected = {
        "message_file_count": 1,
        "attachment_file_count": len(attachments),
        "referenced_attachment_count": len(references),
        "total_file_count": 1 + len(attachments),
    }
    errors: list[str] = []
    for key, value in expected.items():
        if counts.get(key) != value:
            errors.append(f"counts.{key} muss {value} sein")
    return errors


def _validate_manifest_evidence(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    evidence = payload.get("evidence")
    if not isinstance(evidence, dict):
        return ["evidence muss ein Objekt sein"]
    allowed = REQUIRED_EVIDENCE_FIELDS
    extra = set(evidence) - allowed
    missing = allowed - set(evidence)
    for field in sorted(missing):
        errors.append(f"evidence fehlt: {field}")
    for field in sorted(extra):
        errors.append(f"evidence enthaelt nicht erlaubtes Feld: {field}")
    for field in sorted(set(evidence) & BLOCKED_EVIDENCE_FIELDS):
        errors.append(f"evidence enthaelt gesperrtes Feld: {field}")

    counts = payload.get("counts") if isinstance(payload.get("counts"), dict) else {}
    expected = {
        "status": payload.get("status"),
        "interface_id": INTERFACE_ID,
        "module_target": MODULE_TARGET,
        "version_pin": VERSION_PIN,
        "message_file_count": counts.get("message_file_count"),
        "attachment_file_count": counts.get("attachment_file_count"),
        "referenced_attachment_count": counts.get("referenced_attachment_count"),
    }
    for key, expected_value in expected.items():
        if evidence.get(key) != expected_value:
            errors.append(f"evidence.{key} muss {expected_value} sein")
    if evidence.get("no_secret_attestation") is not True:
        errors.append("evidence.no_secret_attestation muss true sein")
    if evidence.get("no_matter_data_attestation") is not True:
        errors.append("evidence.no_matter_data_attestation muss true sein")
    if evidence.get("pointer_status") != "relative_pointers_only":
        errors.append("evidence.pointer_status muss relative_pointers_only sein")
    return errors


def _validate_hash_metadata(label: str, item: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    status = item.get("hash_status")
    if status not in ALLOWED_HASH_STATUS:
        errors.append(f"{label}.hash_status muss provided oder not_available_metadata_only sein")
        return errors
    value = item.get("hash_sha256")
    if status == "provided":
        if not isinstance(value, str) or SHA256_RE.match(value) is None:
            errors.append(f"{label}.hash_sha256 muss ein SHA-256-Hexwert sein")
    elif "hash_sha256" in item:
        errors.append(f"{label}.hash_sha256 darf nur bei hash_status=provided gesetzt sein")
    return errors


def _reject_blocked_fields(value: Any, prefix: str = "") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            if key in BLOCKED_MANIFEST_FIELDS:
                errors.append(f"gesperrtes Manifestfeld: {path}")
            errors.extend(_reject_blocked_fields(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_reject_blocked_fields(child, f"{prefix}[{index}]"))
    return errors


def _validate_no_absolute_paths(value: Any, prefix: str = "") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            if key in {"path", "pointer", "root_pointer"} or key.endswith("_pointer"):
                if isinstance(child, str) and _is_unsafe_relative_path(child):
                    errors.append(f"{path} muss ein relativer pfadloser oder repo-relativer Pointer sein")
            errors.extend(_validate_no_absolute_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_validate_no_absolute_paths(child, f"{prefix}[{index}]"))
    return errors


def _is_unsafe_relative_path(value: str) -> bool:
    if not value or value.startswith(("/", "\\")):
        return True
    if "\\" in value or "://" in value:
        return True
    if re.match(r"^[A-Za-z]:", value):
        return True
    return any(part == ".." for part in value.split("/"))


def _reject_prohibited_text(path: Path, text: str, errors: list[str]) -> None:
    lowered = text.lower()
    for marker in PROHIBITED_TEXT_MARKERS:
        if marker.lower() in lowered:
            errors.append(f"{_display_path(path)} enthaelt unzulässigen Marker: {marker}")


def _load_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{_display_path(path)} ist kein gueltiges JSON: {exc}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{_display_path(path)} muss ein JSON-Objekt sein")
        return None
    return payload


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    args = parse_args()
    errors = validate_contract(args.contract)

    manifest_paths = list(args.package_manifest)
    if not args.skip_fixture and FIXTURE_PATH.is_file():
        manifest_paths.insert(0, FIXTURE_PATH)
    for manifest_path in manifest_paths:
        errors.extend(validate_package_manifest(manifest_path))

    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("STATUS: PASSED")
    print("OK: XNotar/XJustiz-Paketgrenze bleibt metadata-only, pfadrelativ und redigiert ohne Rohpakete, XML/XSD/WSDL, Secrets oder Mandatsdaten.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
