# Translation Status

## Binding Rule

`de` and `en` are mandatory standard languages according to
`policies/language-policy.yaml`. Every change to localized content must maintain
both languages.
For German law and notarial usecases, German is the leading and legally binding
language. English is translation or orientation only.

## Current State

- `docs/de/` contains the German source baseline.
- `usecases/` is maintained as the German subject-matter usecase surface.
- `docs/en/README.md` and `docs/en/START_HERE.md` are maintained as English entry documents.
- `prompts/en/` contains English prompt templates.
- The deeper subject-matter documents under `docs/en/` are present as the parallel maintenance surface and must be updated in sync with `docs/de/` for every subject-matter change.

## Next Useful Step

The deeper subject-matter documents under `docs/en/` should be translated in reading-priority order:

1. `docs/en/fachanwender-guide.md`
2. `docs/en/business-os.md`
3. `docs/en/governance.md`
4. `docs/en/quality-gate.md`
5. Cloud and eventstream runbooks
