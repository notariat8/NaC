# NaC On-Prem Agent Runtime

Status: contract and target-system boundary
Last content update: 2026-07-02

## Purpose

This page describes how NaC can run as an agentic on-prem platform on a
NemoClaw/OpenClaw target system without giving up the GitOps boundaries of the
NaC repository. It extends the
[NemoClaw operating model](nemoclaw-operating-model.md) with the technical
runtime boundary between source repository, target-control and production
notarial workflows.

The current target-system run on `notoclaw01` is a target-control sandbox run.
It proves that a manifest, skill, MCP boundary, connector placeholders, smokes
and evidence can live on the target system. It does not replace a NaC
repository change, pull request, subject-matter approval or production
connector apply.

## Leading Sources

| Layer | Leading source | Meaning |
| --- | --- | --- |
| NaC GitOps | NaC repository on `brev01` | Code, contracts, docs, policies, BPMN, KG, tests, PRs and releases. |
| Target-control | `/home/ubuntu/nac-target-control` on `notoclaw01` | Non-sensitive manifests, runbooks, local smokes and evidence for NemoClaw/OpenClaw. |
| OpenClaw workspaces | `/sandbox/.openclaw/workspace-*` | Runtime-adjacent agent workspaces; not the GitOps source for NaC. |
| Codex runtime | `/home/ubuntu/.codex` | Codex configuration and thread state; not a NaC artifact source. |
| NemoClaw state | `/home/ubuntu/.nemoclaw` | Runtime state; not GitOps source artifacts. |

The machine-readable contract is
[workflows/contracts/nac-onprem-agent-runtime.contract.json](../../../workflows/contracts/nac-onprem-agent-runtime.contract.json).
It is validated by
[scripts/validate_nac_onprem_agent_runtime.py](../../../scripts/validate_nac_onprem_agent_runtime.py).

## Variant C: Outbound Connector

The target architecture does not make the raw NemoClaw/OpenClaw UI the
production publication pattern. The preferred architecture is an outbound
connector from `notoclaw01` to OCI:

1. The browser reaches only the OCI layer at `agent.notariat8.de`.
2. OCI Identity Domain authenticates the user, for example `user@example.com`.
3. An OCI API Gateway or BFF checks session, tenant, role and purpose.
4. ATP stores the binding between IdP subject, tenant, user, agent, sandbox,
   lease and audit metadata.
5. `notoclaw01` opens an outbound mTLS or WebSocket/HTTPS connection to the OCI
   control plane and accepts only verified agent work.
6. NemoClaw/OpenClaw starts, keeps or reconnects the matching sandbox locally.

SSH is therefore only an operations and diagnostic path, not productive user
traffic. Browsers must also not point directly at Brev or the raw OpenClaw UI.
The OCI layer remains the public isolation, identity and policy boundary.

## Storage Boundary For Variant C

The durable truth does not live in NemoClaw. NemoClaw is the target runtime.

| Layer | Stored there | Not stored there |
| --- | --- | --- |
| Git / NaC | Connector code, contracts, policies, tests, BPMN and KG templates | Runtime sandbox state, IdP tokens, credentials, private keys, matter payloads |
| Git / OCI Landing Zone | API Gateway, ATP, Vault and network intent as IaC | Live secrets, TLS private key material, productive runtime values |
| ATP | Tenant, user, role, agent, sandbox, lease, session and audit metadata | Tokens, raw claims, PINs, unredacted matter content |
| OCI Vault | Connector credentials, mTLS material, API secrets and private keys | freely readable configuration or subject-matter payloads |
| `notoclaw01` | running sandboxes, local runtime state, redacted target-control evidence | NaC GitOps truth, productive matter data, global user or tenant registry |

For user separation, one productive sandbox must not be shared across
independent users. The minimum isolation is `tenant + user`; the preferred key
is `tenant + user + matter + role` once matter or case context is loaded.
Reusing a sandbox requires an active lease check in ATP.

## Target-System Layout

`notoclaw01` uses `/home/ubuntu/nac-target-control` as the NaC-specific control
surface. That surface is intentionally separate from `.codex`, `.nemoclaw` and
the OpenClaw workspace paths.

Expected artifacts:

- `blueprints/nac-onprem/agents.yaml`: agent manifest for the NaC on-prem
  sandbox run.
- `blueprints/nac-onprem/workspace-template/`: workspace template with
  `AGENTS.md`, `IDENTITY.md`, `SOUL.md`, `USER.md` and `MEMORY.md`.
- `skills/nac-agent/SKILL.md`: NaC agent skill for the target-system run.
- `mcp/nac/README.md`: local MCP boundary for NaC tools.
- `connectors/xnp/README.md`, `connectors/cyberjack/README.md` and
  `connectors/register/README.md`: prepared connector boundaries without
  production credentials.
- `bin/nac-target-smoke` and `bin/nac-runtime-smoke`: local target-system
  smokes.
- `evidence/2026-06-28-nac-onprem-agent-solution.md`: evidence for the current
  sandbox run without secrets or matter data.

The [NaC runtime smoke](../operations/nac-runtime-smoke.md) is prepared as the
next target-system smoke, but it has not been executed yet. It may only read
existing NemoClaw/OpenClaw status signals and produce redacted evidence; it must
not trigger installation, onboarding, rebuild, policy changes, authenticated
dashboard-link retrieval or runtime mutation.

## Public Origin And Fixed Domain

The production on-prem agent runtime needs a fixed, DNS-backed domain for public
reachability. Random provider-specific tunnel domains are allowed only for demo
or diagnostic smokes and do not confirm production readiness.

The concrete hostname is not hardcoded in the NaC repository. It is supplied as
non-sensitive target-system configuration in
`/home/ubuntu/nac-target-control/config/public-origin` or as an explicit
`NAC_PUBLIC_ORIGIN` for individual smokes. Domain, TLS and reverse-proxy setup
remain a separate owner-gated operations step.

## Agent Roles

The target-system run may validate quickly and locally, but it must not become
project management. The leading Project Manager remains in the main chat on
`brev01`.

Minimum agents in the target-control contract:

- `main`: handoff routing between Target Operator and Project Manager,
- `notary-flow`: notarial workflow analysis without final subject-matter authority,
- `evidence`: smokes, evidence, secret checks and matter-data exclusion,
- `connector-ops`: prepared XNP, card and register boundaries.

Subagents on the target system are responsible only for target-control work.
GitHub write access, PR creation, OCI apply, release steps, secrets and
production specialist-system writes stay in the main run and remain owner
gated.

## Optional Agent Tooling Candidates

Ponytail is recorded as an optional agent-tooling candidate, but it is not
installed or activated. The allowed use is limited to documented
over-engineering and simplicity review. Codex lifecycle hooks, OpenClaw
runtime activation, matter-data processing, shortening security, privacy,
owner-gate, test or validator duties, and GitHub or OCI write access from the
target system are not allowed.

The [Ponytail skill-only smoke](../operations/ponytail-skill-only-smoke.md)
was owner-gated, executed and passed on 2026-06-29. It checked only public
metadata, target paths and non-sensitive evidence preparation. The matching
template is
[workflows/evidence-templates/ponytail-skill-only-smoke.md](../../../workflows/evidence-templates/ponytail-skill-only-smoke.md)
and must not contain secrets, PINs, tokens, keys, certificate material,
personal data or matter data.

The target evidence is
`/home/ubuntu/nac-target-control/evidence/ponytail-skill-only-smoke-2026-06-29.md`.
Ponytail remains `candidate_not_installed`; installation, lifecycle hooks,
OpenClaw runtime activation and GitHub or OCI write from the target system did
not happen.

Every installation, hook activation or OpenClaw runtime activation needs a
separate owner apply gate. Ponytail must never override NaC governance.

## Connector Boundary

The target-system structure may prepare connectors, but it must not run them in
production yet:

| Connector | Current status | Next NaC step |
| --- | --- | --- |
| XNP/SNP | Path and smoke prepared | Under [notarial-onprem-connector-boundaries.md](notarial-onprem-connector-boundaries.md), local readiness and redacted evidence only. |
| cyberJack/card workstation | Path and smoke prepared | Under [notarial-onprem-connector-boundaries.md](notarial-onprem-connector-boundaries.md), card, PIN and workstation boundary without signature triggering. |
| Register | Path and smoke prepared | Under [notarial-onprem-connector-boundaries.md](notarial-onprem-connector-boundaries.md), external status/wait gates only without production filing. |

None of these boundaries may store real credentials, PINs, card material,
matter data or production callback payloads in the product repository or in
`/home/ubuntu/nac-target-control`.

## Data Model Relation

The on-prem agent may use the NaC data model, but it must not become the source
of truth for matter data. Git remains the source for source artifacts, rules,
BPMN, KG and contracts. Runtime metadata belongs in the approved runtime layer,
for example ATP for SaaS metadata or a later approved on-prem store model.

For ontology and graph work this means:

- usecase-local KGs stay under [usecases/](../../../usecases),
- runtime-adjacent status and event data are not handled as free agent memory,
- Oracle Graph Studio or other graph tools are analysis and modeling tools
  after a separate gate, not a requirement for the target-system smoke,
- real matter content remains blocked until a separate approval exists.

## Done Rule

The Target Operator may report only the target-system scope as done when:

- manifest, skill, MCP boundary, connector stubs and smokes are freshly
  checked,
- evidence contains no secrets, tokens, PINs or matter data,
- no NaC repository change is still required.

As soon as a contract, policy, validator, doc or code change is needed in the
NaC repository, the status is `handoff to Project Manager`. The overall work is
complete only after NaC GitOps validation, commit, push, PR checks and, where
needed, owner review.

## Open NaC Work

The current target-system run creates four NaC-side work blocks:

1. Clarify subject-matter notarial workflow rules in BPMN, KG and contracts.
2. Keep matter-data classification, redaction rules and storage boundaries
   aligned for on-prem and SaaS runtime through
   [matter-data-classification-redaction.md](matter-data-classification-redaction.md).
3. Move XNP, cyberJack and register connectors from the boundary contract into
   private operating frames, test mode and later specialist-system adapters.
4. Integrate durable manifest onboarding for NaC agents into GitOps without
   turning `notoclaw01` into the development repository.
