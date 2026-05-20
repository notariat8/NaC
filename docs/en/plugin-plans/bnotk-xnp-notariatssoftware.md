# Plugin Plan: BNotK XNP Notary-Software Companion

Status: `proposed`

## Core Decision

`nac-bnotk-xnp` is the local companion for XNP and notary-software readiness. It
does not replace XNP, does not authenticate as a notary and does not control
protected notary software without an approved interface.

The plugin checks whether the local workstation is ready for an XNP-oriented
workflow and turns a NaC intent into a human-readable plan with approval and
evidence gates.

## Sequence For Commercial Register Online Filings

For a notary-side online commercial-register filing, the sequence is:

1. `nac-cyberjack-rfid`
   - checks card, reader, PC/SC, SAK lite or XNP card path and secureFramework.
2. `nac-bnotk-xnp`
   - checks local XNP login, official-capacity context, XNotar/register module
     or exchange-folder route.
3. `nac-handelsregister`
   - handles register track, HRA/HRB plausibility, package readiness and
     evidence metadata.

`nac-bnotk-xnp` therefore starts only after the card/SAK gate is sufficiently
clear.

## Goal

The plugin should:

- inspect local XNP prerequisites,
- make missing workstation prerequisites visible,
- structure XNP-related plan previews,
- check whether a notary-office workflow has an official-capacity context,
- prepare handoff metadata for XNotar/register-package flows,
- record evidence metadata without storing credentials or mandate content.

## Non-Goals

- No PIN, card or certificate handling.
- No storage of notary credentials.
- No portal automation.
- No XNotar import or filing without a separate approved adapter.
- No replacement for notarial judgment, review or signing.

## Day 0

- Confirm operating system and local workstation profile.
- Confirm `nac-cyberjack-rfid` readiness result.
- Confirm XNP installation and supported version.
- Confirm access route: local XNP login, official-capacity context, XNotar
  module or exchange folder.
- Confirm software-vendor interface boundary.
- Define reviewer and approval roles.

## Day 1

The plugin creates a plan preview with:

- workstation readiness,
- card/SAK gate reference,
- XNP login and context status,
- XNotar/register module or exchange-folder route,
- missing prerequisites,
- approval gates,
- evidence metadata.

Typical tasks:

- translate NaC intent into a human-readable XNP plan,
- check whether a register package can be prepared,
- identify missing data or documents,
- prepare handoff without executing protected actions.

## Day 2

- Re-run readiness after XNP, driver, browser or OS updates.
- Document failed logins or missing official-capacity context.
- Track package versions and evidence references.
- Reconcile manual workstation changes back into Git.

## Security Model

- Credentials, PINs and certificates stay outside Git.
- Logs are redacted by default.
- No real mandate content is stored in repository examples.
- Every filing-adjacent step has a human approval gate.
- The plugin can report "not ready" without failing the whole workflow.

## Source Assessment

Official BNotK/XNP and notary-software-vendor interfaces remain authoritative.
The plugin is allowed to support readiness, planning and evidence only until a
formal interface contract and security review approve a deeper adapter.

## Acceptance Criteria For Pilot

- The plugin can answer whether the XNP workstation prerequisites are present.
- It can reference the upstream card/SAK gate result.
- It creates a plan preview without executing protected XNP actions.
- It stores no credentials, PINs, certificates or mandate content.
- It returns a useful "not ready" state when XNP or the reader path is missing.

## Sources

- BNotK/XNP online help and notary-software vendor integration documentation.
- Local NaC card-gate plan:
  [cyberjack-rfid-plugin-integration.md](cyberjack-rfid-plugin-integration.md)
