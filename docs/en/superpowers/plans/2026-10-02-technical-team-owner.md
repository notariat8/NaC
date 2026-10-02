# Implementation plan: technical Team owner

Issue: [#766](https://github.com/notariat8/NaC/issues/766).
Spec: [Technical Team owner](../specs/2026-10-02-technical-team-owner-design.md).
Status: local correction commissioned; no tenant apply.

1. **Plan → review → fix:** Anchor the owner clarification in policy; map
   active creation plans, group/Teams owner checks and historical evidence
   separately. Independent review checks scope and security boundaries.
2. **Test-first:** Positive coverage for the sole technical owner; negative
   tests for missing, wrong, additional and malformed owners and mismatched
   group/Teams roles. Every failure proves zero writes.
3. **Implement → review → fix:** Explicit ownership in the offline Team plan;
   check every target Team before the first mutation; no automatic migration.
   Historical evidence stays unchanged and non-operative.
4. Synchronize policy, contracts, validators, DE/EN architecture, onboarding
   and relevant Codex/pi profiles. Do not remove license, principal or matter
   gates or replace them with Team ownership.
5. Run focused tests, privacy lint, contract/governance/language/traceability
   validators and a freshly built Graft graph. Independently review the
   complete `main...HEAD` diff; then
   create local commits and normally push to a draft PR. The complete local
   strict doctor and remote CI may run concurrently; never represent a
   running or failed gate as passed.
6. Successfully complete the full strict doctor and remote CI and evaluate
   all results. Stop before merge and any real Team-owner change;
   do not claim current tenant compliance.

AC-OWNER-01 through AC-OWNER-05 are covered by the tests and validators listed
in the spec. Reuse the existing `nac m365 teams-sharepoint plan`,
`privileged-plan` and `application-owner-readiness` CLI edges; do not create
a new live executor.

## Windows validation run

The full run uses native Windows encoding. A blanket UTF-8 mode does not
replace matching subprocess encodings: Python, Node and Windows system tools
may produce different output formats. On the verified workstation,
`PYTHONUTF8=0` and `PYTHONIOENCODING=cp1252` are process-local only; system and
user settings remain unchanged. When a check fails, first reproduce exactly
the affected tests and only after they pass start the final full strict
doctor. No check is omitted.
