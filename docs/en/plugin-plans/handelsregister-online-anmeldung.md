# Plugin Plan: Commercial Register Online Filing

Status: `proposed`

## Core Decision

`noc-handelsregister` is focused on preparing online commercial-register
filings.

Correction of the development sequence: for a real notary-side filing or
completion path, the Card/SAK gate (`noc-cyberjack-rfid`) is required first,
because XNP login tests are not robust without card, card reader, SAK lite or
XNP card path and secureFramework. Then `noc-bnotk-xnp` follows.
`noc-handelsregister` is then the subject-matter layer for register track,
HRA/HRB plausibility and package readiness.

Only a pure citizen or client preflight for `online.notar.de` can start without
notary/XNP authentication. This preflight must not trigger filing, notary
software control or notarial declarations.

The focus is HRA first because the user should be able to prepare concrete HRA
filings. The plugin must still check every input against the register track
first:

- HRA: typically registered merchant, OHG, KG and related partnerships.
- HRB: typically GmbH, UG and AG.

If a user says "HRA" but names a GmbH or UG, the plugin must make the likely
HRB track visible and ask for clarification.

## Operating Boundary

The plugin is not a register-retrieval or scraping plugin.

It may:

- structure the online filing case,
- check HRA/HRB track, legal form and missing information,
- ask for prerequisites of the notarial online procedure,
- for notary-side targets, refer to `noc-cyberjack-rfid` and then
  `noc-bnotk-xnp` as upstream card/XNP gates,
- prepare a filing package as plan preview,
- capture evidence metadata for package version, approval and later filing.

It must not:

- retrieve register data,
- automate protected portals,
- make notarially relevant declarations,
- replace signatures, identification or filing,
- store real ID, PIN, certificate or mandate data in the repository.

## Basis

According to IHK Munich, GmbHs and UGs can be formed online since
August 1, 2022: initially cash formations, and since August 1, 2023 also
contribution-in-kind or mixed formations. Certification of commercial-register
filings for all legal forms except associations has also been permitted online
since August 1, 2022. The procedure requires the Bundesnotarkammer app, an
official ID with eID function and a valid official photo ID.

## Day 0

- Clarify operating mode: citizen/client preflight or notary workstation.
- For notary workstation, complete `noc-cyberjack-rfid` first: card, reader,
  PC/SC, SAK lite or XNP card path and secureFramework.
- Then complete `noc-bnotk-xnp`: local XNP login, official-capacity context,
  XNotar module and exchange folder.
- Clarify register track: HRA, HRB or other register.
- Clarify legal form.
- Capture company name, seat, register court, participants and power of
  representation.
- Clarify notary route: online procedure or in-person appointment.
- Ask readiness for Bundesnotarkammer app, eID function, PIN and ID documents
  without storing values.
- Define reviewers and approval owners.

## Day 1

The plugin creates a plan preview with:

- operating mode, Card/SAK gate status and auth/XNP gate status,
- register track and plausibility warnings,
- missing required information,
- document list for the notary,
- questions for applicant or legal advice,
- approval checkpoint before notarial video communication,
- evidence metadata model for hashes and package versions.

## Day 2

- Follow up rejected or postponed filings.
- Document missing attachments, identification errors, signature errors and
  notary comments.
- Update package version and evidence metadata.
- Keep reusable templates in the repository only without real data.

## Output Shape

The plugin always returns these sections:

1. `Readiness`
2. `Application Package`
3. `Approval Needed`
4. `Evidence`
5. `Day2 Follow-up`

## Sources

- IHK Munich: [ihk-muenchen.de](https://www.ihk-muenchen.de/ratgeber/recht/gesellschaftsrecht/digitalisierung/)
- Bundesnotarkammer online procedure: [online.notar.de](https://online.notar.de/)
