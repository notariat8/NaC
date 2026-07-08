from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY = REPO_ROOT / "policies" / "codex-command-rules-policy.json"
RULES_FILE = REPO_ROOT / ".codex" / "rules" / "default.rules"
CODEX_CONFIG = REPO_ROOT / ".codex" / "config.toml"
AGENT_CONTEXT = REPO_ROOT / "agent-context" / "index.json"
VERIFICATION_CONTRACT = REPO_ROOT / "workflows" / "verification-contracts" / "codex-command-rules.verification.json"
DOC_DE = REPO_ROOT / "docs" / "de" / "operations" / "codex-command-rules-operating-model.md"
DOC_EN = REPO_ROOT / "docs" / "en" / "operations" / "codex-command-rules-operating-model.md"
CODEOWNERS = REPO_ROOT / "CODEOWNERS"

REQUIRED_RISKS = {"GREEN": "allow", "YELLOW": "prompt", "RED": "block"}
REQUIRED_PROFILES = {
    "green_read_only_repository_status",
    "green_local_validation",
    "yellow_pr_preparation",
    "yellow_owner_merge_cleanup",
    "yellow_owner_gated_live_smoke",
    "red_destructive_git_and_filesystem",
    "red_secret_credential_certificate_and_productive_apply",
}
REQUIRED_RED_PREFIXES = {
    ("git", "reset", "--hard"),
    ("git", "checkout", "--"),
    ("rm", "-rf"),
    ("az", "ad", "app", "credential"),
    ("terraform", "apply"),
}
REQUIRED_YELLOW_PREFIXES = {
    ("git", "push"),
    ("gh", "pr", "create"),
    ("gh", "pr", "merge"),
    ("git", "branch", "-d"),
    ("python3", "scripts/nac.py", "m365", "teams-sharepoint", "release-gate-run"),
}
REQUIRED_GREEN_PREFIXES = {
    ("git", "status"),
    ("git", "diff"),
    ("gh", "pr", "view"),
    ("gh", "pr", "checks"),
    ("python3", "scripts/quality_gate.py"),
    ("python3", "scripts/validate_codex_command_rules_operating_model.py"),
}
PROHIBITED_MARKERS = {
    "client" + "_secret",
    "BEGIN " + "PRIVATE KEY",
    "BEGIN " + "CERTIFICATE",
    "gh" + "p_",
    "gh" + "o_",
    "real_mandate_data_sample",
    "password=",
}


def main() -> int:
    errors = validate()
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("STATUS: PASSED")
    print("OK: Codex command rules operating model has GREEN/YELLOW/RED profiles, repo rules and validator coverage.")
    return 0


def validate() -> list[str]:
    errors: list[str] = []
    policy = _read_json(POLICY, errors)
    verification = _read_json(VERIFICATION_CONTRACT, errors)
    context = _read_json(AGENT_CONTEXT, errors)
    rules = _read_rules(RULES_FILE, errors)

    if policy:
        errors.extend(_validate_policy(policy))
    if rules:
        errors.extend(_validate_rules_file(rules))
    if policy and rules:
        errors.extend(_validate_policy_rules_crosswalk(policy, rules))
    if verification:
        errors.extend(_validate_verification_contract(verification))
    if context:
        errors.extend(_validate_agent_context(context))
    errors.extend(_validate_docs_and_codeowners())
    return errors


def _validate_policy(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "nac.codex-command-rules-policy/v0.1":
        errors.append("codex-command-rules-policy.json has wrong schema_version")
    if payload.get("source_rule_file") != ".codex/rules/default.rules":
        errors.append("codex-command-rules-policy.json must point to .codex/rules/default.rules")
    if payload.get("local_user_config_mutation_allowed_by_repo") is not False:
        errors.append("policy must not allow repo-driven local user config mutation")

    risk_decisions = {
        str(item.get("id")): item.get("decision")
        for item in payload.get("risk_levels", [])
        if isinstance(item, dict)
    }
    for risk, decision in REQUIRED_RISKS.items():
        if risk_decisions.get(risk) != decision:
            errors.append(f"risk level {risk} must map to decision {decision}")

    profiles = payload.get("permission_profiles")
    if not isinstance(profiles, list):
        return errors + ["permission_profiles must be a list"]
    by_id = {str(item.get("id")): item for item in profiles if isinstance(item, dict)}
    for profile_id in sorted(REQUIRED_PROFILES - set(by_id)):
        errors.append(f"missing permission profile {profile_id}")

    counters = {"GREEN": 0, "YELLOW": 0, "RED": 0}
    all_prefixes: dict[tuple[str, ...], str] = {}
    for profile_id, profile in by_id.items():
        risk = str(profile.get("risk"))
        decision = profile.get("decision")
        if risk not in REQUIRED_RISKS:
            errors.append(f"{profile_id} has unknown risk {risk}")
            continue
        if decision != REQUIRED_RISKS[risk]:
            errors.append(f"{profile_id} decision must be {REQUIRED_RISKS[risk]}")
        commands = profile.get("commands")
        if not isinstance(commands, list) or not commands:
            errors.append(f"{profile_id} must list commands")
            continue
        for command in commands:
            if not isinstance(command, dict):
                errors.append(f"{profile_id} command must be an object")
                continue
            prefix = tuple(_strings(command.get("prefix")))
            if not prefix:
                errors.append(f"{profile_id} command prefix is empty")
                continue
            counters[risk] += 1
            if prefix in all_prefixes:
                errors.append(f"duplicate command prefix {prefix} in {profile_id} and {all_prefixes[prefix]}")
            all_prefixes[prefix] = profile_id
            if not str(command.get("justification", "")).strip():
                errors.append(f"{profile_id} command {prefix} needs justification")
            errors.extend(_validate_prefix_risk(prefix, risk, profile_id))

    thresholds = payload.get("invariants")
    if not isinstance(thresholds, dict):
        errors.append("policy invariants must be an object")
    else:
        for key in (
            "rules_do_not_replace_owner_gates",
            "rules_do_not_expand_filesystem_or_network_access",
            "rules_do_not_store_secrets_or_mandate_data",
            "rules_do_not_activate_hooks",
            "red_profiles_must_block",
            "yellow_profiles_must_prompt_or_require_batch_approval",
            "green_profiles_must_be_read_only_or_local_validation",
        ):
            if thresholds.get(key) is not True:
                errors.append(f"policy invariant {key} must be true")

    for prefix in REQUIRED_GREEN_PREFIXES - set(all_prefixes):
        errors.append(f"missing required GREEN prefix {prefix}")
    for prefix in REQUIRED_YELLOW_PREFIXES - set(all_prefixes):
        errors.append(f"missing required YELLOW prefix {prefix}")
    for prefix in REQUIRED_RED_PREFIXES - set(all_prefixes):
        errors.append(f"missing required RED prefix {prefix}")
    if counters["GREEN"] < 8:
        errors.append("GREEN command count must be at least 8")
    if counters["YELLOW"] < 5:
        errors.append("YELLOW command count must be at least 5")
    if counters["RED"] < 6:
        errors.append("RED command count must be at least 6")
    return errors


def _validate_prefix_risk(prefix: tuple[str, ...], risk: str, profile_id: str) -> list[str]:
    errors: list[str] = []
    joined = " ".join(prefix)
    risky_fragments = ("reset --hard", "checkout --", "rm -rf", "credential", "secret", "password", "terraform apply")
    if risk == "GREEN" and any(fragment in joined for fragment in risky_fragments):
        errors.append(f"{profile_id} cannot mark risky command as GREEN: {joined}")
    if risk == "GREEN" and prefix[:2] in {("gh", "pr"), ("git", "push")} and prefix not in REQUIRED_GREEN_PREFIXES:
        errors.append(f"{profile_id} GREEN command is not read-only enough: {joined}")
    if risk == "RED" and prefix in REQUIRED_GREEN_PREFIXES:
        errors.append(f"{profile_id} cannot block required GREEN command: {joined}")
    return errors


def _validate_rules_file(rules: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    by_prefix = {tuple(_strings(item.get("pattern"))): str(item.get("decision")) for item in rules}
    for prefix in REQUIRED_GREEN_PREFIXES:
        if by_prefix.get(prefix) != "allow":
            errors.append(f"default.rules must allow GREEN prefix {prefix}")
    for prefix in REQUIRED_YELLOW_PREFIXES:
        if by_prefix.get(prefix) != "prompt":
            errors.append(f"default.rules must prompt YELLOW prefix {prefix}")
    for prefix in REQUIRED_RED_PREFIXES:
        if by_prefix.get(prefix) != "block":
            errors.append(f"default.rules must block RED prefix {prefix}")
    for item in rules:
        prefix = tuple(_strings(item.get("pattern")))
        decision = item.get("decision")
        if decision not in {"allow", "prompt", "block"}:
            errors.append(f"default.rules invalid decision for {prefix}: {decision}")
        if not str(item.get("justification", "")).strip():
            errors.append(f"default.rules missing justification for {prefix}")
    return errors


def _validate_policy_rules_crosswalk(policy: dict[str, Any], rules: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    policy_decisions: dict[tuple[str, ...], str] = {}
    for profile in policy.get("permission_profiles", []):
        if not isinstance(profile, dict):
            continue
        decision = str(profile.get("decision"))
        for command in profile.get("commands", []):
            if isinstance(command, dict):
                policy_decisions[tuple(_strings(command.get("prefix")))] = decision
    rule_decisions = {tuple(_strings(item.get("pattern"))): str(item.get("decision")) for item in rules}
    for prefix, decision in policy_decisions.items():
        if prefix in rule_decisions and rule_decisions[prefix] != decision:
            errors.append(f"default.rules decision for {prefix} does not match policy")
    return errors


def _validate_verification_contract(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "nac.verification-contract/v0.1":
        errors.append("codex-command-rules verification contract has wrong schema_version")
    if payload.get("contract_id") != "verification.codex_command_rules":
        errors.append("codex-command-rules verification contract has wrong contract_id")
    for field in ("applies_when", "required_context", "checks", "invariants", "thresholds", "required_evidence", "pass_condition", "failure_behavior"):
        if field not in payload:
            errors.append(f"codex-command-rules verification contract missing {field}")
    thresholds = payload.get("thresholds")
    if isinstance(thresholds, dict):
        if thresholds.get("minimum_green_commands", 0) < 8:
            errors.append("minimum_green_commands must be at least 8")
        if thresholds.get("minimum_yellow_commands", 0) < 5:
            errors.append("minimum_yellow_commands must be at least 5")
        if thresholds.get("minimum_red_commands", 0) < 6:
            errors.append("minimum_red_commands must be at least 6")
    evidence = set(_strings(payload.get("required_evidence")))
    for required in (
        "command_rules_policy",
        "repo_rules_file",
        "command_rules_docs_de",
        "command_rules_docs_en",
        "command_rules_validator",
        "quality_gate_result",
    ):
        if required not in evidence:
            errors.append(f"verification contract required_evidence missing {required}")
    pass_condition = payload.get("pass_condition")
    if isinstance(pass_condition, dict):
        for key in ("red_profiles_block", "yellow_profiles_prompt", "green_profiles_are_safe", "no_secrets", "no_mandate_data", "no_live_hook_activation"):
            if pass_condition.get(key) is not True:
                errors.append(f"verification contract pass_condition.{key} must be true")
    return errors


def _validate_agent_context(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if "workflows/verification-contracts/codex-command-rules.verification.json" not in _strings(
        payload.get("verification_contracts")
    ):
        errors.append("agent-context/index.json must list codex-command-rules verification contract")
    categories: dict[str, list[str]] = {}
    for layer in payload.get("layers", []):
        if not isinstance(layer, dict):
            continue
        for category in layer.get("categories", []):
            if isinstance(category, dict):
                categories[str(category.get("id"))] = _strings(category.get("paths"))
    command_paths = set(categories.get("command_rules", []))
    for rel_path in (
        "policies/codex-command-rules-policy.json",
        ".codex/rules/default.rules",
        "docs/de/operations/codex-command-rules-operating-model.md",
        "docs/en/operations/codex-command-rules-operating-model.md",
    ):
        if rel_path not in command_paths:
            errors.append(f"agent-context command_rules category missing {rel_path}")
    return errors


def _validate_docs_and_codeowners() -> list[str]:
    errors: list[str] = []
    for path in (DOC_DE, DOC_EN, RULES_FILE, POLICY, VERIFICATION_CONTRACT):
        if not path.is_file():
            errors.append(f"missing required file {path.relative_to(REPO_ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in PROHIBITED_MARKERS:
            if marker.lower() in text.lower():
                errors.append(f"{path.relative_to(REPO_ROOT)} contains prohibited marker {marker}")
    for path in (DOC_DE, DOC_EN):
        text = path.read_text(encoding="utf-8")
        for marker in ("GREEN", "YELLOW", "RED", "codex-command-rules-policy.json", "default.rules"):
            if marker not in text:
                errors.append(f"{path.relative_to(REPO_ROOT)} missing marker {marker}")
    config_text = CODEX_CONFIG.read_text(encoding="utf-8") if CODEX_CONFIG.is_file() else ""
    if "[[hooks." in config_text or "[hooks." in config_text:
        errors.append(".codex/config.toml must not activate hooks")
    if "rules" in config_text.lower():
        errors.append(".codex/config.toml must not activate command rules in this offline slice")
    codeowners = CODEOWNERS.read_text(encoding="utf-8") if CODEOWNERS.is_file() else ""
    for pattern in (".codex/rules/*", "policies/codex-command-rules-policy.json"):
        if pattern not in codeowners:
            errors.append(f"CODEOWNERS missing {pattern}")
    return errors


def _read_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"missing JSON file {path.relative_to(REPO_ROOT)}")
        return None
    text = path.read_text(encoding="utf-8")
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in text.lower():
            errors.append(f"{path.relative_to(REPO_ROOT)} contains prohibited marker {marker}")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(f"{path.relative_to(REPO_ROOT)} invalid JSON: {exc}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{path.relative_to(REPO_ROOT)} must be a JSON object")
        return None
    return payload


def _read_rules(path: Path, errors: list[str]) -> list[dict[str, Any]]:
    if not path.is_file():
        errors.append(f"missing rules file {path.relative_to(REPO_ROOT)}")
        return []
    text = path.read_text(encoding="utf-8")
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in text.lower():
            errors.append(f"{path.relative_to(REPO_ROOT)} contains prohibited marker {marker}")
    blocks = re.findall(r"prefix_rule\((.*?)\)", text, flags=re.DOTALL)
    rules: list[dict[str, Any]] = []
    for block in blocks:
        pattern_match = re.search(r"pattern\s*=\s*(\[[^\]]*\])", block, flags=re.DOTALL)
        decision_match = re.search(r"decision\s*=\s*\"([^\"]+)\"", block)
        justification_match = re.search(r"justification\s*=\s*\"([^\"]+)\"", block, flags=re.DOTALL)
        if not pattern_match:
            errors.append("default.rules prefix_rule block missing pattern")
            continue
        try:
            pattern = ast.literal_eval(pattern_match.group(1))
        except (SyntaxError, ValueError) as exc:
            errors.append(f"default.rules invalid pattern: {exc}")
            continue
        rules.append(
            {
                "pattern": pattern,
                "decision": decision_match.group(1) if decision_match else None,
                "justification": justification_match.group(1) if justification_match else "",
            }
        )
    if not rules:
        errors.append("default.rules contains no prefix_rule blocks")
    return rules


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
