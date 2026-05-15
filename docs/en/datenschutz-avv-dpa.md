# Data Protection AVV DPA

## Purpose

This section defines when NoC needs a German AVV or Data Processing Addendum
(DPA) for OpenAI-backed functions and which evidence must exist before pilot or
production use.

Note: This is an operational governance guide and does not replace legal
advice.

## Source State

Reviewed on 2026-05-15:

- OpenAI Data Processing Addendum v.010126:
  `https://cdn.openai.com/pdf/openai-data-processing-addendum.pdf`
- Gesellschaft fuer Datenschutz, "ChatGPT, Datenschutz und
  Auftragsverarbeitungsvertrag":
  `https://gesellschaft-datenschutz.de/chatgpt-und-auftragsverarbeitung/`

The OpenAI DPA describes OpenAI as processor for the covered service scope and
covers instructions, subprocessors, return/deletion, international transfers
and customer-controlled configuration choices. The German article emphasizes
that the privacy role depends on the license model and that business/API use
requires an AVV/DPA assessment.

## NoC Principle

- Local plugins and local workflows are the default path until AVV/DPA approval
  is documented.
- Personal data, deed data, register content, professional secrets, card
  values, PINs, private keys and mandate content must not be sent to external AI
  services without an approved processing path.
- Data minimization still applies when a DPA exists: IDs, placeholders, reduced
  facts and synthetic test data remain preferred.
- Contract documents, account IDs, organization data, audit reports and real
  customer data are not stored in Git. The repo stores only metadata,
  checklists, hashes or references to the approved document-management system.

## License And Channel Decision

| Channel | AVV/DPA rule | NoC approval |
| --- | --- | --- |
| Free or Pro | Do not use for personal NoC/notary-office data. | Not approved. |
| Team, Enterprise or API | Review DPA/AVV, configuration and purpose limitation. | Only after documented approval. |
| Public GPT Store | Check privacy URL, terms, Action boundary and DPA need per Action. | Separate release approval. |
| Workspace GPT/App | Review tenant, roles, retention, training/data sharing and DPA. | Pilot approval required. |
| Local plugin | No external AI transfer if fully local. | Default path for sensitive gates. |

## Required Artifacts Before Processing

- signed or effectively accepted DPA/AVV version
- exact OpenAI product/license mapping
- processing purpose and documented customer instruction
- categories of personal data and data subjects
- decision whether special categories or professional secrets are excluded or
  separately approved
- configuration for data use, retention, deletion and access
- subprocessor state with review date
- international-transfer/SCC/transfer-impact assessment where required
- incident, data-subject-rights, return and deletion process
- review by privacy owner, business owner and technical owner

## NoC PR Gate

A PR that enables OpenAI-backed processing of personal data is merge-ready only
when:

1. `policies/data-protection-policy.yaml` is satisfied.
2. The target channel is classified in
   `docs/en/gpt-marketplace-operating-model.md`.
3. This AVV/DPA section is linked as checklist reference.
4. No real contract document, organization ID or account secret is in the diff.
5. An issue or PR comment documents the approval decision.
6. `python scripts/quality_gate.py --profile strict` passes.

## Minimum Decision Per Plugin Or Workflow

Each plugin, Action and workflow needs a short decision before a pilot with
personal data:

| Question | Decision |
| --- | --- |
| Is personal data processed externally? | Yes/No |
| Is OpenAI only processor for this channel? | Yes/No/Unclear |
| Is effective DPA/AVV approval in place? | Yes/No |
| Are professional secrets or special categories excluded? | Yes/No |
| Which minimization measure applies? | IDs/placeholders/synthetic/redaction |
| Where is the external contract evidence stored? | Reference only, no document in repo |

## Relationship To Existing NoC Documents

- `docs/en/security-and-dsgvo.md`: general repository protection rules.
- `docs/en/avv-checkliste-eventlock-saas.md`: Function8/EventLock-specific
  AVV checklist.
- `docs/en/gpt-marketplace-operating-model.md`: channel decision for GPT Store,
  Actions, workspace apps and local plugins.
- `policies/data-protection-policy.yaml`: binding privacy and secret rules.
