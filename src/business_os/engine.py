from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .models import ProcessDocument, ValidationResult
from .processors import render_process_summary
from .registry import PROCESS_DEFINITIONS, schema_path
from .schema_tools import validate_schema


@dataclass(slots=True)
class MonthlyCloseReport:
    year: int
    month: int
    invoice_total_gross: float
    bookkeeping_debit: float
    bookkeeping_credit: float
    tax_cases: int
    request_ids: list[str]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


class BusinessProcessEngine:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def load_document(self, document_path: Path) -> ProcessDocument:
        absolute_path = document_path
        if not absolute_path.is_absolute():
            absolute_path = self.repo_root / document_path
        with absolute_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return ProcessDocument(path=absolute_path, content=payload)

    def validate_document(self, document_path: Path) -> ValidationResult:
        document = self.load_document(document_path)
        errors: list[str] = []
        warnings: list[str] = []

        process_type = document.process_type
        if process_type not in PROCESS_DEFINITIONS:
            errors.append(f"Unbekannter Prozess-Typ: {process_type}")
            return ValidationResult(document=document, errors=errors, warnings=warnings)

        definition = PROCESS_DEFINITIONS[process_type]
        schema = self._load_schema(process_type)
        errors.extend(validate_schema(document.content, schema))

        if document.status not in definition.allowed_statuses:
            errors.append(
                f"Status {document.status!r} ist fuer {process_type!r} nicht erlaubt"
            )

        errors.extend(self._validate_business_rules(document))
        warnings.extend(self._build_warnings(document))
        return ValidationResult(document=document, errors=errors, warnings=warnings)

    def render_summary(self, document_path: Path) -> str:
        document = self.load_document(document_path)
        return render_process_summary(document.content)

    def validate_all_processes(self) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        for file_path in sorted(self._iter_process_files()):
            relative_path = file_path.relative_to(self.repo_root)
            results.append(self.validate_document(relative_path))
        return results

    def monthly_close(self, year: int, month: int) -> MonthlyCloseReport:
        request_ids: list[str] = []
        invoice_total_gross = 0.0
        bookkeeping_debit = 0.0
        bookkeeping_credit = 0.0
        tax_cases = 0

        for file_path in self._iter_process_files():
            payload = self.load_document(file_path).content
            if int(payload["year"]) != year:
                continue

            if payload["process_type"] == "invoice" and payload["issue_date"].startswith(f"{year}-{month:02d}"):
                request_ids.append(payload["request_id"])
                for item in payload["items"]:
                    net = item["quantity"] * item["unit_price"]
                    invoice_total_gross += net + (net * item["tax_rate"] / 100.0)

            if payload["process_type"] == "bookkeeping" and payload["entry_date"].startswith(f"{year}-{month:02d}"):
                request_ids.append(payload["request_id"])
                bookkeeping_debit += sum(
                    line["amount"] for line in payload["lines"] if line["direction"] == "debit"
                )
                bookkeeping_credit += sum(
                    line["amount"] for line in payload["lines"] if line["direction"] == "credit"
                )

            if payload["process_type"] == "tax" and payload["period"] == f"{year}-{month:02d}":
                request_ids.append(payload["request_id"])
                tax_cases += 1

        return MonthlyCloseReport(
            year=year,
            month=month,
            invoice_total_gross=round(invoice_total_gross, 2),
            bookkeeping_debit=round(bookkeeping_debit, 2),
            bookkeeping_credit=round(bookkeeping_credit, 2),
            tax_cases=tax_cases,
            request_ids=sorted(set(request_ids)),
        )

    def _load_schema(self, process_type: str) -> dict[str, Any]:
        with schema_path(self.repo_root, process_type).open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _validate_business_rules(self, document: ProcessDocument) -> list[str]:
        errors: list[str] = []
        payload = document.content
        process_type = document.process_type

        duplicate_paths = self._idempotency_duplicates()
        current_path = str(document.path.resolve())
        duplicates = [
            path
            for path in duplicate_paths.get(document.idempotency_key, [])
            if path != current_path
        ]
        if duplicates:
            errors.append(
                f"Idempotency-Key {document.idempotency_key!r} existiert bereits in {len(duplicates)} anderem Vorgang"
            )

        if process_type == "invoice":
            if payload["due_date"] < payload["issue_date"]:
                errors.append("due_date darf nicht vor issue_date liegen")

        if process_type == "bookkeeping":
            debit = sum(line["amount"] for line in payload["lines"] if line["direction"] == "debit")
            credit = sum(line["amount"] for line in payload["lines"] if line["direction"] == "credit")
            if round(debit, 2) != round(credit, 2):
                errors.append("Buchung ist nicht ausgeglichen")

        if process_type == "tax":
            if payload["status"] == "submitted" and payload.get("requires_review", False):
                errors.append("submitted darf nur nach expliziter Freigabe ausserhalb dieses Referenzsystems erfolgen")

        errors.extend(self._validate_actor_context(payload))

        if process_type == "invoice":
            errors.extend(self._validate_rvg_requirements(payload))

        return errors

    def _validate_actor_context(self, payload: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        actor_context = payload.get("actor_context", {})
        if not isinstance(actor_context, dict):
            return ["actor_context muss ein Objekt sein"]

        decision_type = actor_context.get("requested_decision_type")
        impact_level = actor_context.get("impact_level")
        compliance_impact = actor_context.get("compliance_impact")
        approver_role = actor_context.get("approver_role")
        actor_role = actor_context.get("actor_role")

        if decision_type == "requires_approval" and not approver_role:
            errors.append("requires_approval erfordert approver_role")

        if decision_type == "self_resolve":
            if impact_level in {"medium", "high"}:
                errors.append("self_resolve ist nur fuer low impact erlaubt")
            if compliance_impact is True:
                errors.append("self_resolve ist bei compliance_impact=true nicht erlaubt")

        if (
            decision_type == "requires_approval"
            and isinstance(actor_role, str)
            and isinstance(approver_role, str)
            and actor_role == approver_role
        ):
            errors.append("actor_role und approver_role muessen fuer Vier-Augen-Prinzip verschieden sein")

        requested_qualification = actor_context.get("requested_qualification", [])
        qualification_evidence = actor_context.get("qualification_evidence", [])
        if requested_qualification and not qualification_evidence:
            errors.append("requested_qualification erfordert qualification_evidence")

        return errors

    def _validate_rvg_requirements(self, payload: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        metadata = payload.get("metadata", {})
        if not isinstance(metadata, dict):
            return errors

        if metadata.get("billing_regime") != "rvg":
            return errors

        actor_context = payload.get("actor_context", {})
        qualifications = actor_context.get("requested_qualification", [])
        decision_type = actor_context.get("requested_decision_type")
        if not isinstance(qualifications, list) or "rvg_billing_trained" not in qualifications:
            errors.append("RVG-Rechnung erfordert Qualifikation rvg_billing_trained")
        if decision_type == "self_resolve":
            errors.append("RVG-Rechnung darf nicht als self_resolve eingereicht werden")
        return errors

    def _build_warnings(self, document: ProcessDocument) -> list[str]:
        warnings: list[str] = []
        definition = PROCESS_DEFINITIONS[document.process_type]
        if document.status in definition.review_statuses:
            warnings.append(
                f"Status {document.status!r} sollte ueber Review oder Environment-Freigabe abgesichert werden"
            )
        return warnings

    def _iter_process_files(self):
        return self.repo_root.glob("processes/*/*/*.json")

    def _idempotency_duplicates(self) -> dict[str, list[str]]:
        by_key: dict[str, list[str]] = defaultdict(list)
        for file_path in self._iter_process_files():
            with file_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            key = str(payload.get("idempotency_key", ""))
            if key:
                by_key[key].append(str(file_path.resolve()))
        return by_key
