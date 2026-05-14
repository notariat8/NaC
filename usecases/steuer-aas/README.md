# Steuer-aaS Tax Readiness

Status: active intake

Source repository checked on 2026-05-14: `ofunk/Steuer-aaS`

The source repository is empty. This folder is now the canonical location for
the Steuer-aaS tax-readiness usecase in this repository.

## Goal

Prepare a usecase package for tax-readiness workflows that are adjacent to
notarial formation and regulated entity setup. The usecase focuses on intake,
classification, tax-registration preparation, nonprofit or business tax
handoffs, review gates, and evidence metadata.

## Boundaries

- This usecase does not replace tax advice, legal advice, notarial review, or
  official filings.
- The LLM is an intake and structuring interface, not the tax authority or final
  professional judgment.
- No real tax IDs, personal data, bank data, certificates, ERiC credentials, or
  secrets may be stored in Git.
- External filing, submission, or portal automation requires a separately
  reviewed connector and explicit human approval.

## Initial Dependencies

| Layer | Dependency | Purpose |
| --- | --- | --- |
| Plugin | `noc-regulated-core` | Shared regulated workflow guardrails. |
| Plugin | `noc-elster-eric` | ELSTER/ERiC readiness, dry-run filing plans, and evidence companion. |
| Workflow | `workflows/contracts/` | Intake, data-class, approval, and evidence contract. |
| Workflow | `workflows/python/` | Deterministic validation, plan-preview, and completeness checks. |

## Candidate Workflow Scope

| Area | Example questions |
| --- | --- |
| Formation tax readiness | Which tax-registration data is needed after a notarial formation workflow? |
| Nonprofit handoff | Which AO52 or nonprofit pre-check outputs must be handed to tax advisors or the Finanzamt? |
| VAT and payroll readiness | Which flags, roles, and deadlines are relevant before operational start? |
| Evidence | Which decisions, versions, approvals, and handoff timestamps must be recorded? |

## Delivery Plan

1. Define intake contract for entity, activity, tax-advisor role, expected
   revenue classes, nonprofit flags, VAT flags, payroll flags, and deadlines.
2. Bind `noc-elster-eric` readiness outputs without storing credentials or
   submission secrets.
3. Create a dry-run tax-readiness plan preview.
4. Define evidence metadata for intake, review, handoff, filing-readiness, and
   Day2 follow-up.
5. Validate with synthetic, non-personal test data.
