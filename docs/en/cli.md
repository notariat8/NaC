# NaC CLI: Technical Control Surface Behind The Office UI

Status: first unified CLI implemented on 2026-05-19

## Idea

The NaC CLI is not the product surface for a notary office. It is the
technical control and validation layer behind the local office UI, Codex
plugins and later automations.

For subject-matter users, NaC starts with the local operator web app:

```bash
python scripts/nac.py operator --open
```

The CLI remains important because it makes the same checks reproducible:
status, quality gate, BPMN, knowledge graphs, plugins and configuration.

The shared entry point is:

```bash
nac
```

Without installation, the same entry point can be started from the repository:

```bash
python scripts/nac.py status
```

After a local editable installation, the short command is available:

```bash
python -m pip install -e .
nac status
```

## Why This Still Matters For Non-Technical Readers

A CLI is a clearly named work order for the computer. A notary does not need
to memorize these commands. The office benefits because every button, plugin
action and automated check can be traced back to a checkable technical action.

| Question | Answer |
| --- | --- |
| Does the notary need to memorize commands? | No. The visible entry point is the office UI; the CLI is the technical validation surface behind it. |
| Why not only a web UI? | A UI alone can hide logic. The CLI keeps checks, results and repetition visible. |
| Why is this future-ready? | Local web app, Codex plugin, CI and later apps can reuse the same reviewed runtime. |
| What becomes traceable? | Command, input, result, review and Git change. |

## First Commands

```bash
python scripts/nac.py status
python scripts/nac.py doctor --profile strict
python scripts/nac.py web
python scripts/nac.py kg status
python scripts/nac.py kg cost-view immobilienkaufvertrag
python scripts/nac.py kg workflow-contract immobilienkaufvertrag
python scripts/nac.py kg pilot-checklist online-gmbh-gruendung
python scripts/nac.py legal-graph status
python scripts/nac.py legal-graph model-card-proposal
python scripts/nac.py legal-graph ai-sbom-delta-proposal
python scripts/nac.py ai-sbom export-mapping
python scripts/nac.py gnotkg quote --business-value 500000 --table A --fee-rate 1.0 --kv-number 21100
python scripts/nac.py bpmn validate
python scripts/nac.py config list
python scripts/nac.py m365 teams-sharepoint privileged-plan --format json
python scripts/nac.py m365 teams-sharepoint runtime-smoke --owner-approved --format json
python scripts/nac.py m365 teams-sharepoint runtime-metadata --owner-approved --format json
python scripts/nac.py plugins actions
python scripts/nac.py tenant domain-check --domain kanzlei-notariat.example --tenant-slug kanzlei-notariat --admin-email admin@kanzlei-notariat.example
python scripts/nac.py import jobs status --repo ../demo8notariat
python scripts/nac.py time-ledger summary
```

After installation:

```bash
nac status
nac doctor --profile strict
nac web
nac kg status
nac kg cost-view immobilienkaufvertrag
nac kg workflow-contract immobilienkaufvertrag
nac kg pilot-checklist online-gmbh-gruendung
nac legal-graph status
nac legal-graph model-card-proposal
nac legal-graph ai-sbom-delta-proposal
nac ai-sbom export-mapping
nac gnotkg quote --business-value 500000 --table A --fee-rate 1.0 --kv-number 21100
nac bpmn validate
nac config list
nac m365 teams-sharepoint privileged-plan --format json
nac m365 teams-sharepoint runtime-smoke --owner-approved --format json
nac m365 teams-sharepoint runtime-metadata --owner-approved --format json
nac plugins actions
nac tenant domain-check --domain kanzlei-notariat.example --tenant-slug kanzlei-notariat --admin-email admin@kanzlei-notariat.example
nac tenant customer-plan --domain kanzlei-notariat.example --tenant-slug kanzlei-notariat --admin-email admin@kanzlei-notariat.example --saas-admin-email saas-owner@example.com --format json
nac tenant status --repo ../demo8notariat
nac import jobs status --repo ../demo8notariat
nac qms status
nac time-ledger summary
```

## Technical Operating Areas

| Area | Command | Purpose |
| --- | --- | --- |
| Overview | `nac status` | Shows usecases, open required information, BPMN models and configuration files. |
| Quality | `nac doctor --profile strict` | Runs the strict quality gate. |
| Office UI | `nac operator --open` | Starts the local operator web app with cases, checklists, BPMN, editor and workstation tests. |
| Graphical model view | `nac web` | Starts the local web server for BPMN and KG views. |
| Knowledge graphs | `nac kg status`, `nac kg workflow-contract <slug>` and `nac kg pilot-checklist <slug>` | Shows the state of usecase-local knowledge graphs, creates mandate-data-free workflow contract drafts and builds deterministic pilot intake checklists from a usecase KG. |
| Legal graph | `nac legal-graph status`, `nac legal-graph sources`, `nac legal-graph source-inventory`, `nac legal-graph model-card-proposal`, `nac legal-graph ai-sbom-delta-proposal`, `nac legal-graph review erbrecht` and `nac legal-graph update-dry-run erbrecht` | Shows the mandate-data-free legal graph, primary sources, source-inventory/license/TDM gates, model-card and AI-SBOM delta proposals, review points and update patches without auto-merge. |
| AI-SBOM | `nac ai-sbom export-mapping` | Shows the selected CycloneDX/SPDX export mapping without enabling release export, external tool execution, mandate data or secrets. |
| GNotKG cost review | `nac kg cost-view <slug>` and `nac gnotkg quote` | Shows the mandate-data-free cost review view and calculates local technical cost drafts. |
| BPMN | `nac bpmn list` and `nac bpmn validate` | Lists and validates subject-matter BPMN process models. |
| Processes | `nac process validate-all` | Validates deterministic process requests. |
| Workflow contracts | `nac contracts validate` | Validates workflow contracts, spec traceability, secure-link boundaries, Teams/SharePoint Graph data plane and legal-research connector candidates. |
| Microsoft 365 | `nac m365 teams-sharepoint plan`, `nac m365 teams-sharepoint privileged-plan`, `nac m365 teams-sharepoint privileged-apply --owner-approved`, `nac m365 teams-sharepoint runtime-smoke --owner-approved`, `nac m365 teams-sharepoint runtime-metadata --owner-approved`, `nac batch-approval m365`, `nac m365 teams-sharepoint mcp-manifest` and `nac m365 teams-sharepoint mcp-stdio` | Plans the Teams/SharePoint data plane, runs the privileged app/Sites.Selected bootstrap only owner-gated through Microsoft Graph REST v1.0, verifies runtime-app read access to sites, lists and document libraries without reading list items, renders batch approval text without live access, shows the safe `teams-sharepoint-data-mcp` tool manifest without live access, starts the local MCP stdio adapter for request planning and cleans synthetic smoke leftovers only owner-gated. |
| Import jobs | `nac import jobs status --repo ../demo8notariat` | Controls bounded Codex/OCR jobs for import proposals in the separate data repository. |
| Plugins | `nac plugins actions` and `nac plugins install --mode dry-run` | Lists subject-matter plugin commands and checks local plugin mirroring. |
| Configuration | `nac config list` and `nac config validate` | Shows and validates policies, contracts and runtime configuration. |
| Data repository | `nac tenant status --repo ../demo8notariat` | Checks a separate NaC data repository for demo or later production data. |
| Tenant onboarding | `nac tenant domain-check` and `nac tenant customer-plan` | Checks new-customer domains and creates the Entra/M365/SharePoint plan without productive Graph writes. |
| QMS | `nac qms status` and `nac qms evidence --repo ../demo8notariat` | Shows ISO 9001/QMS artifacts and evidence counts from the data repository. |
| Codex Time Ledger | `nac time-ledger add`, `nac time-ledger run` and `nac time-ledger summary` | Records agentic work blocks and summarizes tool time, approvals, waiting time, local CPU/I/O and estimated LLM time. |

## Codex Time Ledger

The Time Ledger is the local measurement layer for longer Codex sessions. It
writes completed work blocks as JSONL under
`out/observability/codex-time-ledger.jsonl` and summarizes them by category and
phase.

```bash
nac time-ledger add --session-id 2026-06-15-nac --task "NaC Time Ledger" --phase context-read --category local_io --started-at 2026-06-15T10:00:00Z --ended-at 2026-06-15T10:08:00Z
nac time-ledger run --session-id 2026-06-15-nac --task "NaC Time Ledger" --phase unit-tests --category local_cpu -- python -m unittest tests/test_codex_time_ledger.py
nac time-ledger summary --session-id 2026-06-15-nac
```

Usage and privacy boundaries are documented in
[operations/codex-time-ledger.md](operations/codex-time-ledger.md).

## `nac legal-graph`

This command controls the mandate-data-free NaC legal graph. The first MVPs are
inheritance law, family law and corporate law. Automatic source runs only
create review patches; a merge requires professional review.

```bash
nac legal-graph status
nac legal-graph sources --format json
nac legal-graph source-inventory --format json
nac legal-graph model-card-proposal --format json
nac legal-graph ai-sbom-delta-proposal --format json
nac legal-graph review erbrecht --format json
nac legal-graph update-dry-run erbrecht --format json
```

The first update pilot uses a primary-source manifest for inheritance law with
`metadata_only_fixture`, `commentary_access_allowed=false`,
`provider_query_allowed=false` and `credentials_required=false`. This keeps
commentaries and publisher databases outside the run until a licensed MCP/API
connector is professionally, contractually and technically approved.

Licensed commentaries and publisher sources do not use scraping or full-text
imports. They require reviewed MCP/API connectors with license, AVV/DPA,
professional-secrecy, AI-SBOM and review gates.

The model-card proposal is also metadata-only. It shows which sections,
candidates and blocks must be reviewed before later Legal-Nemotron use; it
does not start training, publish a checkpoint or claim legal-answer quality.

The AI-SBOM delta proposal has the same boundary. It shows later components,
candidates, attestations and blocks, but activates no runtime, endpoint,
training, evaluation or checkpoint.

## `nac ai-sbom`

This command shows repository-wide AI-SBOM governance artifacts. The current
export mapping selects CycloneDX JSON and SPDX JSON as target profiles, but it
does not enable release export and does not execute external SBOM tools.

```bash
nac ai-sbom export-mapping --format json
```

Release binding, tool execution and published artifacts need a separate owner
apply gate.

## QMS And ISO 9001 Layer

NaC contains a QMS layer under [qms/](../../qms). It maps quality policy,
quality objectives, roles, process map, internal audits, management review and
nonconformities to NaC artifacts.

```bash
nac qms status
nac qms iso9001-map
nac qms audit-plan
nac qms evidence --repo ../demo8notariat
```

## Separate Data Repository

NaC does not write case and test data into the product repository. Synthetic
demo data lives in a separate data repository, for example `../demo8notariat`:

```bash
nac tenant init --repo ../demo8notariat --name demo8notariat --remote-url https://github.com/notariat8/demo8notariat.git
nac tenant write-sample-akte --repo ../demo8notariat --akten-id UVZ-2026-0001
nac tenant list-akten --repo ../demo8notariat
nac tenant show-akte --repo ../demo8notariat --akten-id UVZ-2026-0001
nac tenant write-demo immobilienkaufvertrag --repo ../demo8notariat --case-id DEMO-2026-0001
```

## Tenant Identity And M365 Graph Plan

New customers do not start in a cloud console. NaC first checks whether the
customer domain and initial admin email match:

```bash
nac tenant domain-check --domain kanzlei-notariat.example --tenant-slug kanzlei-notariat --admin-email admin@kanzlei-notariat.example --format json
```

NaC then creates an M365/SharePoint plan. This command does not write to
Microsoft Graph and contains no credentials:

```bash
nac tenant customer-plan --domain kanzlei-notariat.example --tenant-slug kanzlei-notariat --admin-email admin@kanzlei-notariat.example --saas-admin-email saas-owner@example.com --format json
```

Productive Graph changes then run through the M365 operating edge and require
an owner gate:

```bash
nac m365 teams-sharepoint privileged-plan --format json
nac m365 teams-sharepoint runtime-smoke --owner-approved --format json
nac m365 teams-sharepoint mcp-manifest --format json
nac batch-approval m365 --batch-pr 383 --batch-pr 385 --format json
nac m365 teams-sharepoint mcp-stdio
nac m365 teams-sharepoint mcp-stdio --owner-approved --mcp-live-read
nac m365 teams-sharepoint mcp-live-read-smoke --owner-approved --mcp-smoke-tool case_get --mcp-smoke-case-id <case-id> --format json
nac m365 teams-sharepoint mcp-positive-write-read-smoke --owner-approved --format json
nac m365 teams-sharepoint mcp-smoke-cleanup --owner-approved --mcp-smoke-case-id <case-id> --format json
nac m365 teams-sharepoint mcp-smoke-suite --owner-approved --mcp-suite-cleanup --format json
nac m365 teams-sharepoint mcp-smoke-leftover-cleanup --owner-approved --mcp-leftover-dry-run --format json
nac m365 teams-sharepoint mcp-smoke-leftover-cleanup --owner-approved --format json
```

`runtime-smoke` and `runtime-metadata` read only Graph REST metadata and compare
the discovered lists and document libraries against the declarative MVP schema.
`mcp-manifest` is offline and only emits the planned runtime tools, gates and
Graph REST boundaries. `mcp-stdio` is also offline and speaks newline-delimited
JSON-RPC over stdin/stdout. `tools/call` only plans Microsoft Graph v1.0
requests and does not execute requests.
`nac batch-approval m365` is offline as well. The command renders copyable
owner approval texts for prepared PR batches and synthetic live-smoke batches,
but performs no GitHub or Microsoft Graph write action.

`mcp-stdio --owner-approved --mcp-live-read` additionally enables live reads for
`case_get` and `document_list`. Runtime credentials must be set outside the
repository, for example through `M365_RUNTIME_GRAPH_ACCESS_TOKEN_FILE` or
through `M365_TENANT_ID`, `M365_RUNTIME_CLIENT_ID` and
`M365_RUNTIME_CLIENT_SECRET`. For the preferred certificate-based runtime path,
set `M365_TENANT_ID`, `M365_RUNTIME_CLIENT_ID`,
`M365_RUNTIME_CLIENT_CERTIFICATE_PATH` and `M365_RUNTIME_CLIENT_KEY_PATH`; for
an encrypted key also set `M365_RUNTIME_CLIENT_KEY_PASSWORD`. Write tools are
not executed in this mode.

`mcp-live-read-smoke` executes exactly one owner-gated live read and writes the
redacted artifact
`out/m365/teams-sharepoint/mcp-live-read-smoke.redacted.json`. The artifact
contains no raw Graph response, no cleartext case ID, no Graph path, no field
values and no tokens or secrets.

`mcp-positive-write-read-smoke` writes exactly one synthetic `Akten` row with
the `NAC-SMOKE-WRITE-READ-` prefix and reads the same matter back. The
standalone command is useful only when the related cleanup path is explicitly
prepared. For regular runtime evidence, prefer
`mcp-smoke-suite --mcp-suite-cleanup` because it verifies write, read and
cleanup in the same owner-gated run.

`mcp-smoke-cleanup` deletes exactly one synthetic smoke matter named by
case ID. The case ID must start with `NAC-SMOKE-WRITE-READ-`; other matches are
refused.

`mcp-smoke-suite` creates a synthetic case ID only in process memory, executes
write and read, and deletes the same matter in the same run when
`--mcp-suite-cleanup` is set. It is the standard runtime evidence after
MCP/runtime changes, but remains owner-gated because it writes and deletes in
the live tenant.

`mcp-smoke-leftover-cleanup` finds and deletes only synthetic `Akten` list items
whose `NacCaseId` starts with `NAC-SMOKE-WRITE-READ-`. The command refuses
pagination and non-smoke results before any delete. With `--mcp-leftover-dry-run`
it only reads the owner-gated match count. The redacted artifact is written to
`out/m365/teams-sharepoint/mcp-smoke-leftover-cleanup.redacted.json`.

OCI/ATP is archived for the MVP and is not an active CLI operating edge.

The leading matter model uses small JSON files with stable IDs for matters,
people, documents, events and indices. PDF, JPG and other binary files live as
ordinary files next to their metadata. The separation is documented in
[datenrepo-demo8notariat.md](datenrepo-demo8notariat.md).
The subject-matter derivation from common notary-software building blocks is in
[notarsoftware-datenmodell.md](notarsoftware-datenmodell.md).

## Workflow Contracts, Secure Document Links And Connector Candidates

Workflow contracts describe which operating edge may trigger which
subject-matter actions and which evidence is mandatory. The Secure Document
Link contract bounds mobile apps and authenticated web apps to short-lived,
revocable, matter- and purpose-bound upload or read links. The Legal Research
Connector contract records external legal research, MCP and publisher-database
references only as candidates until license, DPA, AI-SBOM, security boundary
and human review are settled.
The legal graph contract limits legal graph updates for inheritance law,
family law and corporate law to mandate-data-free primary sources and review
patches; the commentary connector contract requires licensed MCP/API access
without credentials, mandate data or commentary full text in the product
repository and records provider-level license status, evidence fields, output
boundaries, activation gates, license basis, DPA status, professional-secrecy
status, AI-SBOM status, security boundary and credential operating model.
Primary-source manifests are also validated as a separate artifact type so an
update run cannot introduce commentary access, provider queries or credential
requirements.
The source-inventory, license and TDM gate is visible through
`nac legal-graph source-inventory --format json`. The command only reads the
gate contract, shows no source text, generates no benchmark dataset and starts
no training. For each source it also reports review depth for seed metadata,
license/TDM, attribution, storage boundary and the next review.
The spec traceability contract connects issue, spec, plan, AC IDs and
validation commands for spec-driven work.

```bash
nac contracts validate
```

The GNotKG cost contract is validated there as well. The source basis is
[GNotKG section 3](https://www.gesetze-im-internet.de/gnotkg/__3.html),
[GNotKG section 34](https://www.gesetze-im-internet.de/gnotkg/__34.html),
[GNotKG section 35](https://www.gesetze-im-internet.de/gnotkg/__35.html),
[annex 1](https://www.gesetze-im-internet.de/gnotkg/anlage_1.html) and
[annex 2](https://www.gesetze-im-internet.de/gnotkg/anlage_2.html).
`nac gnotkg quote` stores no entered values; final notarial cost review
remains a review gate.

The check ensures that the contract requires purpose, expiry, matter binding,
storage target, revocation and audit evidence, that spec manifests carry valid
AC IDs and validation commands, and that connector candidates contain no
tracking URLs, credentials, mandate data or productive integration levels. The
target model is described in the
[Authenticated Web-App Operating Model](authenticated-webapp-operating-model.md)
and the
[Legal Research Connector backlog](plugin-plans/legal-research-connectors.md).

## Import Jobs For Codex And OCR

The inbox channel separates upload, machine extraction and subject-matter
acceptance. The web app first creates an import proposal with staged test files
in the data repository. It then creates a bounded import job under
`eingang/jobs/`. Codex or the CLI processes that job metadata-only and writes a
reviewable result to `eingang/extraktionen/`.

```bash
nac import jobs create --repo ../demo8notariat --proposal-id IMP-20260521-BEISPIEL
nac import jobs status --repo ../demo8notariat
nac import jobs process --repo ../demo8notariat --job-id JOB-20260521-BEISPIEL --format json
nac import jobs apply-result --repo ../demo8notariat --job-id JOB-20260521-BEISPIEL
```

`apply-result` only merges the extraction result back into the import proposal
and marks it for human review. Only the visible `Übernehmen` action in the
operator web app creates a demo matter from it. For real OCR, AI or SaaS
processing with personal data, DPA, role, permission and data-storage
boundaries remain mandatory.

## Plugin Commands

Plugin management and the existing local plugin checks now also run through
`nac`:

```bash
nac plugins actions
nac plugins status
nac plugins status nac-grundbuch-portal
nac plugins validate
nac plugins install --mode dry-run
nac plugins card-readiness
nac plugins xnp-reader-prompt
nac plugins xnp-workflow-gate --evidence out/xnp-reader-prompt.json
nac plugins pkcs7-inspect --input example.p7b
```

| Command | Meaning |
| --- | --- |
| `nac plugins status` | Lists all repo-local NaC integrations from the marketplace with CLI status. |
| `nac plugins status <plugin>` | Shows the boundary between Codex plugin and canonical NaC CLI for one integration. |
| `nac plugins card-readiness` | Checks local card-reader, SAK/XNP and readiness metadata. With installed hardware, a real local hardware test is possible; PINs and raw card data are not stored. |
| `nac plugins xnp-reader-prompt` | Creates a safe XNP reader prompt with the card gate in front. |
| `nac plugins xnp-workflow-gate` | Evaluates existing XNP reader-prompt evidence as a mandate-data-free workflow gate. |
| `nac plugins pkcs7-inspect` | Inspects a local PKCS7/P7B/P7C certificate bundle metadata-only, without signing or private-key access. |

The old plugin scripts remain the internal execution layer. The visible path
for users, docs and agents is `nac plugins ...`. Planned integrations are also
reachable through `nac plugins status <plugin>`, but they are shown as
`planned` until a real subject-matter CLI command exists.

For a workstation with installed real hardware:

```bash
nac plugins card-readiness --manual-card-present yes --manual-rfid-off yes --probe-morris-api --json
nac plugins xnp-reader-prompt --manual-card-present yes --manual-rfid-off yes --probe-morris-api --json
nac plugins xnp-workflow-gate --evidence out/xnp-reader-prompt.json --json
```

These commands may check real local drivers, morris, PC/SC, card-reader and XNP
reachability and turn existing evidence into workflow-gate metadata. Productive
portal actions, signing, PIN capture, raw card data, secrets and mandate data in
the repository remain blocked.

## Architecture Rule

New NaC functionality needs an understandable user surface and a checkable
technical execution path. For subject-matter use, that may be a web app,
plugin or Codex surface; for reproducibility, tests and operations, the
technical edge should be reachable through `nac`. Direct scripts such as
`scripts/quality_gate.py` may remain as internal or compatibility layers.

For configuration writes, there is an additional boundary: until a configuration
family has a clear schema, validation and approval rule, the CLI only shows and
validates it. Write commands are added per configuration family once the safe
change contract exists.

## Relationship To The Local Web App

The local web app is the visible office surface. It starts through `nac`,
reads the same BPMN/KG files and uses the same reviewed runtime family. The
target picture is:

```mermaid
flowchart LR
    User["Notary / subject-matter user"] --> UI["Operator web app, plugin or Codex"]
    UI --> Runtime["NaC runtime"]
    Admin["Admin / CI / maintainer"] --> CLI["nac CLI"]
    CLI --> Runtime
    Runtime --> Files["BPMN, KG, policies, contracts"]
    Runtime --> Gate["Quality gate and review"]
```

This makes NaC visually usable for the office while keeping it machine-checkable
for operations, review and further development.
