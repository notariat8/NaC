# Versioned read-only driver for the Teams current-state diagnostic – implementation plan

Status: Plan approved for test-first implementation; no driver-release or real-read approval

Date: September 23, 2026

Spec: [Versioned read-only driver](../specs/2026-09-23-m365-current-state-read-driver-design.md)

Leading issue: [#748](https://github.com/notariat8/NaC/issues/748)

Base: `main` `1b65259b9b4953a3b048be850c7953897b8eab83` / tree `1723094af6a398077be25f7897888faf0159069c`. The new protected Draft PR is reviewed separately from delivered PRs #749 and #751.

Delivery Mode: Protected PR. Risk Gate: Human Approval.

## Deliverables and sequence

1. **Release contract first:** Create a separate `workflows/verification-contracts/m365-current-state-read-driver.verification.json` with exact ACs, artifacts, distinct `OFFLINE_REVIEWABLE` and `LIVE_CAPABLE` states, dependency and zero-side-effect matrices. It binds the existing [#748 contract](../../../../workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml) by file digest; that historical contract and its delivered PR/merge evidence remain unchanged.
2. **Closed resources:** `workflows/contracts/m365-current-state-read-driver-resources.contract.json` defines the six fixed Microsoft GET families, origins, API versions, path templates, permitted bound placeholders, fixed query fields, response projections, and limits. The request-log port permits only Application Insights query GET with a compiled, parameter-bound KQL template. If Entra or SharePoint evidence cannot be projected completely from one GET, the port blocks; the #748 counter matrix is not expanded.
3. **Test-first binding:** `tests/test_m365_current_state_read_driver.py`, `tests/test_m365_current_state_access_gate.py`, `tests/test_spec_traceability.py`, and negative cases in the existing #748 diagnostic test first cover red cases for dummy/missing source, binary, bundle, CycloneDX, SPDX, corresponding source or license evidence, and incomplete third-party attribution inventory; unknown runtime file; wrong owner/DACL/file ID/hash/hardlink/reparse; forged resource template; wrong method, host, query, status, `Location`, `nextLink`, retry, login/refresh attempt, or raw/PII output. Governance fixtures prove same-principal aliases do not extend four-eyes or permissions, uncited two-person claims block, `OWNER_SOLO_APPROVAL` has `four_eyes_satisfied=false`, and a cited applicable duty yields `BLOCKED_SINGLE_PRINCIPAL`. Read fixtures count four Microsoft GETs for two `SPFX_SUBJECT_MISSING` acquisitions or twelve for each other complete double acquisition and zero further requests after a blocked projection. Request URL, query, and target ID must not appear in errors or logs. Tests remain hermetic and use fakes.
4. **Narrow Python source:** `src/nac_bff/current_state_read_driver.py` implements only the closed operations and redaction projections. HTTP transport and authentication capability are separate interfaces. Without a proven no-refresh capability, the Microsoft port factory remains `BLOCKED_NO_REFRESH_CAPABILITY` before touching credentials, authentication, or network. Neither Azure nor M365 CLI is silently used as a substitute. The existing #748 composition and process adapter are extended to verify the release record and all bundle files before one-shot consumption.
5. **Windows build:** `scripts/build_m365_current_state_read_driver.py` pins Python, a license-reviewed build tool, and dependencies. A directory bundle is the initial format; a one-file bundle with unbound temporary extraction is excluded. The build produces a closed file manifest, source/tool/commit/tree binding, binary hashes, classic CycloneDX/SPDX SBOMs, corresponding AGPL source, and visible NaC and third-party attribution with license texts outside the repository. `scripts/validate_m365_current_state_read_driver.py` reads these artifacts and matches the license inventory to every bundled component. `CANDIDATE_BUILT` does not prove independent source/binary correspondence; without such proof, neither byte reproducibility nor `OFFLINE_REVIEWABLE` is claimed.
6. **Integration and docs:** The existing `nac` CLI remains the operating edge; no free URL/KQL/token option is added. Synchronize DE/EN [diagnostic guide](../../m365-current-state-access-diagnostic.md), spec traceability, negative AI-SBOM decision, license/SBOM docs, and Windows CI. Real provider access, SPFx/BFF deployment, and #739/#632 paths remain excluded.
7. **Review and acceptance:** Run `implement -> review -> fix` with independent policy, docs-parity, and validation reviews; then focused negative tests, the full local Windows suite, Graft Build/Check, and Strict Doctor. Review the complete `main...HEAD` diff, commit list, and file list. Use separate forward commits, push without force, and evaluate all required remote CI. The PR stays Draft and stops before driver-release approval or a real read.

## Evidence matrix

| AC | Test objective | Evidence |
| --- | --- | --- |
| AC-748-RD-01 | Actual source, binary, classic SBOM, license, and manifest binding | Release validator and tampered digest/file fixtures |
| AC-748-RD-02 | Complete Windows bundle attestation | SID/DACL, file ID, hash, hardlink, reparse, and extra-file negatives |
| AC-748-RD-03 | Closed GET resources only, one read per provider port | Method/origin/path/query/redirect/retry/pagination negatives and counters |
| AC-748-RD-04 | Authentication without no-refresh proof and invalid governance decisions block before provider I/O | Factory/process fake with zero credential/network/provider counters; gate tests for same-principal aliases, an uncited two-person claim, solo owner with `four_eyes_satisfied=false`, and a cited duty with `BLOCKED_SINGLE_PRINCIPAL` |
| AC-748-RD-05 | Only redacted port fields leave the driver | PII, raw response, header, size, and unknown-field fixtures |
| AC-748-RD-06 | Hermetic integration with #748 gate and four classes | Positive/negative adapter, one-shot, drift, and classification tests; exactly four or twelve Microsoft GETs across two acquisitions and zero further requests after a blocked projection |
| AC-748-RD-07 | DE/EN, contract, SBOM, AI-SBOM, and CLI parity | Spec traceability, language, links, classic SBOM validator, independent review |
| AC-748-RD-08 | Protected Draft PR without live execution | Full diff, local mandatory gates, remote CI, no provider evidence |

## Validation commands for later implementation

```text
python -m unittest discover -s tests -p test_m365_current_state_read_driver.py
python -m unittest discover -s tests -p test_build_m365_current_state_read_driver.py
python -m unittest discover -s tests -p test_m365_current_state_access_gate.py
python -m unittest discover -s tests -p test_m365_current_state_access_diagnostic.py
python -m unittest discover -s tests -p test_spec_traceability.py
python scripts/validate_m365_current_state_read_driver.py
python scripts/validate_m365_current_state_read_driver.py --candidate <protected-external-candidate-path>
python scripts/validate_m365_current_state_access_diagnostic.py
python scripts/validate_spec_traceability.py
python scripts/validate_language_parity.py
python scripts/validate_doc_links.py
python -m unittest discover -s tests
graft build
graft check
python scripts/nac.py doctor --profile strict
git diff --check origin/main...HEAD
git diff --name-status origin/main...HEAD
git log --oneline origin/main..HEAD
```

`OFFLINE_REVIEWABLE` proves review and CI only. `LIVE_CAPABLE` **additionally and jointly** requires a technically verified no-refresh channel, actual current resource/bundle/SBOM bindings, and every existing #748 gate: protected DPA/AVV agreement and receipt bindings, provider/tenant/target scope, account-specific read permission, `principal_id`, `OWNER_SOLO_APPROVAL` or `BLOCKED_SINGLE_PRINCIPAL` based on a concrete cited duty, required checks, one-shot marker, and authorization before port factory and every read. Driver-release approval and approval for exactly one real read are separate decisions. A passing synthetic run is not evidence of Microsoft access.

## Plan review before implementation

Policy review checks license, privacy, DPA/AVV, and provider boundaries; docs review checks DE/EN parity and links; validation review checks counterexamples and that gates execute before credential/provider I/O. Findings are corrected during implementation review. The `--candidate` command applies only after an actual protected bundle exists; the source-contract check does not replace it. This work involves neither login nor a real diagnostic run.
