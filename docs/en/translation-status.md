# Translation Status

## Binding Rule

`de` and `en` are mandatory standard languages according to
[policies/language-policy.yaml](../../policies/language-policy.yaml). Every
change to localized content must maintain both languages.
For German law and notarial usecases, German is the leading and legally binding
language. English is translation or orientation only.

## Current State

- The German source baseline remains leading and is maintained in the German
  language path without being linked from this English reading flow.
- [README.md](../../README.md) is the German-led GitHub root page and now shows
  start paths in a Deutsch/English table.
- [usecases/](../../usecases) is maintained as the German subject-matter
  usecase surface; immediate usecase READMEs are short German front pages that
  link to the matching KG.
- `SKILL.md` files are maintained with German subject-matter instructions and a
  short English summary; technical names, folders, commands and IDs remain
  English/ASCII.
- [docs/en/README.md](README.md) and [docs/en/START_HERE.md](START_HERE.md) are
  maintained as English entry documents.
- Audience paths, maturity, glossary and example path are maintained in `de` and
  `en`.
- The main English entry, governance, operations, eventstream, service and
  active plugin-plan documents are no longer simple file mirrors.
- Old Omnistation imports under
  [docs/en/plugin-plans/omnistation-imports/](plugin-plans/omnistation-imports/)
  are English import notes. German original artifacts remain in the separate
  German language path and are not linked from English reading-flow pages.

## Technical Control

[scripts/validate_language_parity.py](../../scripts/validate_language_parity.py)
checks:

- mandatory language folders for `de` and `en`,
- file parity for localized surfaces,
- root README and usecase language rules,
- German KG and usecase README markers for immediate usecase folders,
- skill language markers for German-led `SKILL.md` files with an English
  summary,
- no identical Markdown/text mirrors between `docs/de` and `docs/en`,
- language-local Markdown links for localized documents and prompts.

## Next Useful Step

Deeper subject-matter texts can still be refined stylistically. New
subject-matter changes must now update both language paths directly.
