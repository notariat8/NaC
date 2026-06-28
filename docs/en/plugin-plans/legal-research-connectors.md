# Plugin Plan: Legal Research Connectors

Status: `draft`

## Purpose

This document records external legal-research, MCP and publisher-database
references as candidates. It is not a product integration and not an approval
for automated research.

NaC treats every source in this list as a possible connector starting point:
record the source, check terms and licensing, clarify privacy and DPA need,
define the security boundary, decide the AI-SBOM state and only then plan a
technical integration.

## Candidate State

| Candidate | Source | Status | NaC Boundary |
| --- | --- | --- | --- |
| Klotzkette connector reference | [CONNECTORS.md](https://github.com/Klotzkette/claude-fuer-deutsches-recht/blob/main/CONNECTORS.md) | Watchlist | External reference list, no direct adoption. |
| German Law MCP by Ansvar Systems | [LobeHub](https://lobehub.com/mcp/ansvar-systems-german-law-mcp) | Candidate | Metadata review for public legal sources, AI-SBOM open. |
| German Law MCP on ElasticFlow | [ElasticFlow](https://elasticflow.app/hub/pt-BR/mcps/german-law-mcp) | Candidate, duplicate listing | Same technical candidate as Ansvar/LobeHub, evidenced separately. |
| beck-online MCP listing | [MCP Market](https://mcpmarket.com/server/beck-online) | License review needed | No use without terms, license, TDM, security and credential review. |
| Deubner Recht portal | [Deubner Recht & Praxis](https://www.deubner-recht.de/) | License review needed | Publisher-portal candidate only; no automated query, full-text import or credential use without terms, license, DPA, TDM and security review. |
| NVIDIA Nemotron Pretraining Legal v1 | [Hugging Face](https://huggingface.co/datasets/nvidia/Nemotron-Pretraining-Legal-v1) | Source and license review needed | English legal pretraining dataset as a baseline/evaluation candidate; not a German legal source, no training start and no checkpoint publication without owner apply, AI-SBOM, license and model-card review. |
| recht.bund.de data access | [Bundesgesetzblatt data access](https://www.recht.bund.de/de/service/webservice/webservice_node.html) | Official source review | Systematic BGBl access through ELI, PDF, ZIP and RSS as a later ingestion candidate; no bulk crawl, PDF fine-tuning or normalization without terms, license and review plan. |
| Rechtsquelle concept | [Wikipedia Rechtsquelle](https://de.wikipedia.org/wiki/Rechtsquelle) | Concept anchor | Only for separating legal source, source-of-law evidence, hierarchy and collision rules; not a primary source and not a training corpus. |

All URLs are kept without tracking parameters. The machine-readable boundary is
defined in the
[Legal Research Connector contract](../../../workflows/contracts/legal-research-connectors.contract.json).

## Approval Boundaries

- No secrets, credentials, session cookies or private keys in the repository.
- No real mandate data, personal data or full document text to external AI or
  MCP services without privacy review.
- No automated queries against protected publisher databases without contract,
  license basis, terms review and technical security evidence.
- No legal truth from AI answers; binding review remains human subject-matter
  review and versioned NaC approval.
- No portal scraping or TDM assumption without explicit legal and provider
  review.
- No fine-tuning, checkpoint publication or use as a legal-answer system
  without separate source, license, evaluation, model-card, AI-SBOM and owner
  apply evidence.

## From Candidate To Connector

A candidate becomes a connector plan only after these steps are complete:

1. Document source, provider, license state and data class.
2. Assess privacy, DPA, TIA need and mandate-data prohibition.
3. Decide AI-SBOM status for AI, API or MCP candidates.
4. Describe the security boundary and credential storage outside Git.
5. Design dry-run or metadata-only mode.
6. Define human review and four-eyes requirements.
7. Only then plan a plugin, MCP or web-app operating edge.

## Web-App View

A future authenticated NaC web app may show this backlog as a status and review
view: candidate, source, license state, review state, blockers and next check.
It must not turn the backlog into a hidden product integration and must not
display secret credentials or third-party full text.

## Validation

The backlog is validated through the central NaC CLI:

```bash
nac contracts validate
```

The validator blocks tracking URLs, credentials in the repository, productive
integration levels, missing license/DPA/review gates and missing evidence
fields.
