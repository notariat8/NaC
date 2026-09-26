# Implementation Plan: Teams MVP Goal and Staged Diagnosis

Status: plan for review; no implementation, publication, or live approval

Date: 26 September 2026

Leading [Issue #620](https://github.com/notariat8/NaC/issues/620). This plan follows the approved [EN specification](../specs/2026-09-26-m365-teams-mvp-simplification-design.md); the German version is authoritative for the notarial context. Baseline: `1503adf3d9392faad373e793bc5275394daff958`, tree `f3765329c0cb568b2686d84a6db2bf88daa2d019`. Delivery mode: Protected PR. Risk gate: Human Approval.

## Goal and Verifiable Boundary

This round simplifies the **decision about the cause** of the Teams 403 and its status communication. It does not yet repair the error or claim a Microsoft read. The Teams MVP is a synthetic test in `notary_team_01`; the public NaC reference repository provides versioned patterns, not tenant or professional approval. Production notarial operation requires its own domain, legal, and operational acceptance. For the 25 September observation, only the two locally checked client receipt hashes apply: `ed89c1171a02fc79c80314512375c7db84be2fce1528c7ba6596d7c24d805e40` and `daf4cc55f0f95f38b118155d8bef33d36a0a68809848ba96b049f1f129b80bda`. They establish an available SPFx subject, UI `no_access`, and a client HTTP 403; the origin and specific permission remain `UNKNOWN`. The receipt files stay outside the repository.

The original [AC-620-01 through AC-620-07](../specs/2026-07-13-m365-mvp-test-environment-design.md) and the [#620 verification contract](../../../../workflows/contracts/m365-mvp-test-environment.verification.contract.json) remain authoritative. Passing the six SIM criteria below does not close #620 or replace the deputy/denial tests or current twelve-step live closure.

## Read-Only Inventory Map (AC-620-SIM-01)

This map classifies the principal areas by their relevance **to the current Teams MVP incident**; `defer` does not retire an area.

| Main area | Contribution and dependency | Decision for this round |
| --- | --- | --- |
| Notarial domain model, BPMN, workflows, use cases, and local knowledge graphs | Define the synthetic matter and its domain truth, not the unproven 403 cause. | Retain; no domain change. |
| SPFx Teams tab and SharePoint site | Render the matter and produced the two neutral client receipts. | Retain; clarify only the documented deployment/receipt status. |
| Azure BFF, Entra validation, and Graph REST projection | Enforce identity, purpose, workspace, and redacted data; the 403 origin is open. | Retain security boundaries; no code fix without cause. |
| Audit-grade evidence, privacy, governance, and approvals | Separate client observation, provider proof, and live authority. | Retain; no weaker gate. |
| #748 read driver, historical request-log triage, and #756 diagnostic event | Alternative routes to a cause; #756 resides on a separate, unmerged branch. | Simplify sequence: assess telemetry suitability offline; defer read-driver release and #756 deployment. |
| #739 provenance and #632 live activation | Terminal historical run and separate write-capable completion. | Keep separate; no quarantine release or activation. |
| Other notarial workstation, plugin, legal-graph, on-prem AI, and archived OCI paths | Relevant to their own goals but not evidence for the current Teams 403. | Defer incident-specific edits; no file change or global quality claim. |

## Exact Change Scope After Plan Approval

1. The paired DE/EN [current-state pages](../../m365-current-state-access-diagnostic.md) receive a **new dated section** rather than overwritten history. It connects the merge of [PR #753](https://github.com/notariat8/NaC/pull/753) and later client receipts to the now-visible HTTP receipt control, keeps 403 origin unknown, and retains the older statement about non-deployment as history of that date. No provider state is inferred. (AC-620-SIM-02/03/05)
2. [BUILD_NOW](../../../../roadmap/BUILD_NOW.md) gets a brief pointer to this current diagnostic blocker beside `#620` without relabeling live closure, #632 boundaries, or milestones as complete. If the [Gantt rule](../../../../AGENTS.md) would make this a real board/milestone change, the additional exact file scope is reviewed before any Gantt edit. (AC-620-SIM-05/06)
3. This DE/EN plan and specification carry reciprocal [spec traceability](../../../../workflows/contracts/spec-traceability.contract.json). This round edits **no** validators, contracts, product modules, agent rules, SPFx assets, or #756 files. If a need for one is demonstrated, implementation stops before the edit and presents the exact additional scope. (AC-620-SIM-01/03/05)

## Staged Offline Decision

1. **Fix the evidence boundary:** Compare only neutral fields, hashes, and the closed observation window. `spfx_subject_available=true` excludes only the missing client-subject branch for this observation. A 403 proves neither Function ingress nor a Python BFF branch. (AC-620-SIM-02)
2. **Read telemetry suitability:** Separately record the [request-log resource contract](../../../../workflows/contracts/m365-current-state-read-driver-resources.contract.json), historical [triage specification](https://github.com/notariat8/NaC/blob/d92b47e0a67b6e5bc2f4387742c84ddfe9d2518b/docs/en/superpowers/specs/2026-09-25-m365-bff-request-log-triage-design.md), target/query/correlation proof, and eligible authentication channel. At baseline `projection_proven=false`; the #748 production port returns `BLOCKED_NO_REFRESH_CAPABILITY` and the license catalog is `PENDING`. Thus only local suitability assessment is planned. Record a missing binding as a precise blocker; zero log rows are not negative proof. (AC-620-SIM-03/04)
3. **Choose the next edge:** If all target, query, correlation, privacy, channel, and owner bindings can later be demonstrated, prepare **one separately approved** closed telemetry triage. Such a single query never replaces the formal #748 two-snapshot diagnosis. If it cannot answer the cause, assess the information gain of the [unmerged #756 event](https://github.com/notariat8/NaC/blob/e80c1a6385ecfaddb9d09dfd4e6bf427b184737c/docs/en/superpowers/specs/2026-09-26-m365-bff-403-diagnostic-event-design.md); no automatic deployment or reproduction. (AC-620-SIM-03/04)
4. **Fix and acceptance only after proven cause:** A later fix requires its own scope, test-first checks, and approval. #620 remains open until assigned and deputy positive cases, full denial/tamper cases, BPMN/task/deadline rendering, site-specific delivery, Graph write/readback/cleanup, and redacted UI/BFF evidence are proven. The exact #632 boundaries remain `Matter.Read`, runtime `Sites.Selected`, and site role `read`; missing bindings may only be created exactly or reused identically in a separately approved live run, and drift blocks. (AC-620-SIM-06)

Across all four steps, only redacted states, hashes, and blocker codes may enter Git, status pages, or public logs. Real app, tenant, and account IDs, raw correlations, query/source evidence, personal data, and credential contents remain in the protected repository-external area; this offline planning does not read credential contents at all.

## AC-to-Evidence Matrix

| Criterion | Planned evidence verifiable without provider access |
| --- | --- |
| AC-620-SIM-01 | This inventory map with goal contribution, dependency, and disposition, plus the separation of test MVP, public reference repository, and production operation. |
| AC-620-SIM-02 | Dated DE/EN status addendum with both hashes, `CLIENT_403_ORIGIN_UNKNOWN`, and unknown specific permission rather than an invented BFF cause. |
| AC-620-SIM-03 | One documented sequence for #748, historical telemetry triage, and the conditional #756 follow-up. |
| AC-620-SIM-04 | Explicit stop conditions for missing target, query, correlation, privacy, authentication, or owner binding before a real read or new reproduction. |
| AC-620-SIM-05 | Consistent DE/EN status pages and `BUILD_NOW`; one final strict doctor with preliminary checks disclosed. |
| AC-620-SIM-06 | Reference to unchanged AC-620-01..07 and the still-open twelve-step live closure, without a completion claim. |

## Review, Validation, and Stops

Before a later edit, record the red check: the dated DE/EN status pages still lack a section on the two paired client receipts, and `BUILD_NOW` does not name the concrete 403 diagnostic blocker. After the edit, a dated section must close that gap without rewriting the older historical statement or claiming a BFF cause from the 403. This is a manual, reviewable documentation regression; no new test code outside scope is invented.

`plan -> review -> fix` checks DE/EN parity, the actual diff boundary, chronology, preservation of #620 criteria, privacy, and separation of client response/Function ingress/Python BFF. Check AC-620-SIM-01..06 individually against the inventory map, dated receipts, decision sequence, stops, DE/EN status, and preserved #620 criteria; the generic traceability validator does not currently enforce this content mapping. Because the link validator does not itself scan these plan/spec files, also check their relative links locally for existence and language path. Run `graft build` before nontrivial work and focused validators as fast preliminary checks. On the final local state run **one** complete `python scripts/nac.py doctor --profile strict`, which already includes `graft check` and those validators. Do not count them again as independent final gates. A protected PR and remote CI are later delivery steps, not effects of this plan approval.

```text
graft build
python scripts/validate_spec_traceability.py
python scripts/validate_language_parity.py
python scripts/validate_doc_links.py
python scripts/nac.py doctor --profile strict
git status --short
git diff --check
git diff --check main...HEAD
git diff --name-status main...HEAD
git log --oneline main..HEAD
```

Before later PR closure, inspect the complete `base...head` file and commit lists against the target branch and mandatory remote checks on the final head; `HEAD` alone is insufficient. Stop before any login, token refresh, credential or provider access, deployment, new Teams request, #739 release, #632 live run, merge, or edit outside the named scope above. An unproven 403 origin stays `UNKNOWN`; a blocked triage never authorizes a retry.
