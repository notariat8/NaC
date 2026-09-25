# Versioned read-only driver for the Teams current-state diagnostic

Status: Specification and plan approved; protected offline package preparation approved on 25 September 2026, finalization, driver release, and real provider run not approved

Date: September 23, 2026

Leading issue: [#748](https://github.com/notariat8/NaC/issues/748)

Base: `main` commit `1b65259b9b4953a3b048be850c7953897b8eab83`, tree `1723094af6a398077be25f7897888faf0159069c`; delivered [PR #749](https://github.com/notariat8/NaC/pull/749) and [PR #751](https://github.com/notariat8/NaC/pull/751). This spec is a new forward change and does not rewrite their historical bindings.

The later owner approval on `main` commit `862c87e1e378657f0066faed1bd36b830be2146d` and tree `3b1cfe5a4cfd7972912b961bfad46b713469f9fa` permits only test-first, protected, repository-external preparation of a Windows package candidate. Its preparation record remains `AWAITING_INDEPENDENT_LICENSE_EVIDENCE`; the separately gated release candidate, finalization, a usable no-refresh authentication channel, and any real Microsoft read remain blocked. The two locally validated client receipts from 25 September report an available SPFx subject and an HTTP-403 response; they do not prove the server-side access decision.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-current-state-read-driver-release
plan: docs/en/superpowers/plans/2026-09-23-m365-current-state-read-driver.md
leading_issue: https://github.com/notariat8/NaC/issues/748
risk_gate: Human Approval
delivery_mode: Protected PR
review_gates:
  - External Service
  - Human Approval
  - Privacy
  - Secrets
  - Platform
  - Policy
affected_artifacts:
  - AGENTS.md
  - .codex/agents/nac-policy-reviewer.toml
  - .pi/agents/nac-policy-reviewer.md
  - docs/de/superpowers/specs/2026-09-23-m365-current-state-read-driver-design.md
  - docs/en/superpowers/specs/2026-09-23-m365-current-state-read-driver-design.md
  - docs/de/superpowers/plans/2026-09-23-m365-current-state-read-driver.md
  - docs/en/superpowers/plans/2026-09-23-m365-current-state-read-driver.md
  - workflows/contracts/m365-current-state-read-driver-resources.contract.json
  - workflows/contracts/m365-current-state-read-driver-license-catalog.json
  - workflows/verification-contracts/m365-current-state-read-driver.verification.json
  - src/nac_bff/current_state_read_driver.py
  - src/nac_bff/current_state_read_driver_release.py
  - src/nac_bff/current_state_read_driver_sbom.py
  - src/nac_bff/current_state_access_adapters.py
  - src/nac_bff/current_state_access_composition.py
  - src/nac_bff/activation_security_windows.py
  - scripts/build_m365_current_state_read_driver.py
  - scripts/validate_m365_current_state_read_driver.py
  - scripts/quality_gate.py
  - scripts/validate_m365_current_state_access_diagnostic.py
  - scripts/validate_spec_traceability.py
  - tests/test_m365_current_state_read_driver.py
  - tests/test_build_m365_current_state_read_driver.py
  - tests/test_m365_current_state_read_driver_sbom.py
  - tests/test_m365_current_state_access_diagnostic.py
  - tests/test_m365_current_state_access_gate.py
  - tests/test_activation_security_windows.py
  - tests/test_spec_traceability.py
  - docs/de/m365-current-state-access-diagnostic.md
  - docs/en/m365-current-state-access-diagnostic.md
  - docs/de/sbom-for-ai.md
  - docs/en/sbom-for-ai.md
  - docs/de/sbom-products.md
  - docs/en/sbom-products.md
  - policies/sbom-policy.yaml
  - .github/workflows/windows-portability.yml
  - assets/docs/generic-workbench/VIS-721-manifest.json
acceptance_ids:
  - AC-748-RD-01
  - AC-748-RD-02
  - AC-748-RD-03
  - AC-748-RD-04
  - AC-748-RD-05
  - AC-748-RD-06
  - AC-748-RD-07
  - AC-748-RD-08
validation_commands:
  - python scripts/validate_m365_current_state_read_driver.py
  - python scripts/validate_m365_current_state_read_driver.py --candidate <protected-external-candidate-path>
  - python -m unittest discover -s tests -p test_m365_current_state_read_driver.py
  - python -m unittest discover -s tests -p test_build_m365_current_state_read_driver.py
  - python -m unittest discover -s tests -p test_m365_current_state_read_driver_sbom.py
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_doc_links.py
  - python scripts/validate_m365_current_state_access_diagnostic.py
  - python -m unittest discover -s tests -p test_m365_current_state_access_diagnostic.py
  - python -m unittest discover -s tests -p test_m365_current_state_access_gate.py
  - python -m unittest discover -s tests -p test_spec_traceability.py
  - graft build
  - graft check
  - python scripts/nac.py doctor --profile strict
```

## Purpose and boundary

The existing [#748 diagnostic contract](../../../../workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml) requires a reviewable driver before a real read. The current composition attests only the external executable path and checks source, classic SBOM, and resource digests merely for hexadecimal shape. This design makes those claims verifiable against actual release artifacts. It remains limited to the synthetic `notary_team_01` workspace and the “NaC Vorgangsansicht” Teams app.

This design authorizes neither a Microsoft read nor consumption of the one-shot diagnostic gate. Terminal Issue #739 and Issue #632 remain separate.
The `--candidate` command in traceability is a **later** package gate and is
not run under the current preparation-only approval; without a finalized, separately approved
package, AC-748-RD-01 remains open at artifact level.

## Scope and design decisions

1. Separate versioned Python source implements only the nine already closed operations in the [#748 contract](../../../../workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml). `local_git_gate`, `github_gate`, and `client_observation_receipt` retain their local or separately credential-write-guarded edges; none receives Microsoft network capability.
2. Windows receives a standalone attested executable release built with a pinned tool. A one-file bundle that unpacks into unbound temporary paths is insufficient. For a directory bundle, the entry executable **and every** loaded runtime/library file must be checked against a closed manifest, owner, current-user-only DACL, file identity, hardlink, and reparse boundary. Tool, version, build command, source commit/tree, input digests, and binary digests are bound in the release record; reproducibility must not be claimed without byte-for-byte replay.
3. Release binding includes actually generated CycloneDX JSON and SPDX JSON SBOMs, the AGPL-3.0-or-later license and corresponding NaC source, and licenses of all bundled runtime components. Syft 1.52.0 reports Windows binary packages using `syft:location:*:path` and SPDX package/file relationships, but does not identify every bundled file as a package. The validator reconciles both formats for discovered packages, attests **every** bundle file separately, and requires explicit attribution of undiscovered files. It invents no SBOM packages or file edges. Distribution must include [NOTICE](../../../../NOTICE), third-party attribution, and license texts. An operator inventory and hashes alone are insufficient: each license, source, and file attribution must also match a separately versioned and reviewed [license catalog](../../../../workflows/contracts/m365-current-state-read-driver-license-catalog.json). Finalization blocks while its status is `PENDING`.
4. A canonical resource manifest binds each port's exact HTTPS origin, API version, path template, allowed placeholders, fixed query structure, output fields, and at most one GET per acquisition. Placeholders come only from protected, already-bound target inputs, never CLI arguments, redirects, response URLs, or open search. Pagination, `$batch`, broad tenant/resource listing, and arbitrary KQL are excluded.
5. A dedicated HTTP transport accepts only `GET`, no body, redirect, or retry. Unexpected HTTP status, `Location`, pagination links, authentication challenges, oversized or non-redactable responses block before another request. Raw responses, headers, tokens, request URLs and queries, target IDs, and personal data are neither emitted nor persisted, including in errors or process logs. The existing reduced port schemas remain exact.
6. Microsoft authentication is a separate capability. Existing Azure/M365 CLIs are not evidence of no-refresh behavior because they may refresh internally before a GET. Until an established channel technically and testably guarantees no refresh, the Microsoft transport factory is disabled and ends **before** credential, authentication, or provider access with `BLOCKED_NO_REFRESH_CAPABILITY`. Token export/import, browser, broker, or device-code login is not a fallback.
7. The new release contract references the historical #748 contract by file digest prospectively; that historical contract file and PR #749/#751 commit, tree, parent, and scope evidence remain unchanged. The spec-traceability validator must check AC and plan parity for this new `spec_id` too; an empty command list or placeholder is not evidence. Before one-shot gate consumption, the #748 composition rechecks the real release record, resource manifest, and attested runtime. `LIVE_CAPABLE` is possible only in conjunction with every existing #748 gate: protected DPA/AVV agreement and receipt bindings, provider/tenant/target scope, account-specific read permission, `principal_id`, exactly bound owner decision, remote checks, one-shot marker, and authorization before port factory and each read. Driver-release approval and approval for exactly one real read are distinct decisions.

## Closed resource families

These are the only permitted API families. Before a production release, its manifest must fix the **concrete** path and query templates. If the required projection cannot be proven with exactly one GET per provider port, that port and the real run remain blocked. The agreed counter of six Microsoft reads per full acquisition is not silently increased.

| Port | Permitted GET family | Boundary |
| --- | --- | --- |
| Teams tab | Graph v1.0 `/teams/{team}/channels/{channel}/tabs/{tab}` | Bound tab only, no channel search. |
| SharePoint app catalog | SharePoint `/_api/web/tenantappcatalog/AvailableApps/GetById('{product}')` on bound catalog site | Bound SPFx product only. |
| Entra API permission | Graph v1.0 on an exactly bound service-principal/grant resource | No directory search; incomplete permission projection blocks. |
| Azure Function metadata | ARM `Microsoft.Web/sites/{function}` with fixed API version | No app-settings, secret, or content query. |
| Azure Function request log | Application Insights v1 GET `/apps/{app}/query` | Fixed parameterized query limited to closed window and correlation binding; no free KQL input. |
| SharePoint access decision | Graph v1.0 on exactly bound synthetic site/list-item resource | No real matters or list/site search; incomplete evidence blocks. |

Microsoft documents [Teams tab GET](https://learn.microsoft.com/en-us/graph/api/channel-get-tabs?view=graph-rest-1.0), [SharePoint ALM GET](https://learn.microsoft.com/en-us/sharepoint/dev/apis/alm-api-for-spfx-add-ins), [service-principal grants](https://learn.microsoft.com/en-us/graph/api/serviceprincipal-list-oauth2permissiongrants?view=graph-rest-1.0), [ARM site GET](https://learn.microsoft.com/en-us/rest/api/appservice/web-apps/get?view=rest-appservice-2024-04-01), [Application Insights query GET](https://learn.microsoft.com/en-us/rest/api/application-insights/query/get?view=rest-application-insights-v1), and [Graph list-item GET](https://learn.microsoft.com/en-us/graph/api/listitem-get?view=graph-rest-1.0). These API documents do not prove current permissions, an active BFF, or a successful diagnostic read.

## Risks and fail-closed decisions

- An apparent GET in a CLI may trigger a refresh. `az rest` and the M365 CLI are therefore not connected as production transport without proof; an offline mock cannot supply that proof.
- One GET may not provide all facts for a port. The outcome is then `BLOCKED_RESOURCE_PROJECTION_INCOMPLETE`; no extra request, POST batch, or broader search is improvised.
- A bundle may contain libraries outside the attested entry executable. Without full bundle and license/SBOM proof, the outcome is `BLOCKED_DRIVER_RELEASE_BINDING`.
- Preparation produces only a current-user-only bundle and `preparation.json` with `AWAITING_INDEPENDENT_LICENSE_EVIDENCE`, not a release record. The first preparation is review evidence; once the catalog is approved on a new commit, a fresh preparation with **identical** file, tool, SBOM, driver-source, and resource digests is required. Finalization needs the reviewed license catalog bound to the Git tree and protected external license texts. A catalog entry is reviewable evidence, not automatic authenticity verification of a third-party download server. Until its source hashes and license texts are independently checked, `BLOCKED_LICENSE_PROVENANCE` applies; the original repair approval allowed no candidate, while the later approval bound above allows only its preparation.
- A client receipt proves neither a BFF request nor request telemetry. Missing, uncorrelated, or non-redactable log evidence blocks; it is not guessed to be `BFF_REQUEST_NOT_OBSERVED`.
- The #748 account/principal rules remain unchanged. Without a specifically cited applicable external two-person duty, `OWNER_SOLO_APPROVAL` is permitted and records `four_eyes_satisfied=false`. A specifically cited applicable duty with only one principal blocks as `BLOCKED_SINGLE_PRINCIPAL`. Multiple accounts of one principal neither constitute four-eyes approval nor expand provider permission.

## Acceptance criteria

- **AC-748-RD-01:** Release manifest and validator bind actual source, build, binary, classic SBOM, license, corresponding source, and resource artifacts by hash, version, and scope; dummy digests, missing third-party notices, and incomplete license inventory fail.
- **AC-748-RD-02:** Every Windows bundle runtime file is bound before launch by the Windows security backend to owner, DACL, file identity, hash, hardlink, and reparse boundary; substitution, extra files, and path drift block.
- **AC-748-RD-03:** The resource manifest allows only six bound Microsoft GET families and no more than one GET per port and acquisition; other methods, hosts, paths, queries, pagination, and redirects fail without a second request.
- **AC-748-RD-04:** Login, token refresh, credential export/import, and credential/provider writes are technically excluded or the production port blocks before access with `BLOCKED_NO_REFRESH_CAPABILITY`. The governance negative matrix proves same-principal account aliases do not extend four-eyes or permissions, uncited two-person claims are rejected, `OWNER_SOLO_APPROVAL` records `four_eyes_satisfied=false`, and a cited applicable duty yields `BLOCKED_SINGLE_PRINCIPAL`.
- **AC-748-RD-05:** Provider responses are reduced in memory to existing port fields; unknown or personal fields, headers, raw responses, request URLs/queries, target IDs, and oversized data fail without public output or log leakage.
- **AC-748-RD-06:** Synthetic positive and negative tests separately prove source/SBOM/bundle binding, HTTP boundaries, four total Microsoft GETs for `SPFX_SUBJECT_MISSING` or twelve for each other complete double acquisition, zero further requests after blocked projection, auth blocking, one-shot gate, and four diagnostic classes; they use no real provider.
- **AC-748-RD-07:** DE/EN spec, plan, verification contract, spec traceability, classic SBOM and AI-SBOM decision, and operator/security docs are synchronized. Pinned build/runtime dependencies appear in the classic SBOM and, where minimum requirements are affected, in the AI-SBOM inventory or as justified pending entries. No new AI model or external AI data flow is claimed.
- **AC-748-RD-08:** The full `main...HEAD` scope, local mandatory gates, and remote CI are reviewed. The PR remains Draft; driver release and exactly one real read then require separate exactly bound approvals.

## Non-goals

No login, token refresh, credential write, real Microsoft/tenant/provider access, app/BFF deployment, role or permission change, #739 release, #632 live run, or merge in this design/plan phase. This spec does not resolve the missing no-refresh authentication capability.
