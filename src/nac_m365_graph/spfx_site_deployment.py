from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ID = "notary_team_01"
SITE_URL = "https://funktion8.sharepoint.com/sites/NaC-Notar-01"
TEAM_ID = "124f1b11-207d-4307-bfd1-ac0fd73aa90a"
WEB_PART_ID = "3a7bba0c-f8c4-41d6-9ec9-f8a3f7e6fa21"
SOLUTION_PRODUCT_ID = "b7a5417c-0dd3-4e69-87c7-95adfd7e8a58"
SOLUTION_TITLE = "nac-bpmn-viewer-client-side-solution"
PACKAGE_NAME = "nac-bpmn-viewer.sppkg"
PACKAGE_RELATIVE_PATH = Path(
    "spfx/nac-bpmn-viewer/sharepoint/solution/nac-bpmn-viewer.sppkg"
)
PACKAGE_CONFIG_RELATIVE_PATH = Path("spfx/nac-bpmn-viewer/config/package-solution.json")
TEAMS_PACKAGE_RELATIVE_PATH = Path(
    "spfx/nac-bpmn-viewer/sharepoint/solution/nac-bpmn-viewer.zip"
)
PAGE_NAME = "NaC-Testumgebung.aspx"
PAGE_TITLE = "NaC-Testumgebung"
# The M365 CLI cannot add the first web part when SharePoint returns an empty
# CanvasContent1 for a SingleWebPartAppPage. Article pages provide the initial
# canvas section required by `spo page clientsidewebpart add`.
PAGE_LAYOUT = "Article"
INITIAL_PAGE_CONTENT = (
    '[{"controlType":0,"pageSettingsSlice":'
    '{"isDefaultDescription":true,"isDefaultThumbnail":true}}]'
)
APP_CATALOG_SCOPE = "tenant"
TEAMS_INSTALLED_APPS_URL = (
    f"https://graph.microsoft.com/v1.0/teams/{TEAM_ID}/installedApps?$expand=teamsApp"
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_COMMAND_PREFIXES = {
    ("spo", "app", "list"),
    ("spo", "app", "add"),
    ("spo", "app", "get"),
    ("spo", "app", "deploy"),
    ("spo", "app", "instance", "list"),
    ("spo", "app", "install"),
    ("spo", "app", "upgrade"),
    ("spo", "app", "teamspackage", "download"),
    ("spo", "page", "list"),
    ("spo", "page", "add"),
    ("spo", "page", "get"),
    ("spo", "page", "set"),
    ("spo", "page", "clientsidewebpart", "add"),
    ("teams", "app", "list"),
    ("teams", "app", "publish"),
    ("teams", "app", "update"),
    ("teams", "app", "install"),
    ("request",),
}
_FORBIDDEN_COMMAND_WORDS = {
    "remove",
    "retract",
    "uninstall",
    "delete",
    "purge",
    "rollback",
}
_FORBIDDEN_OPTIONS = {
    "--skipfeaturedeployment",
    "--password",
    "--secret",
    "--token",
    "--accesstoken",
    "--certificate",
    "--thumbprint",
}


class DeploymentPlanError(ValueError):
    """Raised when a deployment plan crosses a fixed control-plane boundary."""


class CommandResult(Protocol):
    returncode: int
    stdout: str
    stderr: str


class ControlPlaneCommandRunner(Protocol):
    """Injected M365 CLI adapter; implementations must use argv and shell=False."""

    def run(self, argv: Sequence[str]) -> CommandResult: ...


@dataclass(frozen=True)
class SpfxSiteDeploymentPlan:
    repo_root: Path
    workspace_id: str
    site_url: str
    app_catalog_scope: str
    package_path: Path
    package_sha256: str
    page_name: str
    page_title: str
    page_layout: str
    web_part_id: str
    include_teams: bool
    team_id: str
    teams_package_path: Path

    @property
    def planned_operations(self) -> tuple[str, ...]:
        operations = (
            "inspect_tenant_app_catalog",
            "add_or_overwrite_tenant_app",
            "validate_site_scoped_app",
            "deploy_tenant_catalog_app_without_tenant_wide_activation",
            "install_or_reuse_app_on_target_site",
            "create_or_update_modern_page",
            "initialize_page_canvas_if_empty",
            "add_or_reuse_web_part",
            "publish_page",
        )
        if self.include_teams:
            operations += (
                "download_teams_package",
                "publish_or_update_teams_catalog_app",
                "install_or_reuse_teams_app_on_target_team",
            )
        return operations

    def to_redacted_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "nac.m365-spfx-site-deployment-plan/v0.1",
            "workspace_id": self.workspace_id,
            "site_url": self.site_url,
            "app_catalog_scope": self.app_catalog_scope,
            "package_path": PACKAGE_RELATIVE_PATH.as_posix(),
            "package_sha256": self.package_sha256,
            "page": {
                "name": self.page_name,
                "title": self.page_title,
                "layout": self.page_layout,
                "web_part_id": self.web_part_id,
            },
            "teams": {
                "enabled": self.include_teams,
                "team_id": self.team_id if self.include_teams else None,
            },
            "planned_operations": list(self.planned_operations),
            "tenant_wide_deployment": False,
            "destructive_rollback": False,
            "raw_session_data": False,
        }


class _StepFailure(Exception):
    def __init__(self, step: str, category: str, exit_code: int | None = None) -> None:
        super().__init__(category)
        self.step = step
        self.category = category
        self.exit_code = exit_code


def build_spfx_site_deployment_plan(
    *,
    repo_root: Path = REPO_ROOT,
    workspace_id: str = WORKSPACE_ID,
    site_url: str = SITE_URL,
    include_teams: bool = False,
    team_id: str = TEAM_ID,
    expected_package_sha256: str | None = None,
) -> SpfxSiteDeploymentPlan:
    root = Path(repo_root).resolve()
    if workspace_id != WORKSPACE_ID:
        raise DeploymentPlanError(f"workspace must be {WORKSPACE_ID}")
    if site_url != SITE_URL:
        raise DeploymentPlanError(f"site must be {SITE_URL}")
    if team_id != TEAM_ID:
        raise DeploymentPlanError(f"team must be {TEAM_ID}")

    package_path = (root / PACKAGE_RELATIVE_PATH).resolve()
    config_path = (root / PACKAGE_CONFIG_RELATIVE_PATH).resolve()
    teams_package_path = (root / TEAMS_PACKAGE_RELATIVE_PATH).resolve()
    _validate_package_configuration(config_path)
    _validate_sppkg(package_path)
    package_sha256 = _sha256(package_path)

    if expected_package_sha256 is not None:
        expected = expected_package_sha256.strip().lower()
        if not _SHA256_RE.fullmatch(expected):
            raise DeploymentPlanError("expected package SHA256 must contain 64 lowercase hex characters")
        if package_sha256 != expected:
            raise DeploymentPlanError("package SHA256 does not match the approved binding")

    return SpfxSiteDeploymentPlan(
        repo_root=root,
        workspace_id=workspace_id,
        site_url=site_url,
        app_catalog_scope=APP_CATALOG_SCOPE,
        package_path=package_path,
        package_sha256=package_sha256,
        page_name=PAGE_NAME,
        page_title=PAGE_TITLE,
        page_layout=PAGE_LAYOUT,
        web_part_id=WEB_PART_ID,
        include_teams=include_teams,
        team_id=team_id,
        teams_package_path=teams_package_path,
    )


def run_spfx_site_deployment(
    plan: SpfxSiteDeploymentPlan,
    command_runner: ControlPlaneCommandRunner,
) -> dict[str, Any]:
    evidence = _new_evidence(plan)
    try:
        _validate_plan(plan)
    except DeploymentPlanError:
        return _fail_evidence(evidence, "validate_plan", "invalid_plan")

    if _sha256(plan.package_path) != plan.package_sha256:
        return _fail_evidence(evidence, "verify_package_sha256", "package_hash_mismatch")
    evidence["steps"].append({"name": "verify_package_sha256", "status": "PASSED"})

    command_count = 0

    def invoke(
        step: str,
        argv: Sequence[str],
        *,
        reuse_markers: Sequence[str] = (),
    ) -> tuple[str, bool]:
        nonlocal command_count
        command = tuple(str(part) for part in argv)
        _validate_command(plan, command)
        command_count += 1
        try:
            result = command_runner.run(command)
            returncode = int(result.returncode)
            stdout = result.stdout if isinstance(result.stdout, str) else ""
            stderr = result.stderr if isinstance(result.stderr, str) else ""
        except Exception as exc:
            raise _StepFailure(step, "command_runner_exception") from exc
        if returncode != 0:
            raw_error = f"{stdout}\n{stderr}".lower()
            if any(marker.lower() in raw_error for marker in reuse_markers):
                return "", True
            raise _StepFailure(step, "control_plane_command_failed", returncode)
        return stdout, False

    def invoke_json(step: str, argv: Sequence[str]) -> Any:
        stdout, _ = invoke(step, argv)
        try:
            return json.loads(stdout)
        except (TypeError, json.JSONDecodeError) as exc:
            raise _StepFailure(step, "invalid_control_plane_response") from exc

    def passed(name: str, classification: str | None = None) -> None:
        item: dict[str, Any] = {"name": name, "status": "PASSED"}
        if classification is not None:
            item["classification"] = classification
            evidence["classifications"][name] = classification
        evidence["steps"].append(item)

    try:
        catalog_apps = invoke_json(
            "inspect_tenant_app_catalog",
            _m365("spo", "app", "list", "--appCatalogScope", APP_CATALOG_SCOPE, "--output", "json"),
        )
        catalog_app_exists = _find_exact_catalog_app(catalog_apps) is not None
        passed("inspect_tenant_app_catalog", "update" if catalog_app_exists else "create")

        add_command = [
            "spo",
            "app",
            "add",
            "--filePath",
            str(plan.package_path),
            "--appCatalogScope",
            APP_CATALOG_SCOPE,
        ]
        if catalog_app_exists:
            add_command.append("--overwrite")
        add_command.extend(("--output", "none"))
        invoke(
            "add_or_overwrite_tenant_app",
            _m365(*add_command),
        )
        passed("add_or_overwrite_tenant_app", "update" if catalog_app_exists else "create")

        app_record = invoke_json(
            "validate_site_scoped_app",
            _m365(
                "spo",
                "app",
                "get",
                "--name",
                PACKAGE_NAME,
                "--appCatalogScope",
                APP_CATALOG_SCOPE,
                "--output",
                "json",
            ),
        )
        app_catalog_id = _validate_catalog_app_record(app_record)
        passed("validate_site_scoped_app", "reuse")

        invoke(
            "deploy_tenant_catalog_app_without_tenant_wide_activation",
            _m365(
                "spo",
                "app",
                "deploy",
                "--id",
                app_catalog_id,
                "--appCatalogScope",
                APP_CATALOG_SCOPE,
                "--output",
                "none",
            ),
        )
        passed("deploy_tenant_catalog_app_without_tenant_wide_activation", "update")

        site_apps = invoke_json(
            "inspect_target_site_apps",
            _m365("spo", "app", "instance", "list", "--siteUrl", SITE_URL, "--output", "json"),
        )
        site_app_exists = _find_app(site_apps, solution=True) is not None
        passed("inspect_target_site_apps", "reuse" if site_app_exists else "create")
        if site_app_exists:
            _, no_upgrade = invoke(
                "install_or_reuse_app_on_target_site",
                _m365(
                    "spo",
                    "app",
                    "upgrade",
                    "--id",
                    app_catalog_id,
                    "--siteUrl",
                    SITE_URL,
                    "--appCatalogScope",
                    APP_CATALOG_SCOPE,
                    "--output",
                    "none",
                ),
                reuse_markers=("no upgrade", "already up to date", "does not have an upgrade"),
            )
            passed("install_or_reuse_app_on_target_site", "reuse" if no_upgrade else "update")
        else:
            invoke(
                "install_or_reuse_app_on_target_site",
                _m365(
                    "spo",
                    "app",
                    "install",
                    "--id",
                    app_catalog_id,
                    "--siteUrl",
                    SITE_URL,
                    "--appCatalogScope",
                    APP_CATALOG_SCOPE,
                    "--output",
                    "none",
                ),
            )
            passed("install_or_reuse_app_on_target_site", "create")

        pages = invoke_json(
            "inspect_target_page",
            _m365("spo", "page", "list", "--webUrl", SITE_URL, "--output", "json"),
        )
        page_exists = _page_exists(pages)
        passed("inspect_target_page", "update" if page_exists else "create")
        if page_exists:
            invoke(
                "create_or_update_modern_page",
                _m365(
                    "spo",
                    "page",
                    "set",
                    "--name",
                    PAGE_NAME,
                    "--webUrl",
                    SITE_URL,
                    "--layoutType",
                    PAGE_LAYOUT,
                    "--title",
                    PAGE_TITLE,
                    "--output",
                    "none",
                ),
            )
            passed("create_or_update_modern_page", "update")
        else:
            invoke(
                "create_or_update_modern_page",
                _m365(
                    "spo",
                    "page",
                    "add",
                    "--name",
                    PAGE_NAME,
                    "--webUrl",
                    SITE_URL,
                    "--layoutType",
                    PAGE_LAYOUT,
                    "--title",
                    PAGE_TITLE,
                    "--output",
                    "none",
                ),
            )
            passed("create_or_update_modern_page", "create")

        page = invoke_json(
            "inspect_page_web_parts",
            _m365("spo", "page", "get", "--name", PAGE_NAME, "--webUrl", SITE_URL, "--output", "json"),
        )
        if _page_canvas_is_empty(page):
            invoke(
                "initialize_page_canvas_if_empty",
                _m365(
                    "spo",
                    "page",
                    "set",
                    "--name",
                    PAGE_NAME,
                    "--webUrl",
                    SITE_URL,
                    "--content",
                    INITIAL_PAGE_CONTENT,
                    "--output",
                    "none",
                ),
            )
            page = invoke_json(
                "verify_page_canvas_initialized",
                _m365(
                    "spo",
                    "page",
                    "get",
                    "--name",
                    PAGE_NAME,
                    "--webUrl",
                    SITE_URL,
                    "--output",
                    "json",
                ),
            )
            if _page_canvas_is_empty(page):
                raise _StepFailure(
                    "verify_page_canvas_initialized",
                    "unsafe_control_plane_response",
                )
            passed("initialize_page_canvas_if_empty", "update")
            passed("verify_page_canvas_initialized", "reuse")
        web_part_exists = _contains_string(page, WEB_PART_ID)
        passed("inspect_page_web_parts", "reuse" if web_part_exists else "create")
        if web_part_exists:
            passed("add_or_reuse_web_part", "reuse")
        else:
            invoke(
                "add_or_reuse_web_part",
                _m365(
                    "spo",
                    "page",
                    "clientsidewebpart",
                    "add",
                    "--webUrl",
                    SITE_URL,
                    "--pageName",
                    PAGE_NAME,
                    "--webPartId",
                    WEB_PART_ID,
                    "--output",
                    "none",
                ),
            )
            passed("add_or_reuse_web_part", "create")

        invoke(
            "publish_page",
            _m365(
                "spo",
                "page",
                "set",
                "--name",
                PAGE_NAME,
                "--webUrl",
                SITE_URL,
                "--publish",
                "--output",
                "none",
            ),
        )
        passed("publish_page", "update")

        if plan.include_teams:
            try:
                if plan.teams_package_path.is_symlink():
                    raise OSError("Teams package path must not be a symlink")
                if plan.teams_package_path.exists():
                    if not plan.teams_package_path.is_file():
                        raise OSError("Teams package path must be a regular file")
                    plan.teams_package_path.unlink()
            except OSError as exc:
                raise _StepFailure(
                    "prepare_teams_package_download",
                    "teams_package_path_not_replaceable",
                ) from exc
            invoke(
                "download_teams_package",
                _m365(
                    "spo",
                    "app",
                    "teamspackage",
                    "download",
                    "--appName",
                    PACKAGE_NAME,
                    "--fileName",
                    str(plan.teams_package_path),
                    "--output",
                    "none",
                ),
            )
            passed("download_teams_package", "update")
            teams_manifest_app_id = _read_teams_manifest_app_id(plan.teams_package_path)

            teams_apps = invoke_json(
                "inspect_teams_catalog",
                _m365(
                    "teams",
                    "app",
                    "list",
                    "--distributionMethod",
                    "organization",
                    "--output",
                    "json",
                ),
            )
            teams_app = _find_teams_app(teams_apps, teams_manifest_app_id)
            passed("inspect_teams_catalog", "update" if teams_app else "create")
            if teams_app:
                teams_catalog_id = _required_string(teams_app, "id", "teams catalog app id")
                invoke(
                    "publish_or_update_teams_catalog_app",
                    _m365(
                        "teams",
                        "app",
                        "update",
                        "--id",
                        teams_catalog_id,
                        "--filePath",
                        str(plan.teams_package_path),
                        "--output",
                        "none",
                    ),
                )
                passed("publish_or_update_teams_catalog_app", "update")
            else:
                published = invoke_json(
                    "publish_or_update_teams_catalog_app",
                    _m365(
                        "teams",
                        "app",
                        "publish",
                        "--filePath",
                        str(plan.teams_package_path),
                        "--output",
                        "json",
                    ),
                )
                teams_catalog_id = _required_string(published, "id", "teams catalog app id")
                passed("publish_or_update_teams_catalog_app", "create")

            _, already_installed = invoke(
                "install_or_reuse_teams_app_on_target_team",
                _m365(
                    "teams",
                    "app",
                    "install",
                    "--id",
                    teams_catalog_id,
                    "--teamId",
                    TEAM_ID,
                    "--output",
                    "none",
                ),
                reuse_markers=("already installed in this team",),
            )
            installed_apps = invoke_json(
                "verify_teams_app_installed_on_target_team",
                _m365(
                    "request",
                    "--url",
                    TEAMS_INSTALLED_APPS_URL,
                    "--method",
                    "get",
                    "--output",
                    "json",
                ),
            )
            _validate_installed_teams_app(
                installed_apps,
                teams_catalog_id=teams_catalog_id,
                teams_manifest_app_id=teams_manifest_app_id,
            )
            passed(
                "install_or_reuse_teams_app_on_target_team",
                "reuse" if already_installed else "create",
            )
            passed("verify_teams_app_installed_on_target_team", "reuse")
    except _StepFailure as exc:
        evidence["commands_executed"] = command_count
        return _fail_evidence(evidence, exc.step, exc.category, exc.exit_code)
    except DeploymentPlanError:
        evidence["commands_executed"] = command_count
        return _fail_evidence(evidence, "validate_control_plane_response", "unsafe_control_plane_response")

    evidence["commands_executed"] = command_count
    evidence["status"] = "PASSED"
    return evidence


def _new_evidence(plan: SpfxSiteDeploymentPlan) -> dict[str, Any]:
    return {
        "schema_version": "nac.m365-spfx-site-deployment-evidence/v0.1",
        "status": "RUNNING",
        "scope": {
            "workspace_id": plan.workspace_id,
            "site_url": plan.site_url,
            "team_id": plan.team_id if plan.include_teams else None,
        },
        "package": {
            "path": PACKAGE_RELATIVE_PATH.as_posix(),
            "sha256": plan.package_sha256,
        },
        "steps": [],
        "classifications": {},
        "commands_executed": 0,
        "partial_failure_policy": "stop_without_destructive_rollback",
        "raw_session_data_included": False,
    }


def _fail_evidence(
    evidence: dict[str, Any],
    step: str,
    category: str,
    exit_code: int | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {
        "category": category,
        "message": "Control-plane step failed; raw command output was withheld.",
    }
    if exit_code is not None:
        error["exit_code"] = exit_code
    evidence["steps"].append({"name": step, "status": "FAILED", "error": error})
    evidence["status"] = "FAILED"
    return evidence


def _validate_plan(plan: SpfxSiteDeploymentPlan) -> None:
    expected_package_path = (plan.repo_root / PACKAGE_RELATIVE_PATH).resolve()
    expected_teams_path = (plan.repo_root / TEAMS_PACKAGE_RELATIVE_PATH).resolve()
    if plan.workspace_id != WORKSPACE_ID:
        raise DeploymentPlanError("workspace boundary changed")
    if plan.site_url != SITE_URL:
        raise DeploymentPlanError("site boundary changed")
    if plan.team_id != TEAM_ID:
        raise DeploymentPlanError("team boundary changed")
    if plan.app_catalog_scope != APP_CATALOG_SCOPE:
        raise DeploymentPlanError("only the tenant app catalog is allowed")
    if plan.package_path.resolve() != expected_package_path:
        raise DeploymentPlanError("package path changed")
    if plan.teams_package_path.resolve() != expected_teams_path:
        raise DeploymentPlanError("Teams package path changed")
    if not _SHA256_RE.fullmatch(plan.package_sha256):
        raise DeploymentPlanError("invalid package SHA256 binding")
    if (plan.page_name, plan.page_title, plan.page_layout) != (PAGE_NAME, PAGE_TITLE, PAGE_LAYOUT):
        raise DeploymentPlanError("page boundary changed")
    if plan.web_part_id != WEB_PART_ID:
        raise DeploymentPlanError("web part boundary changed")


def _validate_package_configuration(path: Path) -> None:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
        solution = config["solution"]
        zipped_package = config["paths"]["zippedPackage"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise DeploymentPlanError("SPFx package configuration is missing or invalid") from exc
    if solution.get("id", "").lower() != SOLUTION_PRODUCT_ID:
        raise DeploymentPlanError("SPFx solution ID does not match the approved package")
    if solution.get("name") != SOLUTION_TITLE:
        raise DeploymentPlanError("SPFx solution title does not match the approved package")
    if solution.get("skipFeatureDeployment") is not False:
        raise DeploymentPlanError("skipFeatureDeployment must be explicitly false")
    permission_requests = solution.get("webApiPermissionRequests", [])
    if not isinstance(permission_requests, list) or permission_requests:
        raise DeploymentPlanError("SPFx package must not request Graph or web API permissions")
    if zipped_package != "solution/nac-bpmn-viewer.sppkg":
        raise DeploymentPlanError("SPFx package output path is not approved")


def _validate_sppkg(path: Path) -> None:
    if not path.is_file():
        raise DeploymentPlanError(f"SPFx package is missing at {PACKAGE_RELATIVE_PATH.as_posix()}")
    descriptor = f"ea9917ea-2860-45fb-89bd-121120178be3/WebPart_{WEB_PART_ID}.xml"
    try:
        with zipfile.ZipFile(path) as package:
            names = set(package.namelist())
            if "AppManifest.xml" not in names or descriptor not in names:
                raise DeploymentPlanError("SPFx package does not contain the approved app and web part")
            manifest_bytes = package.read("AppManifest.xml")
            for name in names:
                if not name.lower().endswith(".xml"):
                    continue
                xml_bytes = package.read(name)
                xml_text = xml_bytes.decode("utf-8", errors="replace").lower()
                if "skipfeaturedeployment=\"true\"" in xml_text or "skipfeaturedeployment='true'" in xml_text:
                    raise DeploymentPlanError("SPFx package enables tenant-wide feature deployment")
                xml_root = ET.fromstring(xml_bytes)
                for element in xml_root.iter():
                    local_name = _local_name(element.tag).lower()
                    if local_name in {"webapipermissionrequest", "aadpermission"}:
                        raise DeploymentPlanError(
                            "SPFx package contains a Graph or web API permission request"
                        )
        manifest = ET.fromstring(manifest_bytes)
    except (OSError, zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
        raise DeploymentPlanError("SPFx package is not a valid site-scoped package") from exc
    attributes = {_local_name(key): value for key, value in manifest.attrib.items()}
    if attributes.get("ProductID", "").lower() != SOLUTION_PRODUCT_ID:
        raise DeploymentPlanError("SPFx package ProductID does not match the approved solution")
    if attributes.get("Name") != SOLUTION_TITLE:
        raise DeploymentPlanError("SPFx package name does not match the approved solution")
    if attributes.get("IsClientSideSolution", "").lower() != "true":
        raise DeploymentPlanError("SPFx package must be a client-side solution")


def _validate_catalog_app_record(record: Any) -> str:
    if not isinstance(record, dict):
        raise DeploymentPlanError("app catalog response must be an object")
    if _string_field(record, "ProductId").lower() != SOLUTION_PRODUCT_ID:
        raise DeploymentPlanError("app catalog ProductId does not match the package")
    if _field(record, "IsValidAppPackage") is not True:
        raise DeploymentPlanError("app catalog rejected the package")
    for field in (
        "IsPackageDefaultSkipFeatureDeployment",
        "SkipDeploymentFeature",
        "ContainsTenantWideExtension",
    ):
        if _field(record, field) is not False:
            raise DeploymentPlanError(f"app catalog field {field} must be false")
    if not _has_field(record, "AadPermissions"):
        raise DeploymentPlanError("app catalog did not prove that AadPermissions is empty")
    aad_permissions = _field(record, "AadPermissions")
    if aad_permissions not in (None, "", [], {}):
        raise DeploymentPlanError("app catalog reports unexpected AadPermissions")
    return _required_string(record, "ID", "app catalog id")


def _validate_command(plan: SpfxSiteDeploymentPlan, argv: Sequence[str]) -> None:
    if not argv or argv[0] != "m365":
        raise _StepFailure("validate_command", "non_m365_command_blocked")
    lower = tuple(part.lower() for part in argv)
    body = lower[1:]
    if not any(body[: len(prefix)] == prefix for prefix in _ALLOWED_COMMAND_PREFIXES):
        raise _StepFailure("validate_command", "command_not_allowlisted")
    if _FORBIDDEN_COMMAND_WORDS.intersection(body) or _FORBIDDEN_OPTIONS.intersection(body):
        raise _StepFailure("validate_command", "forbidden_command_blocked")
    if any("tenant-wide" in part or "tenantwide" in part for part in lower):
        raise _StepFailure("validate_command", "tenant_wide_command_blocked")
    for option in ("--weburl", "--siteurl"):
        value = _option_value(lower, argv, option)
        if value is not None and value != SITE_URL:
            raise _StepFailure("validate_command", "site_scope_command_blocked")
    team_id = _option_value(lower, argv, "--teamid")
    if team_id is not None and team_id != TEAM_ID:
        raise _StepFailure("validate_command", "team_scope_command_blocked")
    catalog_scope = _option_value(lower, argv, "--appcatalogscope")
    if catalog_scope is not None and catalog_scope != APP_CATALOG_SCOPE:
        raise _StepFailure("validate_command", "app_catalog_scope_command_blocked")
    for part in argv:
        if part.lower().startswith(("http://", "https://")) and part not in {
            SITE_URL,
            TEAMS_INSTALLED_APPS_URL,
        }:
            raise _StepFailure("validate_command", "unexpected_url_command_blocked")
    if tuple(body[:3]) == ("spo", "app", "add"):
        if _option_value(lower, argv, "--filepath") != str(plan.package_path):
            raise _StepFailure("validate_command", "package_path_command_blocked")
    if tuple(body[:3]) in {("teams", "app", "publish"), ("teams", "app", "update")}:
        if _option_value(lower, argv, "--filepath") != str(plan.teams_package_path):
            raise _StepFailure("validate_command", "teams_package_path_command_blocked")
    if tuple(body[:2]) == ("spo", "page"):
        page_name = _option_value(lower, argv, "--name") or _option_value(
            lower, argv, "--pagename"
        )
        if page_name is not None and page_name != PAGE_NAME:
            raise _StepFailure("validate_command", "page_scope_command_blocked")
        content = _option_value(lower, argv, "--content")
        if content is not None and content != INITIAL_PAGE_CONTENT:
            raise _StepFailure("validate_command", "page_content_command_blocked")
    if tuple(body[:1]) == ("request",):
        if _option_value(lower, argv, "--url") != TEAMS_INSTALLED_APPS_URL:
            raise _StepFailure("validate_command", "teams_readback_url_blocked")
        if (_option_value(lower, argv, "--method") or "get").lower() != "get":
            raise _StepFailure("validate_command", "teams_readback_method_blocked")
        if any(option in lower for option in ("--body", "--filepath", "--resource")):
            raise _StepFailure("validate_command", "teams_readback_option_blocked")


def _m365(*parts: str) -> tuple[str, ...]:
    return ("m365", *parts)


def _option_value(lower: Sequence[str], original: Sequence[str], option: str) -> str | None:
    try:
        index = lower.index(option)
    except ValueError:
        return None
    if index + 1 >= len(original):
        raise _StepFailure("validate_command", "missing_command_option_value")
    return original[index + 1]


def _find_app(payload: Any, *, solution: bool) -> dict[str, Any] | None:
    for item in _object_items(payload):
        if solution:
            product_id = _string_field(item, "ProductId").strip().lower()
            if product_id == SOLUTION_PRODUCT_ID:
                return item
        elif _string_field(item, "externalId").lower() == WEB_PART_ID:
            return item
    return None


def _find_exact_catalog_app(payload: Any) -> dict[str, Any] | None:
    exact_matches: list[dict[str, Any]] = []
    collisions: list[dict[str, Any]] = []
    for item in _object_items(payload):
        product_id = _string_field(item, "ProductId").strip().lower()
        has_expected_name = any(
            _string_field(item, field).strip().lower() == expected.lower()
            for field, expected in (
                ("Title", SOLUTION_TITLE),
                ("Name", PACKAGE_NAME),
                ("FileName", PACKAGE_NAME),
                ("FileLeafRef", PACKAGE_NAME),
            )
        )
        if product_id == SOLUTION_PRODUCT_ID:
            exact_matches.append(item)
        elif has_expected_name:
            collisions.append(item)
    if collisions:
        raise DeploymentPlanError(
            "app catalog name collision does not have the approved ProductId"
        )
    if len(exact_matches) > 1:
        raise DeploymentPlanError("app catalog contains duplicate approved ProductId entries")
    return exact_matches[0] if exact_matches else None


def _find_teams_app(payload: Any, external_id: str) -> dict[str, Any] | None:
    expected = external_id.strip().lower()
    if not expected:
        raise DeploymentPlanError("Teams manifest app id is missing")
    for item in _object_items(payload):
        if _string_field(item, "externalId").strip().lower() == expected:
            return item
    return None


def _validate_installed_teams_app(
    payload: Any,
    *,
    teams_catalog_id: str,
    teams_manifest_app_id: str,
) -> None:
    expected_catalog_id = teams_catalog_id.strip().lower()
    expected_manifest_id = teams_manifest_app_id.strip().lower()
    matches: list[dict[str, Any]] = []
    for item in _object_items(payload):
        teams_app = _field(item, "teamsApp")
        if not isinstance(teams_app, dict):
            continue
        catalog_id = _string_field(teams_app, "id").strip().lower()
        manifest_id = _string_field(teams_app, "externalId").strip().lower()
        if catalog_id == expected_catalog_id and manifest_id == expected_manifest_id:
            matches.append(item)
    if len(matches) != 1:
        raise DeploymentPlanError(
            "target team did not prove exactly one installed app with approved identities"
        )


def _read_teams_manifest_app_id(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as package:
            payload = json.loads(package.read("manifest.json").decode("utf-8"))
    except (
        OSError,
        zipfile.BadZipFile,
        KeyError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise DeploymentPlanError("downloaded Teams package is missing a valid manifest") from exc
    if not isinstance(payload, dict):
        raise DeploymentPlanError("downloaded Teams manifest must be an object")
    app_id = payload.get("id")
    if not isinstance(app_id, str) or not re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        app_id.strip(),
    ):
        raise DeploymentPlanError("downloaded Teams manifest app id is invalid")
    return app_id.strip().lower()


def _page_exists(payload: Any) -> bool:
    for item in _object_items(payload):
        for field_name in ("Name", "FileName", "FileLeafRef", "Url", "ServerRelativeUrl"):
            value = _string_field(item, field_name)
            if value.lower() == PAGE_NAME.lower() or value.lower().endswith("/" + PAGE_NAME.lower()):
                return True
    return False


def _page_canvas_is_empty(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    if _has_field(payload, "canvasContentJson"):
        canvas = _field(payload, "canvasContentJson")
    elif _has_field(payload, "CanvasContent1"):
        canvas = _field(payload, "CanvasContent1")
    else:
        return False
    if isinstance(canvas, str):
        try:
            canvas = json.loads(canvas)
        except json.JSONDecodeError as exc:
            raise DeploymentPlanError("page canvas response is invalid") from exc
    if not isinstance(canvas, list):
        raise DeploymentPlanError("page canvas response must be a list")
    return not canvas


def _object_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        value = _field(payload, "value")
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        return [payload]
    return []


def _contains_string(payload: Any, needle: str) -> bool:
    if isinstance(payload, str):
        return needle.lower() in payload.lower()
    if isinstance(payload, dict):
        return any(_contains_string(value, needle) for value in payload.values())
    if isinstance(payload, list):
        return any(_contains_string(value, needle) for value in payload)
    return False


def _field(payload: dict[str, Any], name: str) -> Any:
    expected = name.lower()
    for key, value in payload.items():
        if key.lower() == expected:
            return value
    return None


def _has_field(payload: dict[str, Any], name: str) -> bool:
    expected = name.lower()
    return any(key.lower() == expected for key in payload)


def _string_field(payload: dict[str, Any], name: str) -> str:
    value = _field(payload, name)
    return value if isinstance(value, str) else ""


def _required_string(payload: Any, name: str, label: str) -> str:
    if not isinstance(payload, dict):
        raise DeploymentPlanError(f"{label} response must be an object")
    value = _string_field(payload, name)
    if not value:
        raise DeploymentPlanError(f"{label} is missing")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise DeploymentPlanError("SPFx package cannot be read") from exc
    return digest.hexdigest()


def _local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1]
