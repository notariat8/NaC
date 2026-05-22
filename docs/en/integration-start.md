# Integration Start: Systems, Plugins And Connectors

This document is for software vendors, integration partners and technical
product teams that want to connect NaC with existing notary-office software,
local workstation components or portals.

## Integration Principle

NaC treats external systems as separate responsibility and evidence layers. The
public repository models:

- which information and gates a case needs,
- which plugin readiness exists,
- which evidence is referenced,
- which data classes must not be stored in Git,
- which write paths require review before activation.

## Expected Integration Forms

- local readiness checks for workstation, middleware and card paths,
- connector contracts for structured input and output,
- evidence metadata instead of real document content,
- secure upload and read links for mobile app, object-store, database-blob or
  OneDrive paths,
- dry-run and plan preview before productive write actions,
- explicit human approval for sensitive steps.

## Mobile App And Secure Document Links

An integration may also provide a mobile client or participant app, for example
as a demo app named `n8-demonotariat` in the iOS App Store. The app receives no
blanket access to NaC. It receives only case- and purpose-bound links after
identity, role, case binding and approval state have been checked.

Allowed target patterns are:

- upload link into an object store,
- upload link into a database blob,
- upload or read link into OneDrive,
- read-only link to current matter information, where the case permits it.

Links must be short-lived, revocable, logged, tenant-bound and limited to
specific actions. The product repository stores no secret links, access tokens
or raw document content. NaC keeps only evidence such as hash, storage target
class, case binding, expiry, issuing role, approval state, malware/file-type
check and audit event.

## What An Integration Partner Should Provide

1. Functional boundaries and steps that must not be automated.
2. Data classes and storage locations.
3. Error and support model.
4. Versioning and compatibility window.
5. Test mode with synthetic data.
6. Evidence for whether an action runs locally, externally or manually.
7. Security model for mobile links, revocation, expiry and storage target.

## Relevant Repository Areas

- [plugins/README.md](../../plugins/README.md)
- [workflows/README.md](../../workflows/README.md)
- [workflows/contracts/README.md](../../workflows/contracts/README.md)
- [docs/en/ausfuehrungsmodell.md](ausfuehrungsmodell.md)
- [docs/en/authenticated-webapp-operating-model.md](authenticated-webapp-operating-model.md)
- [docs/en/plugin-plans/README.md](plugin-plans/README.md)
- [docs/en/plugin-operations/README.md](plugin-operations/README.md)
- [docs/en/sbom-for-ai.md](sbom-for-ai.md)

## Guardrail

An integration is dependable for NaC only when it is locally checkable, reviewed
for privacy, versioned, testable and bounded by a human approval process.
