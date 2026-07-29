# BusinessCaseType Live Write Readiness S4e

Status: `S4E_OFFLINE_READINESS`

Issue: [#702](https://github.com/notariat8/NaC/issues/702)

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: business-case-type-live-write-readiness-s4e
leading_issue: https://github.com/notariat8/NaC/issues/702
risk_gate: Human Approval
delivery_mode: Protected PR
review_gates:
  - Secrets
  - External Service
  - Human Approval
acceptance_ids:
  - AC-S4E-01
  - AC-S4E-02
  - AC-S4E-03
  - AC-S4E-04
  - AC-S4E-05
  - AC-S4E-06
  - AC-S4E-07
validation_commands:
  - python3 -m unittest tests.test_business_case_type_live_write_readiness tests.test_business_case_type_live_write_readiness_cli tests.test_business_case_type_live_write_readiness_contract
  - python3 scripts/validate_business_case_type_live_write_readiness.py
  - python3 scripts/nac.py contracts verify
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/nac.py doctor --profile strict
  - git diff --check
```

## Goal

S4e is the final local checkpoint before production adapter composition. It
introduces no credentials, provider clients, or live calls. It reports which
bound adapters and separated identities are still missing before a synthetic
live write in `notary_team_01`.

The CLI evaluates a contract-pinned repository snapshot. It performs no live
discovery and does not claim current Entra state or live authorization. Only a
later owner-gated gate may verify bound adapters and identities against
provider state.

## Identity decision

`NaC M365 Provisioning` remains a bootstrap and inspection identity and must
not write business-case data. The later write path requires a dedicated
identity with exactly Microsoft Graph `Sites.Selected` and site role `write`.
That identity, the provisioning app, and the BFF UAMI must be pairwise
distinct. The BFF UAMI remains `Sites.Selected/read`.

## Redacted adapter bindings

The readiness model accepts SHA-256 bindings only for the owner verifier and
trusted GitHub CLI, provisioning bootstrap and public certificate, write token
provider and Graph HTTP port, and Azure Blob WORM transport, target, CMK,
encryption scope, and locked immutability policy.

Raw identifiers, paths, certificates, keys, tokens, and provider responses are
neither read nor emitted.

## Status

`S4E_READY_OFFLINE` only means that the redacted production adapter bindings
are complete and separation of duties is exact. It grants no live approval.
In particular, a missing dedicated write identity yields fail-closed
`BLOCKED`.

## Acceptance criteria

- **AC-S4E-01:** A missing dedicated write identity blocks with zero
  credential, network, or tenant activity.
- **AC-S4E-02:** Provisioning, write, and BFF principals are pairwise
  distinct, with exact permissions and site roles.
- **AC-S4E-03:** Owner, toolchain, bootstrap, and certificate bindings are
  processed as SHA-256 only.
- **AC-S4E-04:** WORM target, CMK/encryption scope, and locked policy are
  bound only in redacted form.
- **AC-S4E-05:** Secret, file, HTTP, DNS, Graph, Azure, and tenant counters
  remain zero.
- **AC-S4E-06:** The slice creates or changes no Entra, SharePoint, Teams,
  Azure, or credential resource and authorizes no live write.
- **AC-S4E-07:** CLI, contracts, validator, tests, strict gate, independent
  review, and protected PR checks pass.
