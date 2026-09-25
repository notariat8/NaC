# HTTP companion receipt for the NaC tab in Teams

Status: Diagnostic objective approved; backward-compatible detail decision and specification for owner review. No implementation plan, code, deployment, or real provider finding approved.

Date: 25 September 2026

Leading issue: [#748](https://github.com/notariat8/NaC/issues/748); visible product objective: [#620](https://github.com/notariat8/NaC/issues/620).

Starting point: `main` commit `957d8b9ac9a8c6a3d9cbbf26de679d220f302432`, tree `e1edb34d0a1518166bd31b9facde13eb7fdd2478` after the merge of [PR #752](https://github.com/notariat8/NaC/pull/752).

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-client-http-observation
leading_issue: https://github.com/notariat8/NaC/issues/748
risk_gate: Human Approval
delivery_mode: Protected PR
review_gates:
  - Privacy
  - Secrets
  - External Service
  - Human Approval
affected_artifacts:
  - docs/de/superpowers/specs/2026-09-25-m365-client-http-observation-design.md
  - docs/en/superpowers/specs/2026-09-25-m365-client-http-observation-design.md
  - spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/NacBffClient.ts
  - spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/ClientObservationReceipt.ts
  - spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/components/NacWorkbenchHost.tsx
  - src/nac_bff/client_http_observation_receipt.py
  - workflows/verification-contracts/m365-client-http-observation.verification.json
  - spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/ClientHttpObservationReceipt.test.ts
  - tests/test_m365_client_http_observation_receipt.py
acceptance_ids:
  - AC-748-HTTP-01
  - AC-748-HTTP-02
  - AC-748-HTTP-03
  - AC-748-HTTP-04
  - AC-748-HTTP-05
validation_commands:
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_doc_links.py
  - graft check
```

## Purpose and starting point

The deployed tab shows “Kein Zugriff auf diesen Arbeitsbereich.” Its existing, explicitly downloaded [client receipt](../../../../spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/ClientObservationReceipt.ts) contains only the neutral UI state, SPFx subject availability, a closed observation window, and opaque hash bindings. The [BFF client](../../../../spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/NacBffClient.ts) intentionally maps HTTP 401 and 403 to the same neutral message. The receipt cannot distinguish these client responses. It also cannot prove that the Azure Function received the request.

This extension only distinguishes the HTTP class **observed by the SPFx client**. It replaces neither the two provider snapshots nor the four server-side diagnostic classes in the [existing #748 design](2026-09-20-m365-current-state-access-diagnostic-design.md).

## Design decision and alternatives

1. **Recommended: separate, versioned HTTP companion receipt.** The existing six-field receipt and its [verification contract](../../../../workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml) remain byte- and schema-identical. A second explicitly triggered download contains only a closed client HTTP class and the SHA-256 digest of the concurrently produced base receipt. This preserves old downloads, validators, and historical commit/contract bindings. The extra click is the deliberate trade-off.
2. Adding a field directly to the old JSON would be simpler for the user but would break its exact field list, validator, and historical contract binding. That option is excluded.
3. Browser or desktop developer tools avoid code changes, but they are not reliably available for the actual desktop tab without additional UI/preview prerequisites and can expose unredacted network details. They are not a product workflow.

The companion receipt is a **supplemental local observation**, not a new production read driver or a bypass of the #748 gate. The old receipt remains usable on its own; a companion without the matching base receipt is not accepted as bound evidence. A separate DE/EN implementation plan and a new verification-contract binding follow only after review of this spec.

## Closed data and UI boundary

The new JSON receipt has its own filename and exactly these fields:

| Field | Value |
| --- | --- |
| `schema_version` | Constant `nac.client-http-observation/v0.1` |
| `base_receipt_sha256` | SHA-256 over the canonical UTF-8 bytes of the concurrently produced unchanged base receipt |
| `client_http_class` | Exactly `none`, `401`, or `403` |
| `observation_binding_sha256` | SHA-256 over the other three fields as UTF-8 JSON with sorted keys and no whitespace |

`none` only means the client has **no matching HTTP response** for this observation; it does not assert that the server received no request or that the BFF was not deployed. `401` and `403` come only from the actual `HttpClientResponse.status` of the existing `/workbench-snapshot` call. An exception string, URL, header, response body, or another request must never be reinterpreted as that class. Other status codes, abort, timeout, missing correlation, or inconsistent observation produce no HTTP companion receipt. The UI message remains unchanged and neutral.

The new “HTTP-Diagnosebeleg speichern” button appears only in the existing denied state and starts a download only after an explicit click. It sends no telemetry, performs no additional BFF request, and opens no login. Base and companion receipts are created from the same frozen observation; re-render, refresh, unmount, or concurrent loads must not mix status and base digest. The browser persists no raw correlation ID, user/object ID, name, email address, tenant, URL, query, header, response content, token, or credential in the companion. Its maximum size is 1024 bytes.

Only after separate future approval and its own validator/CLI extension may the companion be materialized outside the repository with current-user-only access. Until then it is **not** an input to the historical #748 preflight, `OWNER_SOLO_APPROVAL` evidence, or a substitute for server-side correlated request-log checks.

## Acceptance criteria

- **AC-748-HTTP-01:** For a synthetic SPFx subject with an actual HTTP 401 or HTTP 403 response, an explicit click creates a companion with exactly `401` or `403`; the Teams message stays equally neutral in both cases.
- **AC-748-HTTP-02:** Without a matching HTTP response, the class is only `none` where the existing denied UI state produces a complete base receipt; unclear, aborted, or contradictory states produce no companion. No client value claims the BFF saw the request.
- **AC-748-HTTP-03:** Both files bind to exactly the same frozen observation. Changing, replacing, reusing, or mixing a base receipt causes companion validation to fail closed. The old receipt and historical contract stay valid unchanged.
- **AC-748-HTTP-04:** Synthetic negative tests cover unknown fields/status values, PII/token/URL/header/body leaks, automatic download, additional requests, incorrect correlation, and concurrent load generations. The visible UI and download receive visual verification.
- **AC-748-HTTP-05:** DE/EN spec, subsequent plan, verification contract, spec traceability, privacy/AI-SBOM decision, and Windows/SPFx gates are synchronized before implementation acceptance; this grants no Microsoft read, provider write, login, deployment, or #739/#632 run.

## Risks and non-goals

An HTTP 401/403 response may originate from an upstream layer. The client class is therefore a pointer to the next targeted check, **not a final root cause**. A hash binds two local files but does not prove server authenticity. No existing #748 snapshots, release gates, authentication boundaries, or old Issue #739/#632 artifacts are relaxed. This spec authorizes only its own review; implementation, package/app release, and production diagnostic access remain separately approval-gated.
