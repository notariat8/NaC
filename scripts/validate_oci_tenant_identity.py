from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

src_root_text = str(SRC_ROOT)
if src_root_text in sys.path:
    sys.path.remove(src_root_text)
sys.path.insert(0, src_root_text)

from nac_identity.oci_tenant import build_admin_provisioning_plan, check_domain_ready  # noqa: E402


CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "oci-tenant-identity.contract.json"


def main() -> int:
    errors: list[str] = []
    if not CONTRACT_PATH.exists():
        errors.append("Missing workflows/contracts/oci-tenant-identity.contract.json")
    else:
        _validate_contract(errors)
    _validate_domain_readiness(errors)
    _validate_admin_plan(errors)

    if errors:
        print("OCI tenant identity validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("OCI tenant identity validation passed.")
    return 0


def _validate_contract(errors: list[str]) -> None:
    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "nac.oci-tenant-identity-contract/v0.1":
        errors.append("Contract schema_version is unexpected")
    if payload.get("idp") != "oracle_oci_identity_domains":
        errors.append("Contract must use OCI Identity Domains")
    if payload.get("productive_identity_writes_allowed") is not False:
        errors.append("Contract must block productive identity writes")
    if payload.get("end_user_console_work_allowed") is not False:
        errors.append("Contract must block end-user OCI Console work")
    for endpoint in ("/admin/v1/Users", "/admin/v1/Groups"):
        if endpoint not in payload.get("oci_identity_domain_endpoints", []):
            errors.append(f"Contract missing endpoint {endpoint}")
    for gate in ("domain_ready", "dry_run_plan", "owner_apply_approval"):
        if gate not in payload.get("required_gates", []):
            errors.append(f"Contract missing gate {gate}")


def _validate_domain_readiness(errors: list[str]) -> None:
    ready = check_domain_ready(
        domain="kanzlei-notariat.example",
        tenant_slug="kanzlei-notariat",
        admin_email="admin@kanzlei-notariat.example",
    )
    if ready.get("ready") is not True:
        errors.append(f"Expected ready domain check, got {ready.get('blocking_findings')}")
    if ready.get("verification", {}).get("method") != "dns_txt":
        errors.append("Domain readiness must use DNS TXT verification")

    blocked = check_domain_ready(
        domain="kanzlei-notariat.example",
        tenant_slug="kanzlei-notariat",
        admin_email="admin@gmail.com",
    )
    if blocked.get("ready") is not False:
        errors.append("Freemail admin domain must not be ready")
    if "admin_email_domain_mismatch" not in blocked.get("blocking_findings", []):
        errors.append("Freemail admin check must include domain mismatch")


def _validate_admin_plan(errors: list[str]) -> None:
    plan = build_admin_provisioning_plan(
        tenant_slug="kanzlei-notariat",
        domain="kanzlei-notariat.example",
        admin_email="admin@kanzlei-notariat.example",
        admin_display_name="Admin Notariat",
        identity_domain_url="https://idcs.example.identity.oraclecloud.com:443",
        identity_domain_id="ocid1.domain.oc1.example",
    )
    if plan.get("mode") != "dry_run":
        errors.append("Admin provisioning plan must be dry_run")
    if plan.get("requires_human_approval") is not True:
        errors.append("Admin provisioning plan must require human approval")
    if plan.get("console_access_required_for_end_users") is not False:
        errors.append("Admin provisioning plan must avoid end-user OCI Console work")
    target = plan.get("target", {})
    if not str(target.get("users_endpoint", "")).endswith("/admin/v1/Users"):
        errors.append("Admin provisioning plan must include Users endpoint")
    if not str(target.get("groups_endpoint", "")).endswith("/admin/v1/Groups"):
        errors.append("Admin provisioning plan must include Groups endpoint")
    serialized = json.dumps(plan, sort_keys=True).lower()
    for forbidden in ("secret", "token", "private_key"):
        if forbidden in serialized:
            errors.append(f"Admin provisioning plan exposes forbidden marker {forbidden}")


if __name__ == "__main__":
    raise SystemExit(main())
