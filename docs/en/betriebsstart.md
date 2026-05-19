# Operations Start: Private Fork And Local Checks

This document is for office admins, IT operations and technical owners who want
to evaluate NaC locally or prepare a private operating fork.

## Goal

The public NaC state is a template. Productive operation belongs in a private
environment with its own access control, roles, approvals and no real mandate
data in the public reference.

## Minimal Flow

1. Clone the repository.
2. Set up Python according to [docs/en/minimum-requirements.md](minimum-requirements.md).
3. Run the local base check.
4. Create a private fork or internal repository.
5. Define roles, CODEOWNERS and branch protection for your operation.
6. Only then check local workstation, plugin and system paths.

## Local Checks

```bash
python scripts/startup_check.py --profile base --ide auto --run-tests
python scripts/nac.py doctor --profile strict
```

For plugin or workstation work:

```bash
python scripts/nac.py plugins validate
python scripts/nac.py plugins install --mode link
python scripts/startup_check.py --profile plugin-dev --ide auto
python scripts/startup_check.py --profile notary-workstation --ide auto
```

After `nac plugins install --mode link`, reopen Codex so the local plugin
discovery can see the repo-local plugins in the new session.

## Operating Boundaries

- The private fork must not contain clear-text secrets.
- Mandate data belongs in reviewed systems, DMS or evidence stores, not in the
  public template.
- Local card, signature and portal paths are checked as readiness first.
- Write adapters need separate approval, privacy review and traceable
  responsibility.

## Next Documents

- [docs/en/minimum-requirements.md](minimum-requirements.md)
- [docs/en/cli.md](cli.md)
- [docs/en/ausfuehrungsmodell.md](ausfuehrungsmodell.md)
- [docs/en/startup-verification.md](startup-verification.md)
- [docs/en/plugin-operations/install-local-plugins.md](plugin-operations/install-local-plugins.md)
- [docs/en/operations/fork-and-release-operating-model.md](operations/fork-and-release-operating-model.md)
- [docs/en/pruefung-standardisierung-start.md](pruefung-standardisierung-start.md)
