# BFF 503 stage evidence for the Teams test tab

Status: repository implementation; no deployment or confirmed live cause.

Leading issue: [#762](https://github.com/notariat8/NaC/issues/762). The visible “workspace is currently unavailable” message proves only a failed retrieval, not its server-side cause.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: bff-503-stage-diagnostic
leading_issue: https://github.com/notariat8/NaC/issues/762
risk_gate: Privacy
delivery_mode: Protected PR
plan: docs/en/superpowers/plans/2026-09-30-bff-503-stage-diagnostic.md
review_gates:
  - Privacy
  - Secrets
  - External Service
affected_artifacts:
  - src/nac_bff/workbench_endpoint.py
  - src/nac_bff/fastapi_adapter.py
  - src/nac_bff/composition.py
  - tests/test_nac_bff_workbench_endpoint.py
  - tests/test_nac_bff_azure_function_host.py
acceptance_ids:
  - AC-762-01
  - AC-762-02
  - AC-762-03
validation_commands:
  - python -m unittest tests.test_nac_bff_workbench_endpoint tests.test_nac_bff_azure_function_host
  - python scripts/validate_spec_traceability.py
  - graft check
  - python scripts/nac.py doctor --profile strict
```

## Decision

The existing BFF continues to return only the neutral 503 response to the client. Only the internal server log receives a fixed, non-request-derived stage code for a 503: budget, clock, Graph request, Graph response, unexpected Graph error, invalid Graph result, BPMN asset, projection, request timeout, or unexpected HTTP boundary. Exception text, tokens, object IDs, correlation IDs, list content, and user data never enter this record. A logger failure does not alter the neutral response.

This is a narrowly scoped diagnostic fix, **not** a claim that the Teams 503 is resolved. Real cause evidence requires a separately authorized BFF release and controlled test. No additional client receipt or telemetry infrastructure is introduced.

## Acceptance

- **AC-762-01:** Each captured 503 path records at most one fixed stage; 200, 401, and 403 record no 503 stage. The existing HTTP response stays unchanged.
- **AC-762-02:** Sensitive exception details appear neither in HTTP responses nor in internal 503 stages; invalid stages are rejected.
- **AC-762-03:** Synthetic negative tests for Graph, BPMN, projection, budget, clock, and HTTP boundary pass; this change includes no Microsoft access or deployment.
