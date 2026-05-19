# Notary Start: Evaluate NaC In 15 Minutes

This document is for notary-office decision makers. It explains what NaC is,
what it is not, and how to run a first local check without real mandate data.

## Short Picture

NaC is a reference model for AI-first notary-office operations:

- AI structures input and open questions.
- Subject-matter staff and the notary decide.
- Git documents versions, reviews and approvals.
- Python checks rules and completeness.
- Real mandate data stays outside this public repository.

## What You Can Check

1. Which notarial case types are already modeled.
2. Which information, documents, approvals and technical gates are needed per
   case type.
3. Which plugin and workstation requirements appear for card, register, portal
   or identity paths.
4. Whether the model fits your office workflow.
5. Which parts should move into a private fork.

## What You Should Not Do

- do not enter real mandate data into this repository,
- do not commit ID data, register excerpts, prices, PINs or certificates,
- do not treat AI output as the final legal decision,
- do not start production without a private fork, role model, privacy review and
  local approvals.

## First Check

```bash
python scripts/nac.py status
python scripts/nac.py kg editor-view immobilienkaufvertrag
python scripts/nac.py doctor --profile strict
```

If these commands run, you can inspect available usecases, open case nodes and
whether the repository passes its own gates.

## Decision Questions

- Which three case types should be piloted first?
- Who owns subject-matter approval?
- Who operates the private fork?
- Which local systems and workstations must be connected?
- Where are real mandate documents and evidence stored outside Git?

## Next Documents

- [docs/en/reifegrad.md](reifegrad.md)
- [docs/en/cli.md](cli.md)
- [docs/en/ausfuehrungsmodell.md](ausfuehrungsmodell.md)
- [docs/en/glossar.md](glossar.md)
- [docs/en/beispiel-immobilienkaufvertrag.md](beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../../usecases/README.md)
- [docs/en/minimum-requirements.md](minimum-requirements.md)
- [docs/en/security-and-dsgvo.md](security-and-dsgvo.md)
- [docs/en/kg-editor-workstream.md](kg-editor-workstream.md)
- [docs/en/betriebsstart.md](betriebsstart.md)
