from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

POLICY_FILES = {
    "policies/process-policy.yaml",
    "policies/role-model-policy.yaml",
    "policies/github-identity-registry.json",
    "policies/access-control-policy.yaml",
    "policies/revisionssicherheit-eventstream-policy.yaml",
    "policies/tenant-ownership-policy.yaml",
    "policies/provider-open-services-policy.yaml",
    "policies/language-policy.yaml",
    "policies/license-policy.yaml",
    "policies/data-protection-policy.yaml",
    "policies/sbom-policy.yaml",
    "policies/technology-policy.yaml",
    "policies/codex-command-rules-policy.json",
    "policies/platform-policy.yaml",
}

MIRROR_FILES = {
    "AGENTS.md",
}

MIRROR_PREFIXES = (".codex/agents/", ".pi/agents/")

MANDATORY_ACCESS_POLICY_KEYS = (
    "source_of_truth:",
    "repository_model:",
    "organization_project:",
    "guest_access_rules:",
    "change_control:",
)

MANDATORY_LANGUAGE_POLICY_KEYS = (
    "standard_languages:",
    "- de",
    "- en",
    "language_code_standard:",
    "localized_surfaces:",
    "require_all_standard_languages:",
)

MANDATORY_PROCESS_POLICY_KEYS = (
    "delivery_modes:",
    "github_first_operating_model:",
    "agent_workflows:",
    "protected_pr:",
    "owner_direct_main:",
    "rule_architecture:",
    "human_explanation_de: docs/de/regelarchitektur.md",
    "human_explanation_en: docs/en/regelarchitektur.md",
)

EXPECTED_GITHUB_FIRST_SCALARS = {
    "project_owner": "notariat8",
    "project_title": "NaC Control Plane",
    "project_scope": "organization",
}

EXPECTED_GITHUB_FIRST_TRUE_KEYS = (
    "project_required_for_nontrivial_work",
    "require_leading_issue_for_nontrivial_work",
    "require_project_fields_for_nontrivial_work",
    "allow_owner_direct_with_issue_project_trail",
    "completion_requires_remote_ci_checks",
    "forbid_secrets_and_matter_data_in_github_surfaces",
)

EXPECTED_GITHUB_FIRST_LISTS = {
    "required_project_fields": (
        "Status",
        "Track",
        "Work Type",
        "Risk Gate",
        "Delivery Mode",
        "Priority",
        "Size",
        "Iteration",
        "Due Date",
    ),
    "required_statuses": (
        "Inbox",
        "Ready",
        "In Progress",
        "Review",
        "Blocked",
        "Done",
    ),
    "required_views": (
        "Owner Board",
        "Now",
        "Blocked",
        "Governance And Security",
        "Release Readiness",
        "My Agent Work",
    ),
    "delivery_modes": (
        "Owner Direct",
        "Protected PR",
        "Sync PR",
    ),
}

EXPECTED_GITHUB_FIRST_BRANCH_PREFIXES = {
    "agent": "agent/<issue-number>-<short-slug>",
    "sync": "sync/<issue-number>-<short-slug>",
    "hotfix": "hotfix/<issue-number>-<short-slug>",
}

EXPECTED_AGENT_WORKFLOW_TRUE_KEYS = (
    "require_plan_review_fix_for_nontrivial_work",
    "require_implementation_review_before_user_acceptance",
    "require_final_response_next_step",
    "require_diagnosis_before_fix_for_repeated_or_unclear_failures",
    "require_full_pr_diff_review_before_merge",
    "routine_read_only_github_oci_checks_do_not_need_owner_approval",
    "parallel_gate_preparation_required_when_independent_inputs_known",
    "prohibit_finished_with_agent_executable_next_step",
    "require_continue_when_no_owner_input_needed",
    "require_concrete_blocker_when_owner_input_needed",
    "codex_parallel_review_default_when_net_benefit_expected",
    "require_layer_sync_check_for_data_controller_view_changes",
    "require_error_test_security_review_for_code_reviewer",
)

EXPECTED_FINAL_RESPONSE_NEXT_STEP_TRUE_KEYS = (
    "required_even_when_work_is_complete",
    "must_state_owner_input_needed_or_not_needed",
    "must_name_concrete_next_engineering_or_operational_step",
    "must_not_end_with_ambiguous_waiting_state",
    "no_owner_input_needed_means_continue_not_wait",
    "finished_requires_no_agent_executable_next_step",
    "owner_input_needed_requires_actionable_request",
)

EXPECTED_PERSISTENT_OWNER_WORKING_AGREEMENT_TRUE_KEYS = (
    "enabled",
    "applies_across_turns_sessions_and_context_transitions",
    "active_after_repo_rule_surfaces_are_read",
    "owner_can_replace_or_revoke_explicitly",
    "pre_final_check_required",
    "prohibit_passive_closure_when_tools_available",
    "require_batch_owner_approval_for_repeated_gate_chains",
    "mirror_required_in_agents_md_and_codex_profiles",
)

EXPECTED_PRE_FINAL_CHECK_QUESTIONS = (
    "agent_executable_next_step_without_owner_input",
    "concrete_owner_gate_only",
    "no_agent_executable_continuation_remaining",
)

PERSISTENT_OWNER_MIRROR_EXPECTATIONS = {
    "AGENTS.md": (
        "Persistente Owner-Arbeitsvereinbarung",
        "turn-, session- und kontextwechselübergreifend",
        "Pre-Final-Check",
        "agentisch ausführbaren Schritt ohne Owner-Input",
        "genau ein konkreter kopierbarer Freigabetext",
        "Batch-/One-Shot-Freigabe",
    ),
    ".codex/agents/nac-scope-mapper.toml": (
        "persistent owner working agreement",
        "pre-final check",
        "agent-executable next step without owner input",
        "continue the work",
        "single concrete owner-gate approval text",
    ),
    ".codex/agents/nac-policy-reviewer.toml": (
        "persistent owner working agreement",
        "pre-final check",
        "agent-executable next step without owner input",
        "single concrete owner-gate approval text",
    ),
    ".codex/agents/nac-validation-reviewer.toml": (
        "persistent owner working agreement",
        "pre-final check",
        "agent-executable next step without owner input",
        "validation or branch cleanup",
    ),
    ".codex/agents/nac-docs-parity-reviewer.toml": (
        "persistent owner working agreement",
        "pre-final check",
        "German and English",
        "agent-executable next step without owner input",
    ),
    ".codex/agents/nac-kg-reviewer.toml": (
        "persistent owner working agreement",
        "pre-final check",
        "agent-executable next step without owner input",
        "single concrete owner-gate approval text",
    ),
    ".codex/agents/nac-bpmn-reviewer.toml": (
        "persistent owner working agreement",
        "pre-final check",
        "agent-executable next step without owner input",
        "single concrete owner-gate approval text",
    ),
}

EXPECTED_GITHUB_SURFACES = (
    "issues",
    "pull_requests",
    "projects",
    "project_fields",
    "comments",
)


def strip_yaml_inline_comment(value: str) -> str:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\" and quote == '"':
            escaped = True
            continue
        if char in {'"', "'"}:
            if quote == char:
                quote = None
            elif quote is None:
                quote = char
            continue
        if char == "#" and quote is None and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
    return value


def parse_simple_yaml_scalar(value: str) -> object:
    value = strip_yaml_inline_comment(value).strip()
    if value in {"true", "false"}:
        return value == "true"
    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {'"', "'"}
    ):
        return value[1:-1]
    return value


def parse_simple_yaml_block(
    lines: list[tuple[int, str]], index: int, indent: int
) -> tuple[object, int]:
    if index >= len(lines):
        return {}, index

    if lines[index][1].startswith("- "):
        items: list[object] = []
        while index < len(lines):
            line_indent, content = lines[index]
            if line_indent != indent or not content.startswith("- "):
                break
            items.append(parse_simple_yaml_scalar(content[2:]))
            index += 1
        return items, index

    mapping: dict[str, object] = {}
    while index < len(lines):
        line_indent, content = lines[index]
        if line_indent < indent:
            break
        if line_indent > indent:
            index += 1
            continue
        if content.startswith("- "):
            break
        if ":" not in content:
            index += 1
            continue

        key, value = content.split(":", 1)
        key = key.strip()
        value = strip_yaml_inline_comment(value).strip()
        index += 1
        if value:
            mapping[key] = parse_simple_yaml_scalar(value)
            continue

        if index < len(lines) and lines[index][0] > line_indent:
            child, index = parse_simple_yaml_block(lines, index, lines[index][0])
            mapping[key] = child
        else:
            mapping[key] = {}

    return mapping, index


def load_simple_yaml_mapping(path: Path) -> dict[str, object]:
    lines: list[tuple[int, str]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        lines.append((indent, raw_line.strip()))

    parsed, _ = parse_simple_yaml_block(lines, 0, lines[0][0] if lines else 0)
    if isinstance(parsed, dict):
        return parsed
    return {}


def validate_required_list(
    *,
    errors: list[str],
    policy_name: str,
    section_name: str,
    key: str,
    actual: object,
    expected_values: tuple[str, ...],
) -> None:
    if not isinstance(actual, list):
        errors.append(f"Pflichtabschnitt fehlt in {policy_name}: {section_name}.{key}")
        return

    for expected in expected_values:
        if expected not in actual:
            errors.append(
                f"Pflichtwert fehlt in {policy_name}: {section_name}.{key}.{expected}"
            )


def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def changed_files() -> list[str]:
    base_ref = os.environ.get("GITHUB_BASE_REF")
    if base_ref:
        run_git(["fetch", "--no-tags", "origin", base_ref])
        diff = run_git(["diff", "--name-only", f"origin/{base_ref}...HEAD"])
    else:
        diff = run_git(["diff", "--name-only", "HEAD"])

    if diff.returncode != 0:
        print("ERROR: Konnte geänderte Dateien nicht bestimmen.")
        print(diff.stderr.strip())
        return []

    untracked = run_git(["ls-files", "--others", "--exclude-standard"])
    if untracked.returncode != 0:
        print("ERROR: Konnte ungetrackte Dateien nicht bestimmen.")
        print(untracked.stderr.strip())
        return []

    files = {
        line.strip()
        for output in (diff.stdout, untracked.stdout)
        for line in output.splitlines()
        if line.strip()
    }
    return sorted(files)


def is_policy_file(path: str) -> bool:
    return path in POLICY_FILES


def is_mirror_file(path: str) -> bool:
    return path in MIRROR_FILES or any(path.startswith(prefix) for prefix in MIRROR_PREFIXES)


def validate_access_policy_file() -> list[str]:
    errors: list[str] = []
    policy_path = REPO_ROOT / "policies" / "access-control-policy.yaml"
    if not policy_path.exists():
        errors.append("Pflichtdatei fehlt: policies/access-control-policy.yaml")
        return errors

    text = policy_path.read_text(encoding="utf-8")
    for key in MANDATORY_ACCESS_POLICY_KEYS:
        if key not in text:
            errors.append(f"Pflichtabschnitt fehlt in access-control-policy: {key}")
    return errors


def validate_language_policy_file() -> list[str]:
    errors: list[str] = []
    policy_path = REPO_ROOT / "policies" / "language-policy.yaml"
    if not policy_path.exists():
        errors.append("Pflichtdatei fehlt: policies/language-policy.yaml")
        return errors

    text = policy_path.read_text(encoding="utf-8")
    for key in MANDATORY_LANGUAGE_POLICY_KEYS:
        if key not in text:
            errors.append(f"Pflichtabschnitt fehlt in language-policy: {key}")
    return errors


def validate_process_policy_file() -> list[str]:
    errors: list[str] = []
    policy_path = REPO_ROOT / "policies" / "process-policy.yaml"
    if not policy_path.exists():
        errors.append("Pflichtdatei fehlt: policies/process-policy.yaml")
        return errors

    text = policy_path.read_text(encoding="utf-8")
    for key in MANDATORY_PROCESS_POLICY_KEYS:
        if key not in text:
            errors.append(f"Pflichtabschnitt fehlt in process-policy: {key}")

    policy = load_simple_yaml_mapping(policy_path)
    model = policy.get("github_first_operating_model")
    if not isinstance(model, dict):
        errors.append(
            "Pflichtabschnitt fehlt in process-policy: "
            "github_first_operating_model must be a mapping"
        )
    else:
        for key, expected in EXPECTED_GITHUB_FIRST_SCALARS.items():
            if model.get(key) != expected:
                errors.append(
                    "Pflichtwert fehlt in process-policy: "
                    f"github_first_operating_model.{key}.{expected}"
                )

        for key in EXPECTED_GITHUB_FIRST_TRUE_KEYS:
            if model.get(key) is not True:
                errors.append(
                    "Pflichtwert fehlt in process-policy: "
                    f"github_first_operating_model.{key}.true"
                )

        for key, expected_values in EXPECTED_GITHUB_FIRST_LISTS.items():
            validate_required_list(
                errors=errors,
                policy_name="process-policy",
                section_name="github_first_operating_model",
                key=key,
                actual=model.get(key),
                expected_values=expected_values,
            )

        branch_prefixes = model.get("branch_prefixes")
        if not isinstance(branch_prefixes, dict):
            errors.append(
                "Pflichtabschnitt fehlt in process-policy: "
                "github_first_operating_model.branch_prefixes"
            )
        else:
            for key, expected in EXPECTED_GITHUB_FIRST_BRANCH_PREFIXES.items():
                if branch_prefixes.get(key) != expected:
                    errors.append(
                        "Pflichtwert fehlt in process-policy: "
                        f"github_first_operating_model.branch_prefixes.{key}"
                    )

    agent_workflows = policy.get("agent_workflows")
    if not isinstance(agent_workflows, dict):
        errors.append(
            "Pflichtabschnitt fehlt in process-policy: "
            "agent_workflows must be a mapping"
        )
    else:
        for key in EXPECTED_AGENT_WORKFLOW_TRUE_KEYS:
            if agent_workflows.get(key) is not True:
                errors.append(
                    "Pflichtwert fehlt in process-policy: "
                    f"agent_workflows.{key}.true"
                )
        validate_required_list(
            errors=errors,
            policy_name="process-policy",
            section_name="agent_workflows",
            key="codex_parallel_review_assessment_dimensions",
            actual=agent_workflows.get("codex_parallel_review_assessment_dimensions"),
            expected_values=(
                "layer_count",
                "risk_level",
                "independent_review_perspectives",
                "validation_surface",
                "coordination_cost",
            ),
        )
        validate_required_list(
            errors=errors,
            policy_name="process-policy",
            section_name="agent_workflows",
            key="codex_parallel_review_preserve_single_owner_for",
            actual=agent_workflows.get("codex_parallel_review_preserve_single_owner_for"),
            expected_values=(
                "secrets",
                "oci_write_actions",
                "apply_gates",
                "release_gates",
                "destructive_operations",
            ),
        )
        final_response_next_step = agent_workflows.get("final_response_next_step")
        if not isinstance(final_response_next_step, dict):
            errors.append(
                "Pflichtabschnitt fehlt in process-policy: "
                "agent_workflows.final_response_next_step"
            )
        else:
            for key in EXPECTED_FINAL_RESPONSE_NEXT_STEP_TRUE_KEYS:
                if final_response_next_step.get(key) is not True:
                    errors.append(
                        "Pflichtwert fehlt in process-policy: "
                        f"agent_workflows.final_response_next_step.{key}.true"
                    )
        persistent_owner_working_agreement = agent_workflows.get(
            "persistent_owner_working_agreement"
        )
        if not isinstance(persistent_owner_working_agreement, dict):
            errors.append(
                "Pflichtabschnitt fehlt in process-policy: "
                "agent_workflows.persistent_owner_working_agreement"
            )
        else:
            for key in EXPECTED_PERSISTENT_OWNER_WORKING_AGREEMENT_TRUE_KEYS:
                if persistent_owner_working_agreement.get(key) is not True:
                    errors.append(
                        "Pflichtwert fehlt in process-policy: "
                        f"agent_workflows.persistent_owner_working_agreement.{key}.true"
                    )
            validate_required_list(
                errors=errors,
                policy_name="process-policy",
                section_name="agent_workflows.persistent_owner_working_agreement",
                key="pre_final_check_questions",
                actual=persistent_owner_working_agreement.get("pre_final_check_questions"),
                expected_values=EXPECTED_PRE_FINAL_CHECK_QUESTIONS,
            )

    for rel_path in ("docs/de/regelarchitektur.md", "docs/en/regelarchitektur.md"):
        if not (REPO_ROOT / rel_path).exists():
            errors.append(f"Pflichtdokument zur Regelarchitektur fehlt: {rel_path}")
    return errors


def validate_persistent_owner_working_agreement_mirrors() -> list[str]:
    errors: list[str] = []
    for rel_path, expected_fragments in PERSISTENT_OWNER_MIRROR_EXPECTATIONS.items():
        path = REPO_ROOT / rel_path
        if not path.exists():
            errors.append(f"Pflichtspiegel fehlt: {rel_path}")
            continue
        text = " ".join(path.read_text(encoding="utf-8").split())
        for fragment in expected_fragments:
            if fragment not in text:
                errors.append(
                    "Pflichtspiegel fehlt in "
                    f"{rel_path}: persistent_owner_working_agreement.{fragment}"
                )
    return errors


def validate_data_protection_policy_file() -> list[str]:
    errors: list[str] = []
    policy_path = REPO_ROOT / "policies" / "data-protection-policy.yaml"
    if not policy_path.exists():
        errors.append("Pflichtdatei fehlt: policies/data-protection-policy.yaml")
        return errors

    policy = load_simple_yaml_mapping(policy_path)
    github_surfaces = policy.get("github_surfaces")
    if not isinstance(github_surfaces, dict):
        errors.append(
            "Pflichtabschnitt fehlt in data-protection-policy: github_surfaces"
        )
        return errors

    if github_surfaces.get("forbid_secrets_and_matter_data") is not True:
        errors.append(
            "Pflichtwert fehlt in data-protection-policy: "
            "github_surfaces.forbid_secrets_and_matter_data.true"
        )

    validate_required_list(
        errors=errors,
        policy_name="data-protection-policy",
        section_name="github_surfaces",
        key="applies_to",
        actual=github_surfaces.get("applies_to"),
        expected_values=EXPECTED_GITHUB_SURFACES,
    )
    return errors


def main() -> int:
    files = changed_files()
    if not files:
        print("INFO: Keine geänderten Dateien erkannt oder nur nicht relevante Änderungen.")
        return 0

    policy_changed = any(is_policy_file(path) for path in files)
    mirror_changed = any(is_mirror_file(path) for path in files)

    errors = validate_access_policy_file()
    errors.extend(validate_language_policy_file())
    errors.extend(validate_process_policy_file())
    errors.extend(validate_data_protection_policy_file())
    errors.extend(validate_persistent_owner_working_agreement_mirrors())

    if mirror_changed and not policy_changed:
        errors.append(
            "Änderung an AI-Regelflächen ohne Policy-Änderung erkannt. "
            "Bitte zuerst Policies unter policies/ ändern und Spiegel synchronisieren."
        )

    if policy_changed and not mirror_changed:
        errors.append(
            "Policy-Änderung ohne Spiegel-Aktualisierung erkannt. "
            "Bitte AGENTS.md und .codex/agents als Codex-Agentenspiegel synchronisieren."
        )

    if errors:
        print("STATUS: FAILED")
        for entry in errors:
            print(f"ERROR: {entry}")
        return 1

    print("STATUS: PASSED")
    print("OK: Governance-Sync-Regeln eingehalten.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
