# Notary Software Data Model for NaC

Status: working model for demo matters and later data-repository adapters

This page translates observable patterns from modern notary software into the
NaC data model. It does not replace a product analysis of individual vendors
and does not copy proprietary workflows. The goal is an open model contract
that notaries, staff, ISVs and reviewers can understand.

## Source Picture

Public product information shows recurring building blocks:

| Source | Relevant signal for NaC |
| --- | --- |
| [NOAH features](https://noah-notariatssoftware.de/funktionen/) | Contacts, properties, jurisdiction, matter data, Word drafting, document management, inbox, status, execution, cost accounting and electronic interfaces belong together. |
| [LawX product](https://www.lawx.de/product) and [LawX overview](https://www.lawx.de/impulse/notarsoftware) | The matter is the center; intake data, register information, drafting, execution, deadlines and billing are prepared, the human approves. |
| [TriNotar](https://www.wolterskluwer.com/de-de/solutions/trinotar) and [TriNotar discovery](https://www.wolterskluwer.com/de-de/solutions/trinotar/trinotar-entdecken) | E-file, electronic side file, document versions, inbox, to-dos, OCR, workflow support and export/viewer paths are core requirements. |
| [CVC NOTRE feature scope](https://cvcit.de/it-funktionsumfang/) and [CVC flyer](https://cvcit.de/wp-content/uploads/2025/03/Flyer.pdf) | Electronic file, document versions, signing, scanner, ID scanner, XNP/UVZ/register/DATEV/Outlook paths and cost register must be modelable as interface and evidence layers. |
| [§ 43 NotAktVV](https://www.gesetze-im-internet.de/notaktvv/__43.html) | Electronic side files need a structured dataset and must be convertible into the required document format. |

## Conclusion

NaC must not treat a matter as a flat folder. The open data model needs at
least these layers:

| Layer | NaC file or pointer | Why |
| --- | --- | --- |
| Matter core | `akten/<year>/<matter_id>/akte.json` | File number, status, use case, workflow binding, participant and document IDs. |
| Contacts and participants | `personen/<person_id>.json`, `beteiligte.json` | People, organizations, roles, representatives and duplicate checks stay separate from the matter. |
| Property/register | `grundbuch.json` or later register files | Register data is its own subject-matter object, not just a PDF attachment. |
| Inbox/mail | `eingang.json` | Scan, email, fax, portal or prompt proposal assignment remains traceable. |
| Documents and versions | `dokumente/<document_id>/metadata.json` plus files | Originals, previews, drafts, versions and metadata remain diffable and exportable. |
| Tasks and deadlines | `aufgaben.json` | Inbox and execution need responsibility, status, next task and deadline logic. |
| Costs | `kosten.json` | Cost keys, cost debtors and billing status belong to the matter. |
| Evidence and compliance | `nachweise.json` | AML, identity, signature, register, side-file export and QMS evidence are checkable objects. |
| Journal | `ereignisse.jsonl`, `journal/` | Every change remains chronologically traceable. |

## CLI As Checkable Core

The web app may make office work convenient. The checkable core remains the
CLI:

```bash
nac tenant write-sample-akte --repo ../demo8notariat --akten-id UVZ-2026-0001
nac tenant list-akten --repo ../demo8notariat
nac tenant show-akte --repo ../demo8notariat --akten-id UVZ-2026-0001
```

This lets a notary or reviewer see without web-app access:

- which matters exist,
- which next step is open,
- which participants, documents, tasks and evidence belong to the matter,
- whether the electronic side file is prepared as an export model.

## Boundary

The current GitHub data repository remains a demo target. Production data needs
a reviewed sovereign/GDPR Git provider or equivalent local Git infrastructure.
The model should stay the same during migration; only remote, permissions,
encryption, retention and operations change.
