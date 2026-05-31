# Data Protection AVV DPA

## Purpose

This section defines when NaC needs a German AVV or Data Processing Addendum
(DPA) for OpenAI-backed functions and which evidence must exist before pilot or
production use.

Note: This is an operational governance guide and does not replace legal
advice.

## Source State

DPA/AVV baseline reviewed on 2026-05-15, OpenAI Enterprise and EU data
residency addition reviewed on 2026-05-22:

- OpenAI Data Processing Addendum v.010126:
  `https://cdn.openai.com/pdf/openai-data-processing-addendum.pdf`
- Official OpenAI data-processing-addendum page with PDF download and the link
  to execute the Data Processing Agreement:
  `https://openai.com/de-DE/policies/data-processing-addendum/`
- Gesellschaft fuer Datenschutz, "ChatGPT, Datenschutz und
  Auftragsverarbeitungsvertrag":
  `https://gesellschaft-datenschutz.de/chatgpt-und-auftragsverarbeitung/`
- NaC procurement and approval path for ChatGPT Enterprise, API EU data
  residency and Codex:
  [docs/en/openai-enterprise-eu-residency.md](openai-enterprise-eu-residency.md)

The OpenAI DPA describes OpenAI as processor for the covered service scope and
covers instructions, subprocessors, return/deletion, international transfers
and customer-controlled configuration choices. The German article emphasizes
that the privacy role depends on the license model and that business/API use
requires an AVV/DPA assessment.

Operational note: The contract is not executed through the PDF reference stored
in this repository. It must be initiated through the official OpenAI policy
path. The page's final "execute data processing agreement" step is the
agreement/AVV path to review. Resulting documents, organization IDs and account
data are not stored in this repository.

## NaC Principle

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

| Channel | AVV/DPA rule | NaC approval |
| --- | --- | --- |
| Free or Pro | Do not use for personal NaC/notary-office data. | Not approved. |
| Team or Business | Only for documentation, code, synthetic demos and non-sensitive planning; not evidence for EU data residency or notarial processing. | Not approved for real NaC/notary-office data. |
| Enterprise or API Europe | Review DPA/AVV, EU data residency, purpose limitation, retention, subprocessors/TIA, ZDR/MAM and tool boundaries. | Only after documented approval. |
| Public GPT Store | Check privacy URL, terms, Action boundary and DPA need per Action. | Separate release approval. |
| Workspace GPT/App | Review tenant, roles, retention, training/data sharing and DPA. | Pilot approval required. |
| Local plugin | No external AI transfer if fully local. | Default path for sensitive gates. |

## Required Artifacts Before Processing

- signed or effectively accepted DPA/AVV version
- evidence that execution was initiated or completed through the official
  OpenAI DPA/AVV path
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

## NaC PR Gate

A PR that enables OpenAI-backed processing of personal data is merge-ready only
when:

1. `policies/data-protection-policy.yaml` is satisfied.
2. The target channel is classified in
   `docs/en/gpt-marketplace-operating-model.md`.
3. This AVV/DPA section is linked as checklist reference.
4. No real contract document, organization ID or account secret is in the diff.
5. An issue or PR comment documents the approval decision.
6. `python scripts/nac.py doctor --profile strict` passes.

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

## Law-Firm AI / Legal-Tech SaaS Review

Justin Legal is recorded as a substantive review candidate for law-firm AI,
mandate intake and matter creation. Its privacy text describes personal-data
processing for the product and website, digital mandate initiation and
handling, processing under Article 28 GDPR on behalf of the relevant lawyer,
the lawyer or law firm as controller, deletion on law-firm instruction or
after the usage relationship ends, and external technical services such as
authentication, payment processing, CRM, ticketing, analytics, cookie consent
and hosting.

NaC does not treat this as compliance approval. GDPR- and BRAO-compatible use
would need to be clarified separately before any pilot:

- written DPA/AVV with clear role allocation between law firm, provider and
  subprocessors
- categories of mandate, communication, matter and usage data
- hosting, storage, deletion, export and return process
- complete subprocessor list including third-country transfers, SCC/TIA and
  support access
- separation between website tracking/marketing and confidential mandate
  processing
- encryption, access-control, logging and role model for law-firm users
- no real mandate data in test, demo, analytics or training paths without
  explicit approval
- BRAO review for professional secrecy, service-provider use, necessity of
  access, provider confidentiality commitment, foreign-service context and
  comparable protection of secrets

Until these points are evidenced, such a provider remains comparison and
review material in NaC. It is not an approved product integration and not
evidence of GDPR or BRAO compliance.

## Relationship To Existing NaC Documents

- `docs/en/security-and-dsgvo.md`: general repository protection rules.
- `docs/en/avv-checkliste-eventlock-saas.md`: Function8/EventLock-specific
  AVV checklist.
- `docs/en/gpt-marketplace-operating-model.md`: channel decision for GPT Store,
  Actions, workspace apps and local plugins.
- `docs/en/openai-enterprise-eu-residency.md`: procurement, price orientation,
  EU data residency and Codex cost path.
- `policies/data-protection-policy.yaml`: binding privacy and secret rules.
