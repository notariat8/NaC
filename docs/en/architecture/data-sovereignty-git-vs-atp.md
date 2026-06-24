# Data Sovereignty: Git Templates And ATP Runtime Data

Status: target-architecture decision, without productive schema apply.

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
persistence. JSON columns can hold flexible subject-matter payloads; relational
keys remain the leading integrity boundary. Graph capabilities can later support
relationships, dependencies, parallel paths and critical paths without moving
the primary runtime data model into Git.

## Data Classification

| Data class | Target location | Rule |
| --- | --- | --- |
| Code, tests, IaC, policies | Git | Protected PR, review and quality gate |
| BPMN process definition | Git | versioned template, no concrete mandate content |
| Activated process version | ATP | tenant points to approved template version |
| Process instance | ATP | concrete matter, status, deadlines, events |
| Tenants and user bindings | ATP / IdP | ATP stores NaC binding, IdP authenticates |
| Sessions | ATP | only hashed/derived session data, no tokens or claims |
| Document metadata | ATP | file name, type, status, evidence reference without raw content |
| Document binaries | later Object Storage | encrypted, with retention and audit |
| Demo data | Git allowed | synthetic and explicitly marked only |

## Initial Schema Concept

The target model is built incrementally. For the next expansion, these logical
tables or equivalent store boundaries are sufficient:

- `tenants`: tenant, status, domain binding, activated process versions.
- `users`: NaC user binding, role class, tenant assignment, IdP subject hash.
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

1. ATP schema plan for `tenants`, `matters`, `process_templates`,
   `process_instances` and `process_events`.
2. Migration path for synthetic demo Git data into an ATP-backed demo read-model store.
3. Read `/workspace` status from ATP metadata without loading raw mandate data.
4. Model the real-estate purchase agreement as the first process instance with
   XNP/SNP, land-register, register and completion gates.
