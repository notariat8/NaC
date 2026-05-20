# Startup Verification

## What Is Checked

The startup check verifies locally:

- required commands (`git`, `python`, `gh`)
- profile-dependent commands (`node`, `npm`)
- recommended commands (`pandoc`, `code`)
- minimum Python version
- minimum Node.js version when the selected profile requires it
- required files and policies
- optional VS Code Copilot extensions
- optional process validation and tests
- local Windows, morris and driver indicators for the notary workstation

## How To Run The Check

Check the base setup:

```bash
python scripts/startup_check.py --profile base --ide auto
```

Check the base setup plus process and unit tests:

```bash
python scripts/startup_check.py --profile base --ide auto --run-tests
```

Strict VS Code path including Copilot extensions:

```bash
python scripts/startup_check.py --profile base --ide vscode --run-tests
```

For plugin development:

```bash
python scripts/startup_check.py --profile plugin-dev --ide auto
```

For the notary workstation, card reader, morris and XNP path:

```bash
python scripts/startup_check.py --profile notary-workstation --ide auto
python scripts/nac.py plugins card-readiness --manual-card-present yes --manual-rfid-off yes --probe-morris-api --json
python scripts/nac.py plugins xnp-reader-prompt --manual-card-present yes --manual-rfid-off yes --probe-morris-api --json
python scripts/nac.py operator --open
```

The operator webapp is only a local operator channel. It talks to the
CLI-started bridge on `127.0.0.1`; the bridge runs approved check scripts in the
NaC workspace.

## Limits

- The check only sees locally available information.
- It does not replace GitHub server settings such as branch protection.
- It does not replace domain-system approval.
- With installed hardware, real local card-reader, morris, PC/SC, SAK/XNP and
  XNP readiness tests are possible. Productive card runs, signing, PIN capture
  and filings still need separate approval.
- A morris response such as `NoReader` or `NaCard` is enough for the technical
  middleware binding check without an inserted or attached card, but not for a
  productive card run.
- Forks must also adopt and actively use the check.
