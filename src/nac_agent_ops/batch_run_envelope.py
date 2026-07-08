from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "nac.codex-5h-batch-run-envelope/v0.1"
DEFAULT_TEMPLATE_SESSION_ID = "codex-5h-batch-template"

REQUIRED_CONTEXT_LAYERS = {"always_on", "scoped", "on_demand", "runtime"}
REQUIRED_STOP_LINES = {
    "no_live_tenant_apply",
    "no_secrets_or_credentials",
    "no_destructive_git_or_filesystem",
    "no_merge_without_owner_approval",
}
PROHIBITED_SHARED_CONTEXT_MARKERS = {
    "runtime_logs_shared",
    "raw_tool_output_shared",
    "secrets_shared",
    "tokens_shared",
    "mandate_data_shared",
    "customer_data_shared",
}


def build_batch_run_envelope_template(
    *,
    session_id: str = DEFAULT_TEMPLATE_SESSION_ID,
    objective: str = "Prepare independent NaC offline MVP slices in parallel.",
    time_budget_hours: int = 5,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "TEMPLATE",
        "generated_at": _now(),
        "session_id": session_id,
        "objective": objective,
        "time_budget_hours": time_budget_hours,
        "source": {
            "explicit_offline_owner_request": True,
            "github_issue": None,
            "owner_request_summary": "5h autonomous offline batch; no live tenant action and no merges.",
        },
        "context_load_plan": {
            "always_on": ["AGENTS.md", "policies/process-policy.yaml"],
            "scoped": ["docs/AGENTS.md", "workflows/contracts/AGENTS.md"],
            "on_demand": ["agent-context/index.json", "workflows/verification-contracts/"],
            "runtime": ["fresh git status", "fresh validator output", "fresh PR checks"],
            "shared_context_excludes": sorted(PROHIBITED_SHARED_CONTEXT_MARKERS),
        },
        "lanes": [
            {
                "id": "lane-a",
                "slice": "example-offline-slice",
                "worktree_required": True,
                "worktree_path": "NaC-example-offline-slice",
                "write_scope": ["src/example/", "tests/test_example.py"],
                "owner_gate_required": False,
            },
            {
                "id": "lane-b",
                "slice": "example-second-offline-slice",
                "worktree_required": True,
                "worktree_path": "NaC-example-second-offline-slice",
                "write_scope": ["docs/example/", "tests/test_example_docs.py"],
                "owner_gate_required": False,
            }
        ],
        "subagent_review": {
            "independent_review_questions_count": 2,
            "subagent_plan": [
                {"id": "scope", "role": "scope mapper", "read_only": True},
                {"id": "validation", "role": "validation reviewer", "read_only": True},
            ],
            "no_split_reason": None,
        },
        "command_risk_matrix": [
            {"risk": "GREEN", "command": "git status", "decision": "allow"},
            {"risk": "GREEN", "command": "python3 scripts/quality_gate.py --profile strict", "decision": "allow"},
            {"risk": "YELLOW", "command": "git push", "decision": "owner_gate"},
            {"risk": "YELLOW", "command": "gh pr create", "decision": "owner_gate"},
        ],
        "stop_lines": sorted(REQUIRED_STOP_LINES),
        "validator_matrix": [
            "python3 scripts/validate_codex_5h_batch_run_envelope.py",
            "python3 scripts/nac.py contracts verify",
            "python3 scripts/quality_gate.py --profile strict",
        ],
        "resume_checkpoints": [
            "fresh git status per worktree",
            "pending PR and CI state",
            "open owner gates batched as copyable text",
        ],
        "owner_gates": [
            "PR merge",
            "branch cleanup",
            "live Microsoft 365 tenant action",
            "secret, certificate or Entra credential change",
            "destructive git or filesystem cleanup",
        ],
        "privacy": {
            "storesTokensOrSecrets": False,
            "storesMandateData": False,
            "sharesRuntimeLogsAsPersistentContext": False,
            "sharesRawToolOutputAsPersistentContext": False,
        },
    }


def load_batch_run_envelope(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"batch run envelope must be a JSON object: {path}")
    return payload


def validate_batch_run_envelope(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    _require_nonempty_string(payload, "session_id", errors)
    _require_nonempty_string(payload, "objective", errors)
    time_budget = payload.get("time_budget_hours")
    if not isinstance(time_budget, int) or time_budget < 1 or time_budget > 5:
        errors.append("time_budget_hours must be an integer between 1 and 5")

    source = _dict(payload.get("source"))
    if not source.get("explicit_offline_owner_request") and not source.get("github_issue"):
        errors.append("source must include explicit_offline_owner_request=true or github_issue")

    errors.extend(_validate_context_load_plan(_dict(payload.get("context_load_plan"))))
    errors.extend(_validate_lanes(payload.get("lanes")))
    errors.extend(_validate_subagent_review(_dict(payload.get("subagent_review"))))
    errors.extend(_validate_command_risk_matrix(payload.get("command_risk_matrix")))
    errors.extend(_validate_stop_lines(payload.get("stop_lines")))
    errors.extend(_validate_validator_matrix(payload.get("validator_matrix")))
    errors.extend(_validate_owner_gates(payload.get("owner_gates")))
    errors.extend(_validate_privacy(_dict(payload.get("privacy"))))
    return errors


def batch_run_envelope_status(payload: dict[str, Any]) -> dict[str, Any]:
    errors = validate_batch_run_envelope(payload)
    lanes = payload.get("lanes") if isinstance(payload.get("lanes"), list) else []
    return {
        "schema_version": "nac.codex-5h-batch-run-envelope-status/v0.1",
        "status": "PASSED" if not errors else "BLOCKED",
        "generated_at": _now(),
        "summary": {
            "session_id": payload.get("session_id"),
            "objective": payload.get("objective"),
            "time_budget_hours": payload.get("time_budget_hours"),
            "lane_count": len(lanes),
            "worktree_isolated_lane_count": sum(
                1 for lane in lanes if isinstance(lane, dict) and lane.get("worktree_required") is True
            ),
            "owner_gate_count": len(payload.get("owner_gates") or []),
            "executes_live_tenant_actions": False,
            "stores_tokens_or_secrets": False,
            "stores_mandate_data": False,
        },
        "errors": errors,
        "privacy": {
            "storesTokensOrSecrets": False,
            "storesMandateData": False,
            "sharesRuntimeLogsAsPersistentContext": False,
            "sharesRawToolOutputAsPersistentContext": False,
        },
    }


def format_batch_run_envelope_status(status: dict[str, Any]) -> str:
    summary = _dict(status.get("summary"))
    lines = [
        "# Codex 5h Batch Run Envelope",
        "",
        f"- Status: `{status.get('status')}`",
        f"- Session: `{summary.get('session_id')}`",
        f"- Objective: {summary.get('objective')}",
        f"- Time budget: `{summary.get('time_budget_hours')}` hours",
        f"- Lanes: `{summary.get('lane_count')}`",
        f"- Worktree-isolated lanes: `{summary.get('worktree_isolated_lane_count')}`",
        f"- Owner gates: `{summary.get('owner_gate_count')}`",
        f"- Live tenant actions: `{summary.get('executes_live_tenant_actions')}`",
        "",
    ]
    errors = status.get("errors") if isinstance(status.get("errors"), list) else []
    if errors:
        lines.append("## Errors")
        lines.extend(f"- {error}" for error in errors)
        lines.append("")
    return "\n".join(lines)


def _validate_context_load_plan(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_CONTEXT_LAYERS - set(plan)
    for layer in sorted(missing):
        errors.append(f"context_load_plan missing layer {layer}")
    for layer in REQUIRED_CONTEXT_LAYERS:
        if layer in plan and not _strings(plan.get(layer)):
            errors.append(f"context_load_plan.{layer} must not be empty")
    shared_context = json.dumps(plan, ensure_ascii=False).lower()
    for marker in PROHIBITED_SHARED_CONTEXT_MARKERS:
        if marker.lower() in shared_context and marker not in _strings(plan.get("shared_context_excludes")):
            errors.append(f"context_load_plan must exclude prohibited shared context marker {marker}")
    return errors


def _validate_lanes(raw_lanes: object) -> list[str]:
    if not isinstance(raw_lanes, list) or not raw_lanes:
        return ["lanes must be a non-empty list"]
    errors: list[str] = []
    seen_scopes: dict[str, str] = {}
    writable_lane_count = 0
    for index, lane in enumerate(raw_lanes):
        if not isinstance(lane, dict):
            errors.append(f"lanes[{index}] must be an object")
            continue
        lane_id = str(lane.get("id") or f"lane-{index}")
        write_scope = _strings(lane.get("write_scope"))
        if write_scope:
            writable_lane_count += 1
            if lane.get("worktree_required") is not True:
                errors.append(f"{lane_id} with write_scope must set worktree_required=true")
            if not str(lane.get("worktree_path") or "").strip():
                errors.append(f"{lane_id} with write_scope must set worktree_path")
        for scope in write_scope:
            if scope in seen_scopes:
                errors.append(f"write scope {scope!r} used by both {seen_scopes[scope]} and {lane_id}")
            seen_scopes[scope] = lane_id
    if writable_lane_count > 1:
        worktree_paths = [
            str(lane.get("worktree_path") or "")
            for lane in raw_lanes
            if isinstance(lane, dict) and _strings(lane.get("write_scope"))
        ]
        if len(set(worktree_paths)) != len(worktree_paths):
            errors.append("parallel writable lanes must use distinct worktree_path values")
    return errors


def _validate_subagent_review(review: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    count = review.get("independent_review_questions_count")
    if not isinstance(count, int) or count < 0:
        errors.append("subagent_review.independent_review_questions_count must be a non-negative integer")
        return errors
    subagent_plan = review.get("subagent_plan")
    no_split_reason = str(review.get("no_split_reason") or "").strip()
    if count >= 2:
        if isinstance(subagent_plan, list) and subagent_plan:
            for index, item in enumerate(subagent_plan):
                if not isinstance(item, dict):
                    errors.append(f"subagent_review.subagent_plan[{index}] must be an object")
                elif item.get("read_only") is not True and not item.get("worktree_path"):
                    errors.append(
                        f"subagent_review.subagent_plan[{index}] must be read_only or own a worktree_path"
                    )
        elif not no_split_reason:
            errors.append("two or more independent review questions require subagent_plan or no_split_reason")
    return errors


def _validate_command_risk_matrix(raw_matrix: object) -> list[str]:
    if not isinstance(raw_matrix, list) or not raw_matrix:
        return ["command_risk_matrix must be a non-empty list"]
    errors: list[str] = []
    for index, item in enumerate(raw_matrix):
        if not isinstance(item, dict):
            errors.append(f"command_risk_matrix[{index}] must be an object")
            continue
        risk = item.get("risk")
        decision = item.get("decision")
        command = str(item.get("command") or "").strip()
        if risk not in {"GREEN", "YELLOW", "RED"}:
            errors.append(f"command_risk_matrix[{index}].risk must be GREEN, YELLOW or RED")
        if not command:
            errors.append(f"command_risk_matrix[{index}].command is required")
        if risk == "RED":
            errors.append(f"RED command is prohibited in a 5h batch envelope: {command}")
        if risk == "YELLOW" and decision not in {"owner_gate", "approved_batch_envelope"}:
            errors.append(f"YELLOW command requires owner_gate or approved_batch_envelope: {command}")
        if risk == "GREEN" and decision != "allow":
            errors.append(f"GREEN command must be allow: {command}")
    return errors


def _validate_stop_lines(raw_stop_lines: object) -> list[str]:
    stop_lines = set(_strings(raw_stop_lines))
    errors = [f"stop_lines missing {item}" for item in sorted(REQUIRED_STOP_LINES - stop_lines)]
    if not stop_lines:
        errors.append("stop_lines must not be empty")
    return errors


def _validate_validator_matrix(raw_validators: object) -> list[str]:
    validators = _strings(raw_validators)
    errors: list[str] = []
    if not validators:
        return ["validator_matrix must not be empty"]
    required = {
        "python3 scripts/validate_codex_5h_batch_run_envelope.py",
        "python3 scripts/nac.py contracts verify",
        "python3 scripts/quality_gate.py --profile strict",
    }
    for item in sorted(required - set(validators)):
        errors.append(f"validator_matrix missing {item}")
    return errors


def _validate_owner_gates(raw_owner_gates: object) -> list[str]:
    owner_gates = " ".join(_strings(raw_owner_gates)).lower()
    errors: list[str] = []
    for marker in ("merge", "live", "secret", "destructive"):
        if marker not in owner_gates:
            errors.append(f"owner_gates must mention {marker}")
    return errors


def _validate_privacy(privacy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in (
        "storesTokensOrSecrets",
        "storesMandateData",
        "sharesRuntimeLogsAsPersistentContext",
        "sharesRawToolOutputAsPersistentContext",
    ):
        if privacy.get(key) is not False:
            errors.append(f"privacy.{key} must be false")
    return errors


def _require_nonempty_string(payload: dict[str, Any], key: str, errors: list[str]) -> None:
    if not str(payload.get(key) or "").strip():
        errors.append(f"{key} is required")


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
