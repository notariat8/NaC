# Data Sovereignty: Git Templates And ATP Runtime Data

Status: target-architecture decision, without productive schema apply.

Companion model decision:
[atp-graph-runtime-model.md](atp-graph-runtime-model.md) clarifies that ATP is
the runtime data platform, but not a pure SQL subject-matter model. NaC
separates relational security anchors, versioned JSON payloads and graph or
ontology projections.

## Decision

NaC separates Git as the control plane from ATP as the runtime data plane.

Git remains the binding source for:

- product code, tests and release artifacts
- Infrastructure as Code and operating runbooks
- governance rules, policies, quality gates and review evidence
- canonical BPMN process definitions and template versions
- synthetic demo and test data

ATP becomes the binding runtime database for:

- tenants, users and role bindings
- server-side sessions and revocation information
- matter and case metadata
- activated process versions per tenant
- agent registrations, sandbox bindings and active leases for the on-prem
  agent runtime
- process instances, process events, statuses and deadlines
- XNP/SNP, register, land-register and signature gates as safely redacted metadata
- audit metadata without tokens, claims, secrets or raw mandate data in browser output

Productive mandate data is not stored in Git. Git may still contain synthetic
demo data and subject-matter templates. The older tenant Git repository logic
is therefore a demo/legacy path, not the target model for productive SaaS
operation.

## Rationale

Git is strong for traceability, review and versioning of product logic. Git is
weak for live SaaS data:

- Clones, forks and local worktrees multiply data.
- Tenant, role and field-level access cannot be enforced cleanly per record.
- Deletion, correction, blocking and retention are hard to control with Git history.
- Concurrent runtime writes create merge and consistency problems.
- Queries across matters, deadlines, statuses, events and tenants are not
  viable database operations in Git.

ATP is the better runtime boundary for NaC because it combines transactions,
structured queries, JSON flexibility, access control, backups and server-side
persistence. This is not a SQL-only decision: relational keys remain the leading
security and integrity boundary, JSON payloads carry versioned subject-matter
state, and graph or ontology projections model relationships, dependencies,
parallelism and critical paths. The primary runtime model therefore does not
move back into Git.

## Data Classification

| Data class | Target location | Rule |
| --- | --- | --- |
| Code, tests, IaC, policies | Git | Protected PR, review and quality gate |
| BPMN process definition | Git | versioned template, no concrete mandate content |
| Activated process version | ATP | tenant points to approved template version |
| Process instance | ATP | concrete matter, status, deadlines, events |
| Tenants and user bindings | ATP / IdP | ATP stores NaC binding, IdP authenticates |
| Agent and sandbox bindings | ATP | user/tenant/agent/sandbox lease, not local NemoClaw-only ownership |
| Sessions | ATP | only hashed/derived session data, no tokens or claims |
| Document metadata | ATP | file name, type, status, evidence reference without raw content |
| Document binaries | later Object Storage | encrypted, with retention and audit under [private-payload-target-design.md](private-payload-target-design.md) |
| Demo data | Git allowed | synthetic and explicitly marked only |

## Initial Runtime Contract Concept

The target model is built incrementally. `Schema` does not mean a purely
relational subject-matter design here. It means a runtime contract for
transactional anchors, JSON payloads, audit and graph projections. For the next
expansion, these logical tables or equivalent store boundaries are sufficient:

- `tenants`: tenant, status, domain binding, activated process versions.
- `users`: NaC user binding, role class, tenant assignment, IdP subject hash.
- `agent_registry`: agent types, target-system class, approved capabilities and
  references to Git-versioned contracts.
- `sandbox_bindings`: binding between tenant, user, role, matter, agent and
  local sandbox reference.
- `sandbox_leases`: active lease, expiry, revocation status and reuse boundary
  for the on-prem agent runtime.
- `matters`: matter/case metadata, tenant, use case, status, no raw documents.
- `process_templates`: activatable template reference to Git version, BPMN ID, hash.
- `process_instances`: concrete process instance per matter, template version, runtime status.
- `process_events`: append-only events, gate results, deadlines, XNP/SNP status classes.
- `document_metadata`: optional document references, classification and storage pointer.

The tables must not store tokens, IdP claims, PINs, raw card data, credentials
or unredacted mandate content until the respective privacy, retention and
notarial approval boundary is explicitly defined.

## Process Rule

A process has two separate lifecycles:

1. **Template lifecycle in Git:** subject-matter model, BPMN, review, approval, version.
2. **Instance lifecycle in ATP:** concrete matter, status, events, external responses,
   deadlines and audit metadata.

A Git merge does not automatically change a running matter. A tenant must
activate a template version; process instances then reference that exact
version. This keeps demo, governance and productive runtime data separated.

## Non-Goals

- No OCI apply through this decision.
- No productive ATP schema apply through this decision.
- No migration of real mandate data.
- No raw document storage in ATP or Git.
- No claim that XNP/SNP is productively connected.

## Next Tracks

1. Runtime contract plan for anchors, JSON payloads and graph projections around
   `tenants`, `matters`, `process_templates`, `process_instances` and
   `process_events`.
2. Migration path for synthetic demo Git data into an ATP-backed demo read-model store.
3. Read `/workspace` status from ATP metadata without loading raw mandate data.
4. Model the real-estate purchase agreement as the first process instance with
   XNP/SNP, land-register, register and completion gates.
