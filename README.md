# NoC: Notariat as Code

This repository is maintained as a multilingual `Notariat as Code` reference.
Language-specific documentation and prompts use ISO-639 folder codes.

## Languages

- German: `docs/de/`, `prompts/de/`
- English: `docs/en/`, `prompts/en/`

`de` and `en` are mandatory standard languages. Any change to localized content
must update both languages, regardless of the language used in the prompt.

The binding rule is defined in `policies/language-policy.yaml` and checked by
`scripts/validate_language_parity.py`.

## Start

- German start path: `docs/de/START_HERE.md`
- English start path: `docs/en/START_HERE.md`
- German README: `docs/de/README.md`
- English README: `docs/en/README.md`

## Quick Check

```bash
python scripts/quality_gate.py --profile strict
```

The strict quality gate validates process files, tests, privacy rules,
governance sync, language parity, and cloud runbook parity.
