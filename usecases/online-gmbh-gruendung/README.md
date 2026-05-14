# Online GmbH Formation

Status: active intake

Source repository checked on 2026-05-14: `ofunk/Online-GmbH-Gruendung`

The source repository is empty. This folder is now the canonical location for
the online GmbH formation usecase in this repository.

## Goal

Prepare a notary-office usecase package for online GmbH formation. The package
will bind notary-facing plugins, workflow contracts, deterministic Python
checks, approvals, and evidence metadata.

## Boundaries

- No legal advice is generated as final truth.
- No notarial system is automated without an explicit reviewed connector.
- No real personal data or secrets are stored in the repository.
- Human review remains mandatory for sensitive notarial steps.

## Initial Dependencies

| Layer | Dependency | Purpose |
| --- | --- | --- |
| Plugin | `noc-regulated-core` | Shared regulated workflow guardrails. |
| Plugin | `noc-cyberjack-rfid` | Local card and SAK readiness. |
| Plugin | `noc-bnotk-xnp` | XNP readiness for notary-side work. |
| Plugin | `noc-handelsregister` | Register filing readiness after XNP gate. |
| Workflow | `workflows/contracts/` | Contract for intake, approvals, data classes, and evidence. |
| Workflow | `workflows/python/` | Deterministic validation and plan-preview execution. |

## Delivery Plan

1. Define intake contract for founders, company data, capital, representation,
   documents, and approvals.
2. Bind identity and notary-readiness gates to plugin outputs.
3. Create dry-run package preparation workflow.
4. Define evidence metadata for review, signature, filing readiness, and Day2
   follow-up.
5. Validate with a synthetic, non-personal test case.
