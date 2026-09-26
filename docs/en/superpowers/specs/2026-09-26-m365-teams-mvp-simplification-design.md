# Teams MVP Goal and Staged Diagnostic Path

Status: design and specification approved; implementation plan for review; no implementation or live approval

Date: 26 September 2026

Leading issue: [#620](https://github.com/notariat8/NaC/issues/620). Related, separately bounded work: [#739](https://github.com/notariat8/NaC/issues/739), [#746](https://github.com/notariat8/NaC/issues/746), [#748](https://github.com/notariat8/NaC/issues/748), and [#756](https://github.com/notariat8/NaC/issues/756).

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-teams-mvp-simplification
leading_issue: https://github.com/notariat8/NaC/issues/620
plan: docs/en/superpowers/plans/2026-09-26-m365-teams-mvp-simplification.md
risk_gate: Human Approval
delivery_mode: Protected PR
review_gates:
  - Privacy
  - Policy
  - Human Approval
acceptance_ids:
  - AC-620-SIM-01
  - AC-620-SIM-02
  - AC-620-SIM-03
  - AC-620-SIM-04
  - AC-620-SIM-05
  - AC-620-SIM-06
validation_commands:
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_doc_links.py
  - python scripts/nac.py doctor --profile strict
```

## Purpose and Verifiable Goal

The near-term NaC MVP must display exactly one synthetic notarial matter in the `notary_team_01` test workspace through the “NaC Vorgangsansicht” Teams app, including its BPMN reference, status, tasks, and UTC deadline. An assigned identity or an identity with valid deputy authority receives only the redacted, purpose-bound BFF projection; an unauthorized identity or manipulated workspace, matter, purpose, or filter values receive no matter data. Evidence covers the rendered Teams UI, the BFF access decision, and redacted records. This is test-environment acceptance, not authorization for real matters or production notarial operation. The existing [MVP acceptance criteria](2026-07-13-m365-mvp-test-environment-design.md) remain authoritative; the six simplification criteria below only supplement them.

The locally checked client receipts of 25 September 2026 have SHA-256 `ed89c1171a02fc79c80314512375c7db84be2fce1528c7ba6596d7c24d805e40` and `daf4cc55f0f95f38b118155d8bef33d36a0a68809848ba96b049f1f129b80bda`. They prove `spfx_subject_available=true`, `ui_state=no_access`, and an HTTP 403 received by the client for the bound Workbench GET. They do **not** prove whether the Azure Function accepted the request, whether the Python BFF produced the 403, or which access rule applied. Receipt files and real identity and tenant values remain outside the repository.

## Scope and Boundaries

A read-only repository-wide inventory relates the product goal, architecture, active and historical diagnostic paths, status statements, and common checks. Only these Teams MVP surfaces are proposed for first-round changes: this DE/EN specification and its later DE/EN plan, the [DE/EN current-state status](../../m365-current-state-access-diagnostic.md), and [BUILD_NOW](../../../../roadmap/BUILD_NOW.md). If a shared validator, verification contract, or other document really needs editing, its exact file scope must first be reviewed and approved separately. Other NaC subsystems stay unchanged. This design does not delete or rewrite published code, commits, evidence, or issues.

The [#739 provenance boundary](2026-09-15-m365-bff-failed-partial-safe-completion-design.md) remains terminal; lost artifacts create no release authority. #632 live activation remains a separate decision. A green local test, a client 403, or owner design approval is not provider, deployment, or credential approval.

## Considered Approaches

1. **Release the full #748 read driver first:** broad current-state coverage and strong package binding, but additional binary, SBOM, license, authentication, and approval work before the first 403 cause indicator. Not selected as the default prerequisite for this incident.
2. **Existing telemetry first, #756 only as a justified follow-up — selected:** Existing client receipts bound the window. First assess locally whether an existing, exactly bound request-log target and a provably correlatable query are available at all. A later single provider read still requires separate approval. Only if historical telemetry cannot make the necessary distinction is the inactive internal #756 event considered as the basis for a separately approved new reproduction. This avoids a new release path without proven information gain.
3. **Activate #756 immediately and reproduce the error:** could expose the internal 403 branch, but requires BFF deployment and a new Teams reproduction; it does not retroactively explain the historical observation. Not selected as the first step.

## One Decision Sequence Rather Than Parallel Gate Chains

1. **Known client evidence:** Check receipt hashes, binding, closed window, and neutral fields locally. `spfx_subject_available=true` excludes only the missing SPFx-subject branch for this observation. HTTP 403 remains `CLIENT_403_ORIGIN_UNKNOWN`; do not guess a BFF cause.
2. **Telemetry suitability:** The [request-log resource contract](../../../../workflows/contracts/m365-current-state-read-driver-resources.contract.json) and protected, repository-external evidence must bind the Function target, Application Insights app ID, query projection, and actual capture of the correlation binding. The [historical triage design](https://github.com/notariat8/NaC/blob/d92b47e0a67b6e5bc2f4387742c84ddfe9d2518b/docs/en/superpowers/specs/2026-09-25-m365-bff-request-log-triage-design.md) is a reference, not an approved provider run. At baseline `862c87e1`, the projection remains `projection_proven=false`; the #748 production port blocks without no-refresh capability, and the license catalog is not approved. This path therefore starts with an offline suitability assessment, not an executable Microsoft read. Without target, query, or correlation proof, return a precise `BLOCKED` reason; no log row does not mean “no BFF request.”
3. **Later read-only reconciliation:** Only a separate, narrowly bounded contract and exactly bound approval could permit one closed, redacted telemetry query through an eligible authentication channel. A unique match could establish Function telemetry ingress, not automatically the Python branch or substantive denial reason. This single triage query never substitutes for the formal #748 diagnosis with two independent, identical snapshots. This design authorizes no login, token refresh, redirect, retry, or write.
4. **BFF-internal distinction if necessary:** If telemetry is inconclusive or insufficient to identify the cause, justify use of the [inactive #756 event on a separate, unmerged branch](https://github.com/notariat8/NaC/blob/e80c1a6385ecfaddb9d09dfd4e6bf427b184737c/docs/en/superpowers/specs/2026-09-26-m365-bff-403-diagnostic-event-design.md). Deployment, new reproduction, and reading protected diagnostic evidence each require their own scope and approval checks. Do not relabel the old client receipt as new BFF evidence.
5. **Fix only after cause:** A later fix targets only the proven defect while preserving Entra, role, matter, purpose, privacy, and provider boundaries. Recheck authorized positive and unauthorized negative cases in Teams afterward.

## Simplifying Repository Work

The existing [current-state diagnostic documentation](../../m365-current-state-access-diagnostic.md) should hold the dated operational status; historical specs remain historical contracts. The [Build Now overview](../../../../roadmap/BUILD_NOW.md) should link to this status briefly rather than assert conflicting live readiness. Mark each active or deferred diagnostic edge with its information goal, existing evidence, concrete blocker, and next permitted step.

For changes, run focused synthetic tests and the affected validator as preliminary checks. Run the full strict doctor once on the final local state; do not count validators it already includes again as separate final checks. Repeat individual checks only to investigate failure. A validator claimed as a mandatory gate must actually be registered in that gate. Report skip counts and untested live boundaries. This removes redundant runs without weakening any mandatory check.

## Risks and Acceptance Criteria

- **AC-620-SIM-01:** A DE/EN inventory map classifies NaC's main areas by goal contribution, dependency, and a decision to `retain`, `simplify`, or `defer`. Goal and test acceptance visibly distinguish the Teams MVP, public reference repository, and production notarial operation.
- **AC-620-SIM-02:** Reference the two client receipts only by the stated hashes and neutral fields; the 403 origin and specific permission remain `UNKNOWN` until proven.
- **AC-620-SIM-03:** Classify the #748 read driver, historical request-log triage, and #756 event as active, conditional, or deferred in one decision sequence; do not rewrite published history.
- **AC-620-SIM-04:** A real read or new reproduction blocks before further access if target, query, correlation, privacy, authentication, or owner binding is missing; this design executes neither.
- **AC-620-SIM-05:** Operational status in the named DE/EN current-state documents and `BUILD_NOW` does not contradict the observed client state. Run shared checks once on the final state; do not claim an unregistered validator passed. Contract or gate edits require a separate scope decision.
- **AC-620-SIM-06:** These SIM criteria replace neither AC-620-01 through AC-620-07 nor the bound twelve-step live closure. Later Teams completion still requires the authorized positive and deputy cases, BPMN/task/deadline rendering, the full tamper and denial matrix, site-scoped delivery, Graph write/readback/cleanup, exact #632 bindings, and redacted UI/BFF evidence. An inactive diagnostic event or green CI alone is not completion.

Non-goals for this specification are login, token refresh, provider access, deployment, BFF or SPFx changes, permission changes, #739 quarantine release, #632 live execution, merge, or a claim of global optimality for the entire NaC repository. Later implementation requires a DE/EN plan after specification review and its own technical and operational gates.
