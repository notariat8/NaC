# Repository Refactor Plan: Single-Repository Modules

## Goal

This plan describes the target structure and a low-risk migration to a shared
core with vertical modules in the same repository.

## Target Structure

```text
processes/
  core/
    intake/
    approvals/
    billing/
    accounting_tax/
    audit_close/
  verticals/
    law_firm/
    notary/
    tax_office/
    property_management/
    software_company/
    wealth_management/
    carpentry/
```

## Mapping From Current State To Target Picture

- Existing generic process files are moved to `processes/core/`.
- Domain-related content is moved to `processes/verticals/<vertical>/`.
- Shared rules remain in [policies/](../../../policies) and [docs/en/](..).
- Domain activation remains centralized in
  [policies/process-policy.yaml](../../../policies/process-policy.yaml).

## Migration Sequence

1. **Inventory**
   - classify all existing process files as `core` or `vertical`.
2. **Prepare target paths**
   - create folder structure and fix naming convention.
3. **Migrate pilot vertical**
   - migrate one vertical first, recommended: `notary`, including core
     processes.
4. **Validation and review**
   - run validation/tests and subject-matter approval on the pilot vertical.
5. **Migrate additional verticals**
   - migrate `law_firm`, `tax_office`, `property_management`,
     `software_company`, `wealth_management`, `carpentry` on a fixed cadence.
6. **Closure**
   - update index/documentation references and tag release.

## Risks And Countermeasures

- **Risk:** unclear assignment of core vs vertical.
  **Countermeasure:** apply the boundary rule from
  [docs/en/service-model/core-vertical-blueprint.md](../service-model/core-vertical-blueprint.md)
  as binding.

- **Risk:** path changes break references.
  **Countermeasure:** migrate in small PRs and check references per PR.

- **Risk:** industry-specific special cases blur the core.
  **Countermeasure:** do not merge vertical-specific rules into core without
  multi-vertical evidence.

## Fallback Strategy

- Migration only through small, individually revertible PRs.
- Each migration block is released separately.
- If problems occur, roll back to the last approved release for new matters.
- Running matters keep their bound version.

## Acceptance Criteria

- All processes are clearly assigned to a target path.
- Validation and required reviews are successful.
- Documentation and policies reference the new structure correctly.
- At least one successful pilot vertical is proven productively.

## Implementation Boundary For This Round

This plan describes the refactor but does not perform it automatically. It is
the working basis for the next controlled migration round.
