#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_m365_graph.auth import GraphConfig, GraphConfigError, runtime_token_provider_from_env, token_provider_from_env  # noqa: E402
from nac_m365_graph.graph_client import GraphHttpError, GraphRestClient  # noqa: E402
from nac_m365_graph.privileged_apply import apply_privileged_change_path  # noqa: E402
from nac_m365_graph.privileged_change import (  # noqa: E402
    DEFAULT_PRIVILEGED_CHANGE_CONFIG,
    DEFAULT_PROVISIONED_STATE,
    build_privileged_change_plan,
    load_privileged_change_config,
    load_provisioned_state,
    summarize_privileged_change_plan,
    validate_privileged_change_config,
)
from nac_m365_graph.provisioner import build_plan, summarize_plan  # noqa: E402
from nac_m365_graph.mcp_runtime import (  # noqa: E402
    DEFAULT_MCP_CONTRACT,
    build_tool_manifest,
    load_mcp_contract,
    validate_mcp_contract,
)
from nac_m365_graph.runtime_metadata import build_runtime_metadata_snapshot  # noqa: E402
from nac_m365_graph.runtime_smoke import run_runtime_site_smoke  # noqa: E402
from nac_m365_graph.schema import DEFAULT_SCHEMA, load_schema, validate_schema  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Teams/SharePoint MVP data-plane provisioner using Microsoft Graph REST only."
    )
    parser.add_argument(
        "command",
        choices=[
            "validate",
            "plan",
            "privileged-plan",
            "privileged-apply",
            "runtime-smoke",
            "runtime-metadata",
            "mcp-manifest",
            "mcp-stdio",
            "apply",
            "drift",
            "export",
        ],
        help=(
            "Provisioning command. validate, plan and privileged-plan run without Microsoft 365 credentials; "
            "privileged-apply, runtime-smoke and runtime-metadata are owner-gated and use Graph REST only. "
            "mcp-stdio starts the offline local MCP adapter."
        ),
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA,
        help="Path to the declarative Teams/SharePoint schema.",
    )
    parser.add_argument(
        "--owner-approved",
        action="store_true",
        help="Required for live-affecting commands. Does not bypass missing credentials.",
    )
    parser.add_argument(
        "--privileged-config",
        type=Path,
        default=DEFAULT_PRIVILEGED_CHANGE_CONFIG,
        help="Path to the application-owned privileged change path config.",
    )
    parser.add_argument(
        "--provisioned-state",
        type=Path,
        default=DEFAULT_PROVISIONED_STATE,
        help="Path to the non-secret provisioned Teams/SharePoint state export.",
    )
    parser.add_argument(
        "--mcp-contract",
        type=Path,
        default=DEFAULT_MCP_CONTRACT,
        help="Path to the teams-sharepoint-data-mcp contract.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "mcp-stdio":
        from nac_m365_graph.mcp_stdio import run_stdio_server

        return run_stdio_server(
            contract_path=args.mcp_contract,
            provisioned_state_path=args.provisioned_state,
        )

    if args.command == "mcp-manifest":
        contract = load_mcp_contract(args.mcp_contract)
        errors = validate_mcp_contract(contract)
        if errors:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": errors,
                },
                as_json=args.json,
                return_code=1,
            )
        return _emit(
            {
                "status": "PASSED",
                "summary": {
                    "server_id": contract["server_id"],
                    "tool_count": len(contract["tools"]),
                    "executes_graph_requests": contract["runtime_boundary"]["executes_graph_requests"],
                },
                "result": build_tool_manifest(contract),
            },
            args.json,
        )

    if args.command in {"runtime-smoke", "runtime-metadata"}:
        state = load_provisioned_state(args.provisioned_state)
        schema = load_schema(args.schema)
        errors = validate_schema(schema)
        if errors:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": errors,
                },
                as_json=args.json,
                return_code=1,
            )
        if not args.owner_approved:
            return _emit(
                {
                    "status": "BLOCKED",
                    "errors": [f"{args.command} requires --owner-approved"],
                },
                args.json,
                return_code=2,
            )
        try:
            client = GraphRestClient(runtime_token_provider_from_env())
            if args.command == "runtime-smoke":
                result = run_runtime_site_smoke(client, state, schema)
            else:
                result = build_runtime_metadata_snapshot(client, state, schema)
        except GraphConfigError as exc:
            return _emit(
                {
                    "status": "BLOCKED",
                    "errors": [str(exc)],
                },
                args.json,
                return_code=2,
            )
        except (GraphHttpError, RuntimeError, KeyError) as exc:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": [str(exc)],
                },
                args.json,
                return_code=1,
            )
        return _emit(
            {
                "status": result["status"],
                "summary": result["summary"],
                "result": result,
            },
            args.json,
        )

    if args.command in {"privileged-plan", "privileged-apply"}:
        config = load_privileged_change_config(args.privileged_config)
        state = load_provisioned_state(args.provisioned_state)
        errors = validate_privileged_change_config(config)
        if errors:
            return _emit(
                {
                    "status": "FAILED",
                    "errors": errors,
                },
                as_json=args.json,
                return_code=1,
            )
        if args.command == "privileged-apply":
            if not args.owner_approved:
                return _emit(
                    {
                        "status": "BLOCKED",
                        "errors": ["privileged-apply requires --owner-approved"],
                    },
                    args.json,
                    return_code=2,
                )
            try:
                client = GraphRestClient(token_provider_from_env())
                result = apply_privileged_change_path(client, config, state)
            except (GraphConfigError, GraphHttpError, RuntimeError, KeyError) as exc:
                return _emit(
                    {
                        "status": "FAILED",
                        "errors": [str(exc)],
                    },
                    args.json,
                    return_code=1,
                )
            return _emit(
                {
                    "status": result["status"],
                    "summary": {
                        "applications": len(result["applications"]),
                        "team_owner_checks": len(result["teamOwnerChecks"]),
                        "site_permissions": len(result["sitePermissions"]),
                    },
                    "result": result,
                },
                args.json,
            )
        plan = build_privileged_change_plan(config, state)
        return _emit(
            {
                "status": "PASSED",
                "summary": summarize_privileged_change_plan(plan),
                "operations": [operation.to_dict() for operation in plan],
            },
            args.json,
        )

    schema = load_schema(args.schema)
    errors = validate_schema(schema)
    if errors:
        return _emit(
            {
                "status": "FAILED",
                "errors": errors,
            },
            as_json=args.json,
            return_code=1,
        )

    if args.command == "validate":
        return _emit({"status": "PASSED", "message": "schema is valid"}, args.json)

    plan = build_plan(schema)
    if args.command == "plan":
        return _emit(
            {
                "status": "PASSED",
                "summary": summarize_plan(plan),
                "operations": [operation.to_dict() for operation in plan],
            },
            args.json,
        )

    if not args.owner_approved:
        return _emit(
            {
                "status": "BLOCKED",
                "errors": [f"{args.command} requires --owner-approved"],
            },
            args.json,
            return_code=2,
        )

    try:
        GraphConfig.from_env()
    except GraphConfigError as exc:
        return _emit(
            {
                "status": "BLOCKED",
                "errors": [str(exc)],
            },
            args.json,
            return_code=2,
        )

    return _emit(
        {
            "status": "BLOCKED",
            "errors": [
                f"{args.command} is intentionally blocked in the MVP skeleton until the first owner-gated live Graph REST smoke is approved."
            ],
            "planned_operations": summarize_plan(plan),
        },
        args.json,
        return_code=2,
    )


def _emit(payload: dict, as_json: bool, return_code: int = 0) -> int:
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return return_code

    print(f"STATUS: {payload['status']}")
    if payload.get("message"):
        print(payload["message"])
    if payload.get("summary"):
        print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))
    if payload.get("result"):
        print(json.dumps(payload["result"], indent=2, ensure_ascii=False))
    for error in payload.get("errors", []):
        print(f"ERROR: {error}")
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
