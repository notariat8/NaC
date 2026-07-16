from __future__ import annotations

import hashlib
import io
import json
import os
import re
import stat
import time
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Protocol, Sequence


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
BFF_API_RESOURCE = "NaC M365 BFF"
BFF_API_SCOPE = "Matter.Read"
APPROVED_WEB_API_PERMISSION_REQUESTS = (
    {"resource": BFF_API_RESOURCE, "scope": BFF_API_SCOPE},
)
DEFAULT_READBACK_MAX_ATTEMPTS = 6
DEFAULT_READBACK_BACKOFF_SECONDS = 2.0

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_TEAMS_VERSION_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$"
)
_TEAMS_MANIFEST_VERSION_RE = re.compile(r"^1[.][0-9]{1,2}$")
_ALLOWED_TEAMS_ARCHIVE_ENTRIES = frozenset(
    {"manifest.json", "color.png", "outline.png"}
)
_FORBIDDEN_TEAMS_CAPABILITY_FIELDS = frozenset(
    {
        "authorization",
        "permissions",
        "devicePermissions",
        "bots",
        "composeExtensions",
        "connectors",
        "activities",
        "meetingExtensionDefinition",
        "staticTabs",
        "configurableTabs",
        "webApplicationInfo",
        "validDomains",
    }
)
_ALLOWED_TEAMS_MANIFEST_FIELDS = frozenset(
    {
        "$schema",
        "manifestVersion",
        "version",
        "id",
        "packageName",
        "developer",
        "name",
        "description",
        "icons",
        "accentColor",
        "localizationInfo",
    }
)
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_MAX_TEAMS_PACKAGE_BYTES = 5 * 1024 * 1024
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


@dataclass(frozen=True, slots=True)
class ReadbackPolicy:
    """Bounded GET-only polling after one M365 control-plane write."""

    max_attempts: int = DEFAULT_READBACK_MAX_ATTEMPTS
    backoff_seconds: float = DEFAULT_READBACK_BACKOFF_SECONDS
    sleeper: Callable[[float], None] = time.sleep

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_attempts, bool)
            or not isinstance(self.max_attempts, int)
            or self.max_attempts < 1
        ):
            raise ValueError("max_attempts must be a positive integer")
        if (
            isinstance(self.backoff_seconds, bool)
            or not isinstance(self.backoff_seconds, (int, float))
            or self.backoff_seconds < 0
        ):
            raise ValueError("backoff_seconds must be non-negative")
        if not callable(self.sleeper):
            raise TypeError("sleeper must be callable")


DEFAULT_READBACK_POLICY = ReadbackPolicy()


@dataclass(frozen=True, slots=True)
class TeamsCatalogVersionReadback:
    """Validated catalog-version shape suitable for Step 12 reconciliation."""

    expected_version: str
    highest_version: str
    expected_publishing_state: str | None
    historical_published_versions: tuple[str, ...]
    published_versions: tuple[str, ...]
    definition_count: int
    required_action: str

    @property
    def expected_is_unique_highest_published(self) -> bool:
        return (
            self.highest_version == self.expected_version
            and self.expected_publishing_state == "published"
            and self.published_versions.count(self.expected_version) == 1
        )

    def to_redacted_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "nac.m365-teams-catalog-version-readback/v0.1",
            "expected_version": self.expected_version,
            "highest_version": self.highest_version,
            "expected_publishing_state": self.expected_publishing_state,
            "historical_published_versions": list(self.historical_published_versions),
            "published_versions": list(self.published_versions),
            "definition_count": self.definition_count,
            "required_action": self.required_action,
            "expected_is_unique_highest_published": (
                self.expected_is_unique_highest_published
            ),
        }


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
    *,
    readback_policy: ReadbackPolicy = DEFAULT_READBACK_POLICY,
    bound_artifacts: Mapping[str, tuple[Path, str]] | None = None,
) -> dict[str, Any]:
    evidence = _new_evidence(plan)
    try:
        _validate_plan(plan)
        if not isinstance(readback_policy, ReadbackPolicy):
            raise DeploymentPlanError("readback policy is invalid")
    except DeploymentPlanError:
        return _fail_evidence(evidence, "validate_plan", "invalid_plan")

    if _sha256(plan.package_path) != plan.package_sha256:
        return _fail_evidence(evidence, "verify_package_sha256", "package_hash_mismatch")
    evidence["steps"].append({"name": "verify_package_sha256", "status": "PASSED"})

    command_count = 0
    runtime_bound_artifacts = dict(bound_artifacts or {})
    allowed_teams_catalog_detail_id: str | None = None
    allowed_teams_manifest_app_id: str | None = None

    def invoke(
        step: str,
        argv: Sequence[str],
        *,
        reuse_markers: Sequence[str] = (),
    ) -> tuple[str, bool]:
        nonlocal command_count
        command = tuple(str(part) for part in argv)
        _validate_command(
            plan,
            command,
            allowed_teams_catalog_detail_id=allowed_teams_catalog_detail_id,
            allowed_teams_manifest_app_id=allowed_teams_manifest_app_id,
        )
        command_count += 1
        try:
            command_bindings = {
                argument: binding
                for argument, binding in runtime_bound_artifacts.items()
                if command.count(argument) == 1
            }
            if command_bindings:
                run_bound = getattr(command_runner, "run_bound", None)
                if not callable(run_bound):
                    raise _StepFailure(step, "sealed_artifact_runner_required")
                result = run_bound(command, command_bindings)
            else:
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

    def poll_json(
        step: str,
        argv: Sequence[str],
        *,
        accepted: Callable[[Any], bool],
        timeout_category: str,
    ) -> Any:
        for attempt in range(readback_policy.max_attempts):
            try:
                payload = invoke_json(step, argv)
            except _StepFailure as exc:
                if exc.category != "control_plane_command_failed":
                    raise
            else:
                if accepted(payload):
                    return payload
            if attempt + 1 < readback_policy.max_attempts:
                try:
                    readback_policy.sleeper(readback_policy.backoff_seconds)
                except Exception as exc:
                    raise _StepFailure(step, "readback_sleep_failed") from exc
        raise _StepFailure(step, timeout_category)

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

        app_get_command = _m365(
            "spo",
            "app",
            "get",
            "--name",
            PACKAGE_NAME,
            "--appCatalogScope",
            APP_CATALOG_SCOPE,
            "--output",
            "json",
        )
        app_record = poll_json(
            "validate_site_scoped_app",
            app_get_command,
            accepted=_catalog_app_record_is_visible,
            timeout_category="app_catalog_add_readback_timeout",
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

        deployed_record = poll_json(
            "verify_tenant_catalog_app_deployed",
            app_get_command,
            accepted=_catalog_app_record_is_deployed,
            timeout_category="app_catalog_deploy_readback_timeout",
        )
        _validate_catalog_app_record(deployed_record)
        passed("verify_tenant_catalog_app_deployed", "reuse")

        site_app_list_command = _m365(
            "spo", "app", "instance", "list", "--siteUrl", SITE_URL, "--output", "json"
        )
        site_apps = invoke_json(
            "inspect_target_site_apps",
            site_app_list_command,
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
            site_app_timeout = "site_app_upgrade_readback_timeout"
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
            site_app_timeout = "site_app_install_readback_timeout"

        poll_json(
            "verify_target_site_app",
            site_app_list_command,
            accepted=lambda payload: _find_app(payload, solution=True) is not None,
            timeout_category=site_app_timeout,
        )
        passed("verify_target_site_app", "reuse")

        pages = invoke_json(
            "inspect_target_page",
            _m365("spo", "page", "list", "--webUrl", SITE_URL, "--output", "json"),
        )
        page_exists = _page_exists(pages)
        passed("inspect_target_page", "update" if page_exists else "create")
        page_get_command = _m365(
            "spo", "page", "get", "--name", PAGE_NAME, "--webUrl", SITE_URL, "--output", "json"
        )
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
            page_timeout = "page_update_readback_timeout"
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
            page_timeout = "page_create_readback_timeout"

        page = poll_json(
            "inspect_page_web_parts",
            page_get_command,
            accepted=_page_readback_is_visible,
            timeout_category=page_timeout,
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
            page = poll_json(
                "verify_page_canvas_initialized",
                page_get_command,
                accepted=lambda payload: _page_readback_is_visible(payload)
                and not _page_canvas_is_empty(payload),
                timeout_category="page_canvas_readback_timeout",
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
            page = poll_json(
                "verify_web_part_added",
                page_get_command,
                accepted=lambda payload: _page_readback_is_visible(payload)
                and _contains_string(payload, WEB_PART_ID),
                timeout_category="web_part_add_readback_timeout",
            )
            passed("verify_web_part_added", "reuse")

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
        poll_json(
            "verify_page_published",
            page_get_command,
            accepted=_page_publish_readback_is_ready,
            timeout_category="page_publish_readback_timeout",
        )
        passed("verify_page_published", "reuse")

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
            (
                teams_manifest_app_id,
                teams_manifest_version,
                teams_package_sha256,
            ) = _read_teams_manifest_identity(plan.teams_package_path)
            runtime_bound_artifacts[str(plan.teams_package_path)] = (
                plan.teams_package_path,
                teams_package_sha256,
            )
            allowed_teams_manifest_app_id = teams_manifest_app_id
            teams_installed_apps_url = _teams_installed_apps_url(teams_manifest_app_id)

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
                teams_catalog_id = _validate_teams_catalog_app_record(
                    teams_app,
                    teams_manifest_app_id=teams_manifest_app_id,
                )
                allowed_teams_catalog_detail_id = teams_catalog_id
                catalog_detail_command = _m365(
                    "request",
                    "--url",
                    _teams_catalog_detail_url(teams_catalog_id),
                    "--method",
                    "get",
                    "--output",
                    "json",
                )
                teams_app_detail = invoke_json(
                    "inspect_teams_catalog_app_version",
                    catalog_detail_command,
                )
                version_readback = _validate_teams_catalog_app_detail(
                    teams_app_detail,
                    teams_catalog_id=teams_catalog_id,
                    teams_manifest_app_id=teams_manifest_app_id,
                    teams_manifest_version=teams_manifest_version,
                )
                catalog_action = version_readback.required_action
                passed("inspect_teams_catalog_app_version", "reuse")
                if version_readback.expected_publishing_state == "submitted":
                    raise _StepFailure(
                        "publish_or_update_teams_catalog_app",
                        "teams_catalog_review_pending",
                    )
                if catalog_action == "update":
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
                    updated_detail = poll_json(
                        "verify_teams_catalog_app_update",
                        catalog_detail_command,
                        accepted=lambda payload: _teams_catalog_readback_is_ready(
                            payload,
                            teams_catalog_id=teams_catalog_id,
                            teams_manifest_app_id=teams_manifest_app_id,
                            teams_manifest_version=teams_manifest_version,
                        ),
                        timeout_category="teams_catalog_update_readback_timeout",
                    )
                    version_readback = _validate_teams_catalog_app_detail(
                        updated_detail,
                        teams_catalog_id=teams_catalog_id,
                        teams_manifest_app_id=teams_manifest_app_id,
                        teams_manifest_version=teams_manifest_version,
                    )
                    passed("verify_teams_catalog_app_update", "reuse")
                if not version_readback.expected_is_unique_highest_published:
                    raise _StepFailure(
                        "publish_or_update_teams_catalog_app",
                        "teams_catalog_review_pending",
                    )
                passed("publish_or_update_teams_catalog_app", catalog_action)
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
                teams_catalog_id = _validate_published_teams_app(
                    published,
                    teams_manifest_app_id=teams_manifest_app_id,
                )
                allowed_teams_catalog_detail_id = teams_catalog_id
                catalog_detail_command = _m365(
                    "request",
                    "--url",
                    _teams_catalog_detail_url(teams_catalog_id),
                    "--method",
                    "get",
                    "--output",
                    "json",
                )
                published_detail = poll_json(
                    "verify_teams_catalog_app_publish",
                    catalog_detail_command,
                    accepted=lambda payload: _teams_catalog_readback_is_ready(
                        payload,
                        teams_catalog_id=teams_catalog_id,
                        teams_manifest_app_id=teams_manifest_app_id,
                        teams_manifest_version=teams_manifest_version,
                    ),
                    timeout_category="teams_catalog_publish_readback_timeout",
                )
                version_readback = _validate_teams_catalog_app_detail(
                    published_detail,
                    teams_catalog_id=teams_catalog_id,
                    teams_manifest_app_id=teams_manifest_app_id,
                    teams_manifest_version=teams_manifest_version,
                )
                passed("publish_or_update_teams_catalog_app", "create")
                passed("verify_teams_catalog_app_publish", "reuse")

            evidence["teams_catalog_version_readback"] = version_readback.to_redacted_dict()

            installed_apps = invoke_json(
                "inspect_teams_app_installation_on_target_team",
                _m365(
                    "request",
                    "--url",
                    teams_installed_apps_url,
                    "--method",
                    "get",
                    "--output",
                    "json",
                ),
            )
            try:
                already_installed = _has_installed_teams_app(
                    installed_apps,
                    teams_catalog_id=teams_catalog_id,
                    teams_manifest_app_id=teams_manifest_app_id,
                )
            except DeploymentPlanError as exc:
                raise _StepFailure(
                    "inspect_teams_app_installation_on_target_team",
                    "unsafe_control_plane_response",
                ) from exc
            passed(
                "inspect_teams_app_installation_on_target_team",
                "reuse" if already_installed else "create",
            )
            install_write_failed = False
            if not already_installed:
                try:
                    invoke(
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
                    )
                except _StepFailure as exc:
                    if (
                        exc.step != "install_or_reuse_teams_app_on_target_team"
                        or exc.category
                        not in {"command_runner_exception", "control_plane_command_failed"}
                    ):
                        raise
                    install_write_failed = True
                installed_apps = poll_json(
                    "verify_teams_app_installed_on_target_team",
                    _m365(
                        "request",
                        "--url",
                        teams_installed_apps_url,
                        "--method",
                        "get",
                        "--output",
                        "json",
                    ),
                    accepted=lambda payload: _has_installed_teams_app(
                        payload,
                        teams_catalog_id=teams_catalog_id,
                        teams_manifest_app_id=teams_manifest_app_id,
                    ),
                    timeout_category="teams_app_install_readback_timeout",
                )
            try:
                _validate_installed_teams_app(
                    installed_apps,
                    teams_catalog_id=teams_catalog_id,
                    teams_manifest_app_id=teams_manifest_app_id,
                )
            except DeploymentPlanError as exc:
                raise _StepFailure(
                    "verify_teams_app_installed_on_target_team",
                    "unsafe_control_plane_response",
                ) from exc
            passed(
                "install_or_reuse_teams_app_on_target_team",
                "reuse" if already_installed or install_write_failed else "create",
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
    if permission_requests != list(APPROVED_WEB_API_PERMISSION_REQUESTS):
        raise DeploymentPlanError("SPFx package permissions must be exactly NaC M365 BFF / Matter.Read")
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
            embedded_permissions: list[dict[str, str]] = []
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
                    if local_name == "webapipermissionrequest":
                        attributes = {
                            _local_name(key).lower(): value
                            for key, value in element.attrib.items()
                        }
                        embedded_permissions.append(
                            {
                                "resource": attributes.get("resource", ""),
                                "scope": attributes.get("scope", ""),
                            }
                        )
                    elif local_name == "aadpermission":
                        raise DeploymentPlanError("SPFx package contains an unapproved AAD permission")
            if embedded_permissions != list(APPROVED_WEB_API_PERMISSION_REQUESTS):
                raise DeploymentPlanError(
                    "SPFx package permission request must be exactly NaC M365 BFF / Matter.Read"
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
        raise DeploymentPlanError("app catalog did not prove the exact AadPermissions request")
    aad_permissions = _field(record, "AadPermissions")
    if _normalize_catalog_permissions(aad_permissions) != list(APPROVED_WEB_API_PERMISSION_REQUESTS):
        raise DeploymentPlanError("app catalog reports unexpected AadPermissions")
    return _required_string(record, "ID", "app catalog id")


def _catalog_app_record_is_visible(record: Any) -> bool:
    return (
        isinstance(record, dict)
        and _string_field(record, "ProductId").strip().lower() == SOLUTION_PRODUCT_ID
    )


def _catalog_app_record_is_deployed(record: Any) -> bool:
    if not _catalog_app_record_is_visible(record):
        return False
    for field in ("Deployed", "IsDeployed"):
        if _has_field(record, field):
            return _field(record, field) is True
    return False


def _normalize_catalog_permissions(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            return []
        resource = _field(item, "Resource")
        scope = _field(item, "Scope")
        if not isinstance(resource, str) or not isinstance(scope, str):
            return []
        normalized.append({"resource": resource, "scope": scope})
    return normalized


def _validate_command(
    plan: SpfxSiteDeploymentPlan,
    argv: Sequence[str],
    *,
    allowed_teams_catalog_detail_id: str | None = None,
    allowed_teams_manifest_app_id: str | None = None,
) -> None:
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
    allowed_urls = {SITE_URL}
    if allowed_teams_manifest_app_id is not None:
        allowed_urls.add(_teams_installed_apps_url(allowed_teams_manifest_app_id))
    if allowed_teams_catalog_detail_id is not None:
        allowed_urls.add(_teams_catalog_detail_url(allowed_teams_catalog_detail_id))
    for part in argv:
        if part.lower().startswith(("http://", "https://")) and part not in allowed_urls:
            raise _StepFailure("validate_command", "unexpected_url_command_blocked")
    if tuple(body[:3]) == ("spo", "app", "add"):
        if _option_value(lower, argv, "--filepath") != str(plan.package_path):
            raise _StepFailure("validate_command", "package_path_command_blocked")
    if tuple(body[:3]) == ("teams", "app", "publish"):
        if _option_value(lower, argv, "--filepath") != str(plan.teams_package_path):
            raise _StepFailure("validate_command", "teams_package_path_command_blocked")
    if tuple(body[:3]) == ("teams", "app", "update"):
        if allowed_teams_catalog_detail_id is None:
            raise _StepFailure("validate_command", "teams_catalog_update_identity_missing")
        expected = _m365(
            "teams",
            "app",
            "update",
            "--id",
            allowed_teams_catalog_detail_id,
            "--filePath",
            str(plan.teams_package_path),
            "--output",
            "none",
        )
        if tuple(argv) != expected:
            raise _StepFailure("validate_command", "teams_catalog_update_command_blocked")
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
        request_urls: set[str] = set()
        if allowed_teams_manifest_app_id is not None:
            request_urls.add(_teams_installed_apps_url(allowed_teams_manifest_app_id))
        if allowed_teams_catalog_detail_id is not None:
            request_urls.add(_teams_catalog_detail_url(allowed_teams_catalog_detail_id))
        request_url = _option_value(lower, argv, "--url")
        if request_url not in request_urls:
            raise _StepFailure("validate_command", "teams_readback_url_blocked")
        if tuple(argv) != _m365(
            "request",
            "--url",
            request_url,
            "--method",
            "get",
            "--output",
            "json",
        ):
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
    matches: list[dict[str, Any]] = []
    for item in _teams_catalog_items(payload):
        if _string_field(item, "externalId").strip().lower() == expected:
            matches.append(item)
    if len(matches) > 1:
        raise DeploymentPlanError(
            "Teams catalog contains duplicate entries for the manifest externalId"
        )
    return matches[0] if matches else None


def _validate_teams_catalog_app_record(
    payload: Any,
    *,
    teams_manifest_app_id: str,
) -> str:
    if not isinstance(payload, dict):
        raise DeploymentPlanError("Teams catalog app response must be an object")
    teams_catalog_id = _required_guid(payload, "id", "Teams catalog app id")
    external_id = _required_guid(payload, "externalId", "Teams catalog app externalId")
    if external_id != teams_manifest_app_id:
        raise DeploymentPlanError(
            "Teams catalog app externalId does not match the downloaded manifest"
        )
    if _field(payload, "distributionMethod") != "organization":
        raise DeploymentPlanError(
            "Teams catalog app must be bound to the organization catalog"
        )
    return teams_catalog_id


def _teams_catalog_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict) and "value" in payload:
        items = payload["value"]
        if not isinstance(items, list):
            raise DeploymentPlanError("Teams catalog value must be a list")
    else:
        raise DeploymentPlanError(
            "Teams catalog response must be a list or an object with a value list"
        )
    if any(not isinstance(item, dict) for item in items):
        raise DeploymentPlanError("Teams catalog entries must be objects")
    return items


def _teams_catalog_readback_is_ready(
    payload: Any,
    *,
    teams_catalog_id: str,
    teams_manifest_app_id: str,
    teams_manifest_version: str,
) -> bool:
    if isinstance(payload, dict) and _field(payload, "appDefinitions") == []:
        detail_catalog_id = _required_guid(payload, "id", "Teams catalog detail id")
        detail_external_id = _required_guid(
            payload,
            "externalId",
            "Teams catalog detail externalId",
        )
        if (
            detail_catalog_id != teams_catalog_id
            or detail_external_id != teams_manifest_app_id
        ):
            raise DeploymentPlanError("Teams catalog pending readback identity is invalid")
        return False
    return summarize_teams_catalog_versions(
        payload,
        teams_catalog_id=teams_catalog_id,
        teams_manifest_app_id=teams_manifest_app_id,
        teams_manifest_version=teams_manifest_version,
    ).expected_is_unique_highest_published


def summarize_teams_catalog_versions(
    payload: Any,
    *,
    teams_catalog_id: str,
    teams_manifest_app_id: str,
    teams_manifest_version: str,
) -> TeamsCatalogVersionReadback:
    """Validate a Teams catalog detail and summarize its semver-safe state."""

    if not isinstance(payload, dict):
        raise DeploymentPlanError("Teams catalog detail response must be an object")
    detail_catalog_id = _required_guid(payload, "id", "Teams catalog detail id")
    detail_external_id = _required_guid(
        payload,
        "externalId",
        "Teams catalog detail externalId",
    )
    if detail_catalog_id != teams_catalog_id:
        raise DeploymentPlanError("Teams catalog detail id does not match the selected app")
    if detail_external_id != teams_manifest_app_id:
        raise DeploymentPlanError(
            "Teams catalog detail externalId does not match the downloaded manifest"
        )

    definitions = _field(payload, "appDefinitions")
    if not isinstance(definitions, list):
        raise DeploymentPlanError("Teams catalog detail appDefinitions must be a list")
    definitions_by_version: dict[tuple[int, int, int], tuple[str, str]] = {}
    for definition in definitions:
        if not isinstance(definition, dict):
            raise DeploymentPlanError("Teams catalog app definition must be an object")
        version = _field(definition, "version")
        publishing_state = _field(definition, "publishingState")
        if not isinstance(version, str) or not _TEAMS_VERSION_RE.fullmatch(version):
            raise DeploymentPlanError("Teams catalog app definition version is invalid")
        if publishing_state not in {"published", "submitted", "rejected"}:
            raise DeploymentPlanError("Teams catalog app definition publishingState is invalid")
        version_key = _teams_version_key(version)
        if version_key in definitions_by_version:
            raise DeploymentPlanError("Teams catalog contains duplicate app definition versions")
        definitions_by_version[version_key] = (version, publishing_state)
    if not definitions_by_version:
        raise DeploymentPlanError("Teams catalog app has no version definitions")

    target_version = _teams_version_key(teams_manifest_version)
    highest_key = max(definitions_by_version)
    if highest_key > target_version:
        raise DeploymentPlanError("Teams catalog downgrade is blocked")

    historical_keys = sorted(key for key in definitions_by_version if key < target_version)
    historical_versions: list[str] = []
    for key in historical_keys:
        version, state = definitions_by_version[key]
        if state != "published":
            raise DeploymentPlanError(
                "Teams catalog historical app definitions must be published"
            )
        historical_versions.append(version)

    expected_definition = definitions_by_version.get(target_version)
    expected_state = expected_definition[1] if expected_definition is not None else None
    if expected_state == "rejected":
        raise DeploymentPlanError("Teams catalog rejected the matching manifest version")
    required_action = "reuse" if expected_definition is not None else "update"

    published_versions = tuple(
        version
        for _, (version, state) in sorted(definitions_by_version.items())
        if state == "published"
    )
    return TeamsCatalogVersionReadback(
        expected_version=teams_manifest_version,
        highest_version=definitions_by_version[highest_key][0],
        expected_publishing_state=expected_state,
        historical_published_versions=tuple(historical_versions),
        published_versions=published_versions,
        definition_count=len(definitions_by_version),
        required_action=required_action,
    )


def _validate_teams_catalog_app_detail(
    payload: Any,
    *,
    teams_catalog_id: str,
    teams_manifest_app_id: str,
    teams_manifest_version: str,
) -> TeamsCatalogVersionReadback:
    return summarize_teams_catalog_versions(
        payload,
        teams_catalog_id=teams_catalog_id,
        teams_manifest_app_id=teams_manifest_app_id,
        teams_manifest_version=teams_manifest_version,
    )


def _teams_version_key(version: str) -> tuple[int, int, int]:
    if not _TEAMS_VERSION_RE.fullmatch(version):
        raise DeploymentPlanError("Teams version is invalid")
    major, minor, patch = version.split(".")
    return int(major), int(minor), int(patch)


def _validate_published_teams_app(
    payload: Any,
    *,
    teams_manifest_app_id: str,
) -> str:
    teams_catalog_id = _required_guid(payload, "id", "teams catalog app id")
    published_external_id = _required_guid(
        payload,
        "externalId",
        "teams catalog app externalId",
    )
    if published_external_id != teams_manifest_app_id:
        raise DeploymentPlanError(
            "published Teams catalog externalId does not match the downloaded manifest"
        )
    return teams_catalog_id


def _validate_installed_teams_app(
    payload: Any,
    *,
    teams_catalog_id: str,
    teams_manifest_app_id: str,
) -> None:
    if not _has_installed_teams_app(
        payload,
        teams_catalog_id=teams_catalog_id,
        teams_manifest_app_id=teams_manifest_app_id,
    ):
        raise DeploymentPlanError(
            "target team did not prove exactly one installed app with approved identities"
        )


def _has_installed_teams_app(
    payload: Any,
    *,
    teams_catalog_id: str,
    teams_manifest_app_id: str,
) -> bool:
    if not isinstance(payload, dict) or not isinstance(payload.get("value"), list):
        raise DeploymentPlanError("target team installed-app response must contain a value list")
    if _field(payload, "@odata.nextLink") not in (None, ""):
        raise DeploymentPlanError("target team installed-app response must not be paginated")
    items = payload["value"]
    if any(not isinstance(item, dict) for item in items):
        raise DeploymentPlanError("target team installed-app entries must be objects")
    expected_catalog_id = teams_catalog_id.strip().lower()
    expected_manifest_id = teams_manifest_app_id.strip().lower()
    matches: list[dict[str, Any]] = []
    for item in items:
        teams_app = _field(item, "teamsApp")
        if not isinstance(teams_app, dict):
            raise DeploymentPlanError("target team installed-app entry is missing teamsApp")
        catalog_id = _string_field(teams_app, "id").strip().lower()
        manifest_id = _string_field(teams_app, "externalId").strip().lower()
        if manifest_id != expected_manifest_id:
            raise DeploymentPlanError(
                "target team installed-app response violated the manifest identity filter"
            )
        if catalog_id != expected_catalog_id:
            raise DeploymentPlanError(
                "target team installed-app response contains a catalog identity collision"
            )
        matches.append(item)
    if len(matches) > 1:
        raise DeploymentPlanError(
            "target team returned duplicate installed apps with approved identities"
        )
    return len(matches) == 1


def _read_teams_manifest_identity(path: Path) -> tuple[str, str, str]:
    try:
        package_bytes = _stable_teams_package_bytes(path)
        with zipfile.ZipFile(io.BytesIO(package_bytes)) as package:
            records: dict[str, bytes] = {}
            canonical_names: set[str] = set()
            for info in package.infolist():
                name = info.filename
                canonical = PurePosixPath(name).as_posix()
                unix_mode = (info.external_attr >> 16) & 0o170000
                if (
                    not name
                    or name.startswith("/")
                    or "\\" in name
                    or canonical != name
                    or canonical in canonical_names
                    or canonical not in _ALLOWED_TEAMS_ARCHIVE_ENTRIES
                    or info.is_dir()
                    or info.flag_bits & 0x1
                    or unix_mode == stat.S_IFLNK
                    or info.file_size > _MAX_TEAMS_PACKAGE_BYTES
                ):
                    raise DeploymentPlanError(
                        "downloaded Teams package archive is invalid"
                    )
                canonical_names.add(canonical)
                records[canonical] = package.read(info)
            if "manifest.json" not in records:
                raise DeploymentPlanError(
                    "downloaded Teams package is missing a valid manifest"
                )
            payload = json.loads(records["manifest.json"].decode("utf-8"))
    except DeploymentPlanError:
        raise
    except (
        OSError,
        zipfile.BadZipFile,
        KeyError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise DeploymentPlanError(
            "downloaded Teams package is missing a valid manifest"
        ) from exc
    if not isinstance(payload, dict):
        raise DeploymentPlanError("downloaded Teams manifest must be an object")
    app_id = payload.get("id")
    version = payload.get("version")
    manifest_version = payload.get("manifestVersion")
    if not isinstance(app_id, str) or not _GUID_RE.fullmatch(app_id):
        raise DeploymentPlanError("downloaded Teams manifest app id is invalid")
    if not isinstance(version, str) or not _TEAMS_VERSION_RE.fullmatch(version):
        raise DeploymentPlanError("downloaded Teams manifest version is invalid")
    if (
        not isinstance(manifest_version, str)
        or not _TEAMS_MANIFEST_VERSION_RE.fullmatch(manifest_version)
    ):
        raise DeploymentPlanError("downloaded Teams manifestVersion is invalid")
    if (
        not set(payload).issubset(_ALLOWED_TEAMS_MANIFEST_FIELDS)
        or any(
            field in payload and payload.get(field) not in (None, [], {}, "")
            for field in _FORBIDDEN_TEAMS_CAPABILITY_FIELDS
        )
    ):
        raise DeploymentPlanError(
            "downloaded Teams manifest contains unapproved fields or capabilities"
        )
    icons = payload.get("icons")
    if icons is not None:
        if (
            not isinstance(icons, dict)
            or set(icons) != {"color", "outline"}
            or icons.get("color") != "color.png"
            or icons.get("outline") != "outline.png"
        ):
            raise DeploymentPlanError("downloaded Teams manifest icons are invalid")
        for icon_name in ("color.png", "outline.png"):
            if not records.get(icon_name, b"").startswith(_PNG_SIGNATURE):
                raise DeploymentPlanError("downloaded Teams package icon is invalid")
    elif any(name != "manifest.json" for name in records):
        raise DeploymentPlanError("downloaded Teams package has unreferenced icons")
    return app_id.lower(), version, hashlib.sha256(package_bytes).hexdigest()


def _stable_teams_package_bytes(path: Path) -> bytes:
    descriptor = -1
    try:
        named_before = path.lstat()
        descriptor = os.open(
            path,
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0),
        )
        opened = os.fstat(descriptor)
        identity = (
            opened.st_dev, opened.st_ino, opened.st_mode, opened.st_size,
            opened.st_mtime_ns, opened.st_ctime_ns,
        )
        if (
            stat.S_ISLNK(named_before.st_mode)
            or not stat.S_ISREG(opened.st_mode)
            or (named_before.st_dev, named_before.st_ino)
            != (opened.st_dev, opened.st_ino)
            or opened.st_size < 1
            or opened.st_size > _MAX_TEAMS_PACKAGE_BYTES
        ):
            raise DeploymentPlanError(
                "downloaded Teams package must be one stable regular file"
            )
        chunks: list[bytes] = []
        remaining = opened.st_size
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                raise DeploymentPlanError(
                    "downloaded Teams package changed while reading"
                )
            chunks.append(chunk)
            remaining -= len(chunk)
        final = os.fstat(descriptor)
        named_after = path.lstat()
        final_identity = (
            final.st_dev, final.st_ino, final.st_mode, final.st_size,
            final.st_mtime_ns, final.st_ctime_ns,
        )
        named_identity = (
            named_after.st_dev, named_after.st_ino, named_after.st_mode,
            named_after.st_size, named_after.st_mtime_ns, named_after.st_ctime_ns,
        )
        if identity != final_identity or final_identity != named_identity:
            raise DeploymentPlanError(
                "downloaded Teams package changed while reading"
            )
        return b"".join(chunks)
    except DeploymentPlanError:
        raise
    except OSError as exc:
        raise DeploymentPlanError(
            "downloaded Teams package stable read failed"
        ) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _page_exists(payload: Any) -> bool:
    for item in _object_items(payload):
        for field_name in ("Name", "FileName", "FileLeafRef", "Url", "ServerRelativeUrl"):
            value = _string_field(item, field_name)
            if value.lower() == PAGE_NAME.lower() or value.lower().endswith("/" + PAGE_NAME.lower()):
                return True
    return False


def _page_readback_is_visible(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    return any(
        _has_field(payload, field)
        for field in ("controls", "canvasContentJson", "CanvasContent1", "Name", "FileName")
    )


def _page_publish_readback_is_ready(payload: Any) -> bool:
    if not _page_readback_is_visible(payload):
        return False
    for field in ("Published", "IsPublished"):
        if _has_field(payload, field):
            return _field(payload, field) is True
    if not _has_field(payload, "Level"):
        return False
    level = _field(payload, "Level")
    return isinstance(level, str) and level.strip().lower() == "published"


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


def _required_guid(payload: Any, name: str, label: str) -> str:
    value = _required_string(payload, name, label)
    if not _GUID_RE.fullmatch(value):
        raise DeploymentPlanError(f"{label} is not a valid GUID")
    return value.lower()


def _teams_catalog_detail_url(teams_catalog_id: str) -> str:
    if not _GUID_RE.fullmatch(teams_catalog_id):
        raise DeploymentPlanError("Teams catalog detail URL requires a validated GUID")
    return (
        "https://graph.microsoft.com/v1.0/appCatalogs/teamsApps/"
        f"{teams_catalog_id.lower()}?$expand=appDefinitions"
    )


def _teams_installed_apps_url(teams_manifest_app_id: str) -> str:
    if not _GUID_RE.fullmatch(teams_manifest_app_id):
        raise DeploymentPlanError("Teams installed-app URL requires a validated manifest GUID")
    return (
        f"https://graph.microsoft.com/v1.0/teams/{TEAM_ID}/installedApps?"
        f"$filter=teamsApp/externalId%20eq%20'{teams_manifest_app_id.lower()}'"
        "&$expand=teamsApp"
    )


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
