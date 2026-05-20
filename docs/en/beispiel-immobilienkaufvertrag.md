# Example: Real-Estate Purchase Contract Without Real Mandate Data

This example shows the NaC flow for a real-estate purchase contract. It uses no
real names, no address, no purchase price and no land-register excerpt.

## 1. Select The Case Type

The usecase lives under
[usecases/immobilienkaufvertrag/](../../usecases/immobilienkaufvertrag). The
business-facing front page is
[usecases/immobilienkaufvertrag/README.md](../../usecases/immobilienkaufvertrag/README.md).

## 2. Show Open Questions

```bash
python scripts/nac.py kg case immobilienkaufvertrag
```

NaC shows open nodes for property, seller, buyer, purchase price, encumbrances,
financing, possession transfer and approvals.

## 3. Do Not Store Real Input In Git

Real data is not entered. The public KG state only tracks:

- which information is required,
- who reviews it,
- which documents or evidence are referenced,
- which gates block drafting, notarization or execution.

## 4. Show The Safe Editor View

```bash
python scripts/nac.py kg editor-view immobilienkaufvertrag
```

The editor view shows form and checklist fields. `value` fields remain blocked
so nobody accidentally writes real mandate data to Git.

## 5. Human Approval Remains Decisive

AI can structure and prepare completeness. Notarial review, draft approval,
notarization decision and execution approval remain human responsibility.

## 6. Evidence Instead Of File Contents

The public reference stores evidence metadata only: status, reference, gate and
approval point. The actual register excerpt, ID, contract or payment evidence
belongs in a reviewed system, DMS or approved evidence store.

## 7. Check Quality

```bash
python scripts/nac.py doctor --profile strict
```

Only a green gate means the technical reference state is consistent. Productive
operation still starts only in a private fork with local roles, privacy review
and workstation checks.
