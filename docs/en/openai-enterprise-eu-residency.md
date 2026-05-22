# OpenAI Enterprise, EU Data Residency And Codex Costs

## Purpose

This document records the procurement and approval path for ChatGPT Enterprise,
OpenAI API with EU data residency, and Codex use in the NaC context. It is an
operational governance note and does not replace legal advice, privacy review,
or a binding OpenAI quote.

NaC principle: Real notarial cases, personal data, professional secrets, deed
data and document content may only be processed after documented approval for
DPA/AVV, data residency, roles, retention and tool boundaries.

## Source State

Reviewed on 2026-05-22:

- [OpenAI ChatGPT Pricing](https://openai.com/business/chatgpt-pricing/)
- [OpenAI Help: How can I contact sales?](https://help.openai.com/en/articles/9047878-how-can-i-contact-sales)
- [OpenAI API data controls](https://developers.openai.com/api/docs/guides/your-data)
- [OpenAI Help: Data residency and inference residency for ChatGPT](https://help.openai.com/en/articles/9903489-eu-data-residency)
- [OpenAI Help: Codex rate card](https://help.openai.com/en/articles/20001106-codex-rate-card)

Prices, regions, model coverage and additional terms must be checked again on
the official OpenAI pages and in the concrete order form before signing.

## Short Decision

| Question | NaC answer |
| --- | --- |
| Is a Team or Business subscription sufficient for real NaC/notary-office data? | No. Business can be useful for demos, documentation, code and synthetic data, but by itself it is not sufficient evidence for EU data residency and notarial processing. |
| Can `eu.api.openai.com` be used under a Team/Business subscription? | Not as a subscription assumption. API data residency needs an eligible API organization, per-project region configuration, the regional domain prefix and additional approvals such as Modified Abuse Monitoring or Zero Data Retention. |
| How do we get Enterprise? | Through the OpenAI sales contact form with work email, company, country/region, seat estimate, timeline, billing needs and compliance requirements. |
| What do Enterprise and Codex cost? | Enterprise is custom pricing. Business ChatGPT & Codex has a public list price. The Codex rate card describes average Codex cost at about USD 100 to 200 per developer per month, varying by model, instances, automations and fast mode. |
| What is the safe target path for NaC? | Enterprise or API contract with DPA/AVV, EU data residency in the order form or project, clarified retention, subprocessor/TIA review, tool boundaries and NaC review gate. |

## Procurement Path

1. Prepare requirements:
   seat count, target users, notarial/mandate-data exclusions, EU region,
   inference-residency request, API spend, Codex use, billing/PO needs and
   DPA/AVV requirements.
2. Contact OpenAI Sales:
   the official sales contact form is the public entry path for ChatGPT
   Enterprise and API Enterprise needs.
3. Clarify contract terms:
   Enterprise or API contract, DPA/AVV, EU data residency, inference
   residency, retention, Zero Data Retention or Modified Abuse Monitoring,
   subprocessors, support/SLA, billing channel and Codex cost model.
4. Configure technically:
   for API use, create a separate project with region Europe (EEA +
   Switzerland), use the correct regional API domain and restrict project and
   organization permissions.
5. Approve in NaC:
   the approval is documented as an issue, PR comment or external evidence
   reference. Contract documents, account IDs, API keys and real mandate data
   are not stored in the product repository.

## EU Data Residency And API

For API use, EU processing is not only a client-side setting. The NaC path
requires at least:

- eligible OpenAI API organization with data-residency capability
- per-project region configuration for Europe (EEA + Switzerland)
- use of `https://eu.api.openai.com` for matching API requests
- approval for Modified Abuse Monitoring or Zero Data Retention where required
  for non-US regions
- review of supported endpoints, models, tools and limitations
- no real mandate data in remote MCP, Web Search or third-party tools without
  separate approval

System data, metadata, billing, support data and third-party paths may be
outside the selected region. This boundary must be expressly considered in the
privacy review.

## ChatGPT Enterprise

ChatGPT Enterprise is the target channel when real authenticated users,
workspace controls, SSO/SCIM, role-based administration, custom legal terms,
support/SLA, data residency or stricter privacy terms are required. For NaC,
Enterprise is not a blanket permission: concrete workspace configuration,
Apps, MCP connectors, Web Search, retention, approvals and logging remain
subject to approval.

For ChatGPT data residency:

- The workspace must be provisioned with data residency in the requested
  region.
- Inference residency is available only to eligible Enterprise/Edu customers
  and supported regions.
- Not all data is in the residency scope; account, billing, login, usage and
  other system data must be assessed separately.
- External integrations such as Apps, MCP and Web Search have their own data
  paths and must not be treated as EU-resident by default.

## Codex Workspace And Costs

In NaC terms, a Codex workspace is not a replacement for the local notary
workstation profile. It is a development and automation environment with admin,
security, worktree and agent capabilities that can work on code, documentation,
tests and synthetic demos.

For real notarial processing:

- Codex must not store real deed data, secrets, API keys, card values, PINs,
  private keys or mandate documents in the product repo.
- Local card-reader, XNP, eID and morris paths remain checked through the local
  `notary-workstation` profile.
- Hosted Codex or API functions use the same DPA/AVV, data-residency,
  retention and tool gates as other external AI processing.
- The Codex cost model must be checked in the contract or rate card against the
  planned usage case; averages do not replace budget approval.

## Minimum Approval For NaC Pilots

Before processing real personal or notarial data, at least the following must
exist:

- effectively accepted DPA/AVV or equivalent contractual basis
- order form or admin evidence for EU data residency, where used
- documented decision on inference residency or residual risk
- OpenAI product/license mapping: Business, Enterprise, API or Codex
- project/workspace configuration for retention, training/data sharing, roles,
  SSO/MFA and access paths
- decision on Modified Abuse Monitoring or Zero Data Retention
- subprocessor, transfer, TIA and SCC review where required
- tool boundary for Apps, MCP, Web Search, file uploads and connectors
- NaC review by privacy owner, business owner and technical owner
- reference to [docs/en/datenschutz-avv-dpa.md](datenschutz-avv-dpa.md)

## Decision Matrix

| Channel | Suitable for | Not suitable for | NaC status |
| --- | --- | --- | --- |
| ChatGPT Business or earlier Team tier | documentation, code, synthetic demos, non-sensitive planning | real mandate data without additional DPA/AVV, residency and tool approval | limited only |
| ChatGPT Enterprise | authenticated users, SSO, admin controls, contractual Enterprise boundaries | blanket processing without concrete workspace and tool review | target path for ChatGPT UI |
| OpenAI API Europe | server-side NaC functions with regional project and `eu.api.openai.com` | use without eligible API organization, ZDR/MAM decision and endpoint review | target path for API integration |
| Codex | development, reviews, tests, synthetic cases, repository automation | storing real mandate data or secrets in repo/workspace | development and operations path |
| Local NaC workstation | XNP, eID, card reader, morris, local gates | external AI processing without approval | default path for sensitive gates |
