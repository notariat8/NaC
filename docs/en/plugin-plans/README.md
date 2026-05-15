# Plugin Plans

## Purpose

This directory describes the local plugin and connector plans for NoC. The
plans are deliberately maintained as Markdown sources so they remain reviewable,
versioned and readable without a proprietary runtime.

## Basic Decision

NoC runs locally:

- Workspace: `~/NoC` in Ubuntu WSL.
- Git source: `https://github.com/ofunk/NoC.git`.
- Codex, OCI CLI, GitHub CLI and domain integrations are installed locally.
- Omnistation is not an execution location for NoC.
- Remote hosts may only be used for non-critical research.

This decision avoids breaks around GitHub authentication, browser callbacks, OCI
configuration and local domain integrations.

## Plan Families

| Plan | Purpose | Day 0 | Day 1 | Day 2 |
| --- | --- | --- | --- | --- |
| [local-codex-runtime.md](local-codex-runtime.md) | Local Codex/LLM workstation | Workspace and startup check | Local plan generation | Regular tool and policy checks |
| [github-control-plane.md](github-control-plane.md) | GitHub as GitOps control plane | Auth and repository access | PRs, checks, reviews | Branch protection, audit, drift |
| [idaas-plugin-integration.md](idaas-plugin-integration.md) | German eID verification and IAM projection planning | Purpose, tenant, claim set, privacy basis | eID/IAM plan preview and contract check | Assertions, revocations, retention drift, connector recertification |
| [oci-infrastructure.md](oci-infrastructure.md) | OCI CLI/MCP and Resource Manager | API key and CLI | Stacks, eventstream, evidence | Drift, rotation, cost control |
| [domain-connector-runtime.md](domain-connector-runtime.md) | Domain-system connectors | Contract model | Plan/apply/reconcile | Monitoring, replays, exit |
| [handelsregister-online-anmeldung.md](handelsregister-online-anmeldung.md) | HRA-first online commercial-register filing | Register track, legal form, eID/app and notary route | Filing-package plan and evidence checklist | Rejections, signature/identity errors, package versions |
| [handelsregister-bundesapi.md](handelsregister-bundesapi.md) | Deprecated commercial-register retrieval spike, not the current plugin path | Usage and license check | Dry-run research plan | Rate limits, source switch, audit |
| [bnotk-xnp-notariatssoftware.md](bnotk-xnp-notariatssoftware.md) | XNP/notary-software local companion | Card/SAK gate, workstation and interface check | Local plan/apply companion | Local logs, evidence, update maintenance |
| [bea-portal-plugin-integration.md](bea-portal-plugin-integration.md) | beA portal and client-security companion | Local beA prerequisites | Send/receive/eEB workflow | Incidents, versions, evidence |
| [elster-developer-plugin-integration.md](elster-developer-plugin-integration.md) | ELSTER/ERiC developer and local companion | Manufacturer/tooling check | Dry-run filing and evidence plans | ERiC versions, evidence, deadlines |
| [cyberjack-rfid-plugin-integration.md](cyberjack-rfid-plugin-integration.md) | Card/SAK gate before XNP login | Card, reader, PC/SC, SAK lite, secureFramework | Card/SAK readiness for XNP test | Firmware, driver, card path, evidence |
| [grundbuch-portal-plugin-integration.md](grundbuch-portal-plugin-integration.md) | Land-register portal workflow and evidence companion | Authorization and legitimate interest | Retrieval plan and evidence import | Federal-state drift, logs, fees |

## Sequence For Commercial Register / HRA Workflows

The first technical building block depends on the operating mode:

- Citizen or client preflight: `noc-handelsregister` may only structure
  readiness, missing information and notary appointment preparation.
- Notary-side execution or filing-adjacent workflow: `noc-cyberjack-rfid` comes
  first, because XNP login cannot be tested without card, reader, SAK lite or
  XNP card path and secureFramework.
- Then `noc-bnotk-xnp` follows. Only after local XNP login, official-capacity
  context, XNotar module and exchange folder are clarified may
  `noc-handelsregister` build the domain register layer on top.

Therefore HRA is not the first technical integration point. It is the first
domain layer above the card/SAK gate and the notary/XNP gate.

## Binding Adapter Pattern

Each plugin or connector plan follows this flow:

1. Capture intent.
2. Validate schema and policy.
3. Generate a plan preview.
4. Obtain human approval.
5. Execute idempotently.
6. Write audit evidence.
7. Make drift visible.
8. Document exit and replacement path.

## Security Boundaries

- No secrets, tokens, private keys or real personal data in the repository.
- Local credentials stay in local stores (`~/.oci`, Git Credential Manager,
  browser/OAuth stores).
- Adapters must not write around policies.
- Sensitive processes require four-eyes approval.
- Every durable manual intervention must be reconciled in Git.

## Status Model

Plugin plans use these status values:

- `draft`: subject matter sketched, not released for implementation.
- `proposed`: implementation-adjacent, but not yet reviewed.
- `approved`: approved for pilot implementation.
- `active`: used in a pilot or production flow.
- `deprecated`: replaced, retained only for traceability.

## Local Regeneration Flow

```bash
cd ~/NoC
git pull
python3 scripts/startup_check.py --ide auto --run-tests
```

If the startup check fails, the errors are documented and not bypassed through
remote execution. Afterwards the Markdown plans are adjusted locally, checked,
committed and pushed.

## Open Local Prerequisites

The current local startup check still expects:

- `python` as an alias or command in addition to `python3`.
- `gh` for GitHub operations.
- VS Code extensions `github.copilot` and `github.copilot-chat` when VS Code is
  the target IDE.
- Package installation or `PYTHONPATH=src` so `business_os` can be found in
  tests.
- Optional `pandoc` for manual PDF exports only.

These items are local tooling tasks, not Omnistation tasks.
