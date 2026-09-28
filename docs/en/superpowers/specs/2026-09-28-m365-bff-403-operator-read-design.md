# One-shot operator server read for the Teams 403 incident

Status: local design revision for owner review; no production read, sign-in,
token refresh, or change to the inactive #756 contract.

Date: 28 September 2026. Leading [Issue #756](https://github.com/notariat8/NaC/issues/756).
The [existing Stage A specification](2026-09-26-m365-bff-403-diagnostic-event-design.md)
and its [follow-up plan](../plans/2026-09-26-m365-bff-403-direct-server-diagnosis.md)
remain unchanged until review. This draft neither supersedes the historic
#739/#632 gates nor authorizes provider access.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-bff-403-operator-read
leading_issue: https://github.com/notariat8/NaC/issues/756
risk_gate: Human Approval
delivery_mode: Protected PR
review_gates:
  - Privacy
  - Secrets
  - Policy
  - External Service
  - Human Approval
acceptance_ids:
  - AC-756-OR-01
  - AC-756-OR-02
  - AC-756-OR-03
  - AC-756-OR-04
  - AC-756-OR-05
validation_commands:
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_doc_links.py
  - graft check
```

## Purpose and boundary

The protected current client evidence from 25 September 2026 shows
`spfx_subject_available=true` and HTTP 403 for the synthetic workbench GET.
It does not prove whether Azure in front of the BFF or a BFF branch produced
the response. **AC-756-OR-01:** Before new code or deployment, inspect the
current server state read-only at most once. This text does not bypass the
existing `LOCAL_INACTIVE_ONLY` contract or the production
`BLOCKED_NO_REFRESH_CAPABILITY` stop. A later implementation requires a
forward-versioned, reviewed operator contract and a separate exact approval.

There is no generic driver, unrestricted Azure search, new Teams test, or
restart of the terminal #739 run.

## Closed target and read sequence

All braced parameters are **protected runtime bindings**, not guesses:
`{bound_subscription}` comes from the approved test target;
`{bound_component}` and `{bound_app_id}` come from uniquely verified Azure
metadata; `{bound_workspace}` comes from the uniquely linked Application
Insights component. The values and byte-exact URI hashes are bound only
after this local design review and before any real GET, in repository-external
evidence readable only by the operator. A different tenant or resource group,
or multiple matches, stops the run. The contract may not accept a free URL.

**AC-756-OR-02:** The sequence below is closed. Each step has at most one GET
and only the stated output fields:

1. Function metadata:
   `GET https://management.azure.com/subscriptions/{bound_subscription}/resourceGroups/rg-nac-bff-test/providers/Microsoft.Web/sites/func-nac-bff-test-funktion8?api-version=2025-03-01`.
   Project only the exact resource ID, type, name, `kind`, `state`, and
   provisioning state. A 404 proves absence only after the exact subscription,
   resource group, and read permission have been established. A 401/403 or
   ambiguous response is `UNPROVEN`. This GET alone does **not** prove the
   deployed code or package version.
2. Only if the Function exists: one ARM GET restricted to its resource group,
   `Microsoft.Insights/components`, name fragment `appi-nac-bff-test-`, and
   at most two results:
   `GET https://management.azure.com/subscriptions/{bound_subscription}/resourceGroups/rg-nac-bff-test/resources?api-version=2021-04-01&$filter=resourceType eq 'Microsoft.Insights/components' and substringof('appi-nac-bff-test-',name)&$top=2`.
   Canonically percent-encode the readable URI and bind its exact bytes as
   the sole permitted request URI before any real access.
   Zero or two results, a `nextLink`, unexpected type, or wrong scope means
   `UNPROVEN` and no further search. Retain only name and resource ID.
3. Only for exactly one matching component:
   `GET https://management.azure.com/subscriptions/{bound_subscription}/resourceGroups/rg-nac-bff-test/providers/Microsoft.Insights/components/{bound_component}?api-version=2020-02-02`.
   Allow only resource ID, `properties.AppId`, `properties.IngestionMode`,
   `properties.WorkspaceResourceId`, `properties.RetentionInDays`,
   `properties.SamplingPercentage`, and provisioning state. Never print,
   store, or hash `ConnectionString`, `InstrumentationKey`, tokens, or other
   excluded fields. Because the API may return those fields, technically
   prove response projection **before** this GET or stop here. The actual
   link to the expected BFF needs separate
   proof; a similar name is insufficient.
4. For workspace-based ingestion, only for the exact workspace bound in step
   3:
   `GET https://management.azure.com{bound_workspace}?api-version=2025-07-01`.
   Project only the exact resource ID and `properties.retentionInDays`.
   The workspace ID must be a canonical ARM resource path without its own
   query or fragment and belong to the same test scope. Missing or
   insufficient retention for the evidence window blocks the log query.

Official API shapes: [Web Apps Get](https://learn.microsoft.com/en-us/rest/api/appservice/web-apps/get?view=rest-appservice-2025-03-01),
[Resources List by Resource Group](https://learn.microsoft.com/en-us/rest/api/resources/resources/list-by-resource-group?view=rest-resources-2021-04-01),
[Insights Components 2020-02-02](https://learn.microsoft.com/en-us/azure/templates/microsoft.insights/2020-02-02/components),
and [Log Analytics Workspace Get](https://learn.microsoft.com/en-us/rest/api/loganalytics/workspaces/get?view=rest-loganalytics-2025-07-01).

## Single historic log query

**AC-756-OR-03:** Only after target identity, capture, retention, and read
permission are proven may one GET target
`https://api.applicationinsights.io/v1/apps/{bound_app_id}/query`. Its `query`
URL parameter contains only this byte-exactly bound KQL query. No raw URL,
path, request ID, or personal field is returned:

```kusto
requests
| where timestamp between (datetime(2026-09-25T10:42:03.397Z) .. datetime(2026-09-25T10:42:10.487Z))
| where url startswith "https://func-nac-bff-test-funktion8.azurewebsites.net/v1/workspaces/notary_team_01/matters/NAC-SYN-MATTER-001/workbench-snapshot"
| summarize telemetry_rows=count(), http_401=countif(resultCode == "401"), http_403=countif(resultCode == "403"), other=countif(resultCode !in ("401", "403"))
```

The [Application Insights Query GET](https://learn.microsoft.com/en-us/rest/api/application-insights/query/get?view=rest-application-insights-v1)
and [request telemetry model](https://learn.microsoft.com/en-us/azure/azure-monitor/app/data-model-complete)
support the API and field shape. The query counts telemetry rows only;
sampling, disabled collection, and empty results must not be read as “no
request.” The current BFF source does not prove a persisted
`request_correlation_binding_sha256` for the historic request. Thus even a
single concurrent 403 is **not** unique correlation or a concrete permission
reason. The result is at most `TEMPORAL_STATUS_ONLY`; the cause remains
`UNPROVEN`.

## Authentication, privacy, and stops

**AC-756-OR-04:** A later operator run may use only the protected,
pre-verified existing Funktion8 account and its existing read permissions.
Azure CLI is only a possible transport, not an approval or proof of a single
GET, redirect/retry suppression, or refresh bounds. A technically verified
transport must enforce GET-only, exact hosts and URIs, at most one call per
allowed resource, and no redirects, retries, paging, free bodies, or raw
response logs. If it cannot, the run remains blocked. A silent token refresh
if necessary, including a cache write in the existing current-user-only
store, is a **separate, explicitly approved credential operation**. No
browser sign-in, device code, account or tenant switch, token export, or
credential contents. 401/403, authentication prompt, multiple matches,
unexpected fields, or unredactable response stops without retry.

**AC-756-OR-05:** This draft grants zero provider reads, credential writes,
deployments, tenant writes, or #739/#632 runs. After spec review come a
DE/EN plan, forward-versioned contract, synthetic negative tests, and local
validation. Before the first real GET, final commit/tree, receipt pair,
target, account principal, permission, DPA basis, transport, and exact
URI/query hashes are separately verified and approved. If Stage A yields
only `UNPROVEN`, the already planned private #756 instrumentation becomes the
**justified** next path, still subject to its own approval. The actual
permission fix follows only from a proven denial reason.
