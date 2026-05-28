# Single-Repo Plan For Notarial Usecases

## Goal

This plan replaces the earlier multi-domain migration idea. NaC remains one
repository for Notariat as Code. The target structure separates shared
notarial rules, concrete notarial usecases, runtime and integrations.

## Target Structure

```text
usecases/
  immobilienkaufvertrag/
  unterschriftsbeglaubigung/
  online-gmbh-gruendung/
  handelsregisteranmeldung/
workflows/
plugins/
policies/
docs/
```

## Principles

- New subject-matter examples are created only as notarial usecases under
  [usecases/](../../../usecases).
- Shared rules belong in [policies/](../../../policies) and are mirrored in
  agent-facing surfaces.
- Technical runtime fixtures under [processes/](../../../processes) are not
  additional product examples.
- Non-notarial domain sets are not accepted.

## Implementation Steps

1. **Fix the scope**
   - Mirror the notarial scope in policy, README, START_HERE and agent rules.
2. **Maintain the usecase catalog**
   - Keep existing usecases aligned with maturity and pilot readiness.
3. **Separate runtime fixtures**
   - Mark technical process examples as compatibility and test material.
4. **Select the pilot usecase**
   - Pilot real-estate purchase contract or signature certification first,
     using synthetic data.
5. **Check release binding**
   - Running matters remain on their bound version; new versions apply only to
     new matters.

## Risks And Countermeasures

- **Risk:** old multi-domain terms reappear in documentation or prompts.
  **Countermeasure:** search for non-notarial domain sets before PR completion.
- **Risk:** technical fixtures are misunderstood as product examples.
  **Countermeasure:** README and start documents point to
  [usecases/](../../../usecases) for examples only.
- **Risk:** local notary-office variants blur the reference standard.
  **Countermeasure:** variants only through change request, review and version
  binding.

## Exit Criteria

- README, START_HERE, policy and agent-facing surfaces describe NaC as
  notary-office-only.
- Onboarding prompts refer only to notarial usecases.
- Issue #3 describes notarial example processes instead of domain sets.
- `nac doctor --profile strict` passes.
