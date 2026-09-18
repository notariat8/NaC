from __future__ import annotations

from pathlib import Path

try:
    from scripts import validate_governance_sync
except ModuleNotFoundError:  # Direct script execution from the repository root.
    import validate_governance_sync


REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_AGENT_MARKERS = (
    "`gh` ist optional",
    "Frühere, einmalige, abgebrochene oder in einem anderen Task erteilte Login-Freigaben sind nicht wiederverwendbar",
    "Ein pauschales `Login jetzt` darf niemals GitHub- und Microsoft-/Entra-Anmeldung gemeinsam autorisieren",
    "Werte werden niemals gelesen, ausgegeben, kopiert, gehasht oder persistiert",
    "Der read-only Issue-/PR-Abgleich und die Reconciliation dürfen keinen GitHub-Gerätecode und keinen Funktion8-/Entra-Browserlogin anfordern",
    "Ausschließlich die final-HEAD-, PR-#747-, Check-, Resolver-, Principal- und `OWNER_SOLO_APPROVAL`-gebundene Read-only-Reconciliation",
)

EXPECTED_POLICY = {
    "preferred_read_only_channel": "github_mcp_connector",
    "gh_optional": True,
    "missing_gh_auth_is_not_github_outage": True,
    "require_exact_current_task_login_authorization": True,
    "prior_login_authorization_reusable": False,
    "combined_provider_login_authorization_allowed": False,
    "automatic_device_code_login_allowed": False,
    "token_value_inspection_allowed": False,
    "git_credential_to_api_token_conversion_allowed": False,
    "issue_746_windows_interactive_authentication_allowed": False,
    "issue_746_windows_read_only_reconciliation_allowed_after_bound_gate": True,
    "issue_746_windows_live_access_allowed": False,
    "issue_746_windows_recovery_access_allowed": False,
    "issue_746_windows_provider_write_allowed": False,
    "issue_746_windows_tenant_write_allowed": False,
    "issue_746_windows_credential_mutation_allowed": False,
    "issue_746_windows_automatic_retry_allowed": False,
    "unsupported_read_capability_action": "report_exact_capability_gap",
}

REQUIRED_ISSUE_746_MARKERS = (
    "The controller uses only an already established authentication context",
    "Login, device code,\nbrowser authentication, token refresh, cache creation, or configuration rewrite\nblocks reconciliation",
    "There is no\nprovider, tenant, credential, or live access",
)


def validate(root: Path = REPO_ROOT) -> list[str]:
    errors: list[str] = []

    agents_text = (root / "AGENTS.md").read_text(encoding="utf-8")
    for marker in REQUIRED_AGENT_MARKERS:
        if marker not in agents_text:
            errors.append(f"AGENTS.md missing authentication marker: {marker}")

    process_policy = validate_governance_sync.load_simple_yaml_mapping(
        root / "policies" / "process-policy.yaml"
    )
    boundary = process_policy.get("github_authentication_boundary")
    if not isinstance(boundary, dict):
        errors.append("process-policy github_authentication_boundary must be a mapping")
    else:
        for key, expected in EXPECTED_POLICY.items():
            if boundary.get(key) != expected:
                errors.append(
                    "process-policy github_authentication_boundary."
                    f"{key} must equal {expected!r}"
                )
        enforced_by = boundary.get("enforced_by")
        if enforced_by != ["scripts/validate_agent_authentication_boundary.py"]:
            errors.append(
                "process-policy github_authentication_boundary.enforced_by must bind the validator"
            )

    issue_746_spec = (
        root
        / "docs"
        / "en"
        / "superpowers"
        / "specs"
        / "2026-09-15-m365-bff-failed-partial-safe-completion-design.md"
    ).read_text(encoding="utf-8")
    for marker in REQUIRED_ISSUE_746_MARKERS:
        if marker not in issue_746_spec:
            errors.append(f"Issue #746 safe-completion spec missing marker: {marker}")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: NaC agent authentication boundary is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
