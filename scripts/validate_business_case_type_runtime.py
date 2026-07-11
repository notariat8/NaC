from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.notary_kg.business_case_type_runtime import BusinessCaseTypeCatalog


EXPECTED_ACCEPTANCE_IDS = [f"AC-S3-{number:02d}" for number in range(1, 7)]
EXPECTED_VERIFICATION_KEYS = {
    "schema_version",
    "contract_id",
    "domain_contract_id",
    "title",
    "status",
    "leading_issue",
    "acceptance_ids",
    "applies_when",
    "required_context",
    "checks",
    "invariants",
    "thresholds",
    "exit_conditions",
    "required_evidence",
    "pass_condition",
    "failure_behavior",
}
REQUIRED_APPLIES_PATHS = {
    "src/notary_kg/business_case_type_*.py",
    "src/notary_kg/cli.py",
    "src/nac_cli/cli.py",
    "workflows/contracts/business-case-type-runtime.contract.json",
    "workflows/verification-contracts/business-case-type-runtime.verification.json",
    "scripts/validate_business_case_type_runtime.py",
    "tests/test_business_case_type_*.py",
    "agent-context/index.json",
}
REQUIRED_CHECKS = {
    "python3 -m unittest tests.test_business_case_type_runtime tests.test_business_case_type_cache tests.test_business_case_type_cli",
    "python3 scripts/validate_business_case_type_runtime.py",
    "python3 scripts/nac.py contracts verify",
    "python3 scripts/validate_spec_traceability.py",
    "python3 scripts/validate_language_parity.py",
    "python3 scripts/validate_doc_links.py",
    "python3 scripts/nac.py doctor --profile strict",
    "git diff --check",
}
REQUIRED_AGENT_PATHS = {
    "src/notary_kg/business_case_type_runtime.py",
    "src/notary_kg/business_case_type_cache.py",
    "src/notary_kg/business_case_type_transport.py",
    "src/notary_kg/cli.py",
    "src/nac_cli/cli.py",
    "tests/test_business_case_type_runtime.py",
    "tests/test_business_case_type_cache.py",
    "tests/test_business_case_type_cli.py",
    "docs/de/cli.md",
    "docs/en/cli.md",
}
AC_SEMANTIC_TOKENS = {
    "AC-S3-01": ("canonical ids", "aliases", "unknown ids", "retired"),
    "AC-S3-02": ("exactly one", "catalogversion", "duplicates", "timeout"),
    "AC-S3-03": ("300-second", "900-second", "30-second", "site-wide"),
    "AC-S3-04": ("viewer", "never"),
    "AC-S3-05": ("etag", "not_modified", "matter", "document", "person"),
    "AC-S3-06": ("central cli", "strict gate", "independent review"),
}


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        return []
    return value


def validate_verification_contract(verification: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if set(verification) != EXPECTED_VERIFICATION_KEYS:
        errors.append("verification contract top-level shape mismatch")
    expected_scalars = {
        "schema_version": "nac.verification-contract/v0.1",
        "contract_id": "verification.business_case_type_runtime_s3",
        "domain_contract_id": "notarial.business_case_type_runtime",
        "status": "active_mvp",
        "leading_issue": "https://github.com/notariat8/NaC/issues/612",
    }
    for field, expected in expected_scalars.items():
        if verification.get(field) != expected:
            errors.append(f"verification contract {field} mismatch")
    if verification.get("acceptance_ids") != EXPECTED_ACCEPTANCE_IDS:
        errors.append("verification contract must contain exact AC-S3-01..06 order")

    applies_when = verification.get("applies_when")
    if not isinstance(applies_when, dict) or set(applies_when) != {"paths"}:
        errors.append("verification contract applies_when must contain only paths")
        paths: set[str] = set()
    else:
        paths = set(_string_list(applies_when.get("paths")))
    for path in sorted(REQUIRED_APPLIES_PATHS - paths):
        errors.append(f"verification contract applies_when.paths missing {path}")

    required_context = verification.get("required_context")
    context_keys = {"always_on", "scoped", "on_demand", "runtime"}
    if not isinstance(required_context, dict) or set(required_context) != context_keys:
        errors.append("verification contract required_context shape mismatch")
    else:
        for key in sorted(context_keys):
            if not _string_list(required_context.get(key)):
                errors.append(f"verification contract required_context.{key} must be non-empty")

    checks = set(_string_list(verification.get("checks")))
    for check in sorted(REQUIRED_CHECKS - checks):
        errors.append(f"verification contract checks missing {check}")

    invariants = _string_list(verification.get("invariants"))
    if len(invariants) != len(EXPECTED_ACCEPTANCE_IDS):
        errors.append("verification contract requires one invariant per acceptance criterion")
    invariant_by_ac = {
        item.split(":", 1)[0]: item.lower()
        for item in invariants
        if ":" in item
    }
    for acceptance_id, tokens in AC_SEMANTIC_TOKENS.items():
        text = invariant_by_ac.get(acceptance_id, "")
        if not text:
            errors.append(f"verification contract invariant missing {acceptance_id}")
            continue
        for token in tokens:
            if token not in text:
                errors.append(f"verification contract {acceptance_id} semantic token missing: {token}")

    expected_thresholds = {
        "canonical_business_case_type_count": 20,
        "direct_alias_count": 2,
        "registry_revalidation_seconds": 300,
        "registry_hard_expiry_seconds": 900,
        "negative_cache_seconds": 30,
        "required_acceptance_criteria": 6,
        "allowed_live_graph_calls": 0,
    }
    if verification.get("thresholds") != expected_thresholds:
        errors.append("verification contract thresholds mismatch")

    if not _string_list(verification.get("exit_conditions")):
        errors.append("verification contract exit_conditions must be non-empty")
    evidence = set(_string_list(verification.get("required_evidence")))
    for item in {
        "issue_612_acceptance_criteria",
        "focused_runtime_cache_cli_test_result",
        "strict_gate_result",
        "independent_review_result",
    } - evidence:
        errors.append(f"verification contract required_evidence missing {item}")

    expected_pass = {
        "all_checks_pass": True,
        "all_acceptance_ids_covered": True,
        "no_live_graph_or_tenant_access": True,
        "no_unresolved_review_findings": True,
    }
    if verification.get("pass_condition") != expected_pass:
        errors.append("verification contract pass_condition mismatch")

    expected_failures = {
        "acceptance_mismatch": "block_completion",
        "missing_required_context": "fail_closed",
        "fixture_or_runtime_error": "return_redacted_nonzero_result",
        "quality_gate_failure": "block_completion",
        "review_finding": "block_completion",
    }
    if verification.get("failure_behavior") != expected_failures:
        errors.append("verification contract failure_behavior mismatch")
    return errors


def validate_agent_context(agent_context: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    routes = [
        category
        for layer in agent_context.get("layers", [])
        if isinstance(layer, dict)
        for category in layer.get("categories", [])
        if isinstance(category, dict) and category.get("id") == "business_case_type_runtime_s3"
    ]
    if len(routes) != 1:
        return ["agent context requires exactly one business_case_type_runtime_s3 route"]
    paths = set(_string_list(routes[0].get("paths")))
    for path in sorted(REQUIRED_AGENT_PATHS - paths):
        errors.append(f"agent context business_case_type_runtime_s3 route missing {path}")
    return errors


def validate_document_traceability(texts: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for label, text in texts.items():
        for acceptance_id in EXPECTED_ACCEPTANCE_IDS:
            if f"**{acceptance_id}:**" not in text:
                errors.append(f"{label} missing mapped acceptance criterion {acceptance_id}")
    return errors


def validate_repository(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    contract_path = root / "workflows/contracts/business-case-type-runtime.contract.json"
    verification_path = root / "workflows/verification-contracts/business-case-type-runtime.verification.json"
    agent_context_path = root / "agent-context/index.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    verification = json.loads(verification_path.read_text(encoding="utf-8"))
    agent_context = json.loads(agent_context_path.read_text(encoding="utf-8"))

    if contract.get("schema_version") != "nac.business-case-type-runtime/v1":
        errors.append("unexpected domain contract version")
    if contract.get("contract_id") != "notarial.business_case_type_runtime":
        errors.append("unexpected domain contract id")
    if contract.get("scope", {}).get("offline_only") is not True:
        errors.append("S3 must remain offline only")
    for blocked in ("graph_client", "http", "credentials", "matter_data", "document_content"):
        if contract.get("scope", {}).get(blocked) is not False:
            errors.append(f"S3 blocked scope enabled: {blocked}")
    cache = contract.get("registry_cache", {})
    if (cache.get("fresh_seconds"), cache.get("hard_expiry_seconds"), cache.get("negative_seconds")) != (300, 900, 30):
        errors.append("cache boundary mismatch")

    errors.extend(validate_verification_contract(verification))
    errors.extend(validate_agent_context(agent_context))
    texts = {
        "DE spec": (root / "docs/de/superpowers/specs/2026-07-11-business-case-type-runtime-s3-design.md").read_text(encoding="utf-8"),
        "EN spec": (root / "docs/en/superpowers/specs/2026-07-11-business-case-type-runtime-s3-design.md").read_text(encoding="utf-8"),
        "DE plan": (root / "docs/de/superpowers/plans/2026-07-11-business-case-type-runtime-s3.md").read_text(encoding="utf-8"),
        "EN plan": (root / "docs/en/superpowers/plans/2026-07-11-business-case-type-runtime-s3.md").read_text(encoding="utf-8"),
    }
    errors.extend(validate_document_traceability(texts))

    catalog = BusinessCaseTypeCatalog.from_repo(root)
    if len(catalog.entries) != 20 or len(catalog.aliases) != 2:
        errors.append("runtime catalog count mismatch")
    if len(catalog.catalog_version) != 64:
        errors.append("CatalogVersion must be SHA-256")
    return errors


def main() -> int:
    errors = validate_repository()
    status = "PASSED" if not errors else "FAILED"
    print(json.dumps({"status": status, "errors": errors}, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
