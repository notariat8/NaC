# SBOM For AI

## Purpose

`SBOM for AI` is a separate repository-wide governance track for NaC. It
extends classic software SBOMs with AI-specific transparency for models, data,
infrastructure, security controls and performance indicators.

This page is the starting point for the workstream. It applies to all plugins,
workflows, usecases, prompts and external model calls in NaC.

## Source State

Reviewed on 2026-05-15:

- BSI press release on the G7 `SBOM for AI` guidance, 2026-05-12:
  `https://www.bsi.bund.de/DE/Service-Navi/Presse/Pressemitteilungen/Presse2026/260512_G7_Richtlinie_SBOM_for_AI.html`
- BSI AI topic page, `SBOM for AI` section:
  `https://www.bsi.bund.de/EN/Themen/Unternehmen-und-Organisationen/Informationen-und-Empfehlungen/Kuenstliche-Intelligenz/KI.html`
- CISA/G7 resource `Software Bill of Materials for AI - Minimum Elements`:
  `https://www.cisa.gov/resources-tools/resources/software-bill-materials-ai-minimum-elements`

The BSI/G7 line focuses on transparency across the AI supply chain. AI-SBOM
extends classic SBOMs because AI systems include not only software components
but also models, datasets, infrastructure, security and operational properties.

## NoC Minimum Clusters

NaC introduces the following minimum clusters as the working baseline:

| Cluster | NoC content |
| --- | --- |
| `metadata` | Name, version, owner, lifecycle, release binding |
| `system_level_properties` | System boundaries, purpose, autonomy level, human approval |
| `models` | Model name, provider, version, purpose, local/external processing |
| `datasets` | Training, test, validation and prompt data sources as metadata |
| `infrastructure` | Runtime, hosting, tenant, region, local gateways, minimum requirements for workstation, hardware and middleware |
| `security_properties` | Controls against data leakage, prompt injection and supply-chain risk |
| `key_performance_indicators` | Coverage, drift, error rates, review and incident metrics |

NoC additionally tracks privacy/AVV-DPA status, professional-secret boundaries,
human-review ownership, local runtime/hardware minimum requirements and
release/evidence binding.

## Initial Artifacts

- Policy: `policies/sbom-policy.yaml`
- Draft AI-SBOM: `sbom/ai/nac-ai-sbom-draft.json`
- Validator: `scripts/validate_ai_sbom.py`
- Minimum requirements: `docs/en/minimum-requirements.md`
- Classic SBOM products: `docs/en/sbom-products.md`
- AVV/DPA gate: `docs/en/datenschutz-avv-dpa.md`

## Immediate Tasks

| Priority | Task | Outcome |
| --- | --- | --- |
| P0 | Inventory all AI touchpoints in `plugins/`, `workflows/`, `usecases/` and `prompts/`. | List of AI-enabled artifacts. |
| P0 | Update `sbom/ai/nac-ai-sbom-draft.json` for every new AI-enabled artifact. | Repository-wide AI-SBOM baseline. |
| P0 | Track local minimum requirements for runtime, hardware, morris and XNP in the AI-SBOM. | Workstation and middleware dependencies are verifiably inventoried. |
| P0 | Check external AI processing against `docs/en/datenschutz-avv-dpa.md`. | AVV/DPA status per channel. |
| P1 | Decide the mapping to CycloneDX, SPDX or another approved AI-SBOM profile. | Machine-readable target profile. |
| P1 | Extend release binding in `.github/workflows/sbom-export.yml`. | AI-SBOM as release artifact. |
| P2 | Automate model-risk, vulnerability and drift review. | Day2 operation for the AI supply chain. |

## Rules

- Do not store real personal data, mandate content, secrets, private keys or
  certificate material in AI-SBOM artifacts.
- AI-SBOM documents metadata, ownership and boundaries, not confidential
  contents themselves.
- Every AI-enabled release needs an AI-SBOM decision.
- Every local plugin or workflow dependency from
  `docs/en/minimum-requirements.md` needs an SBOM/AI-SBOM entry or a justified
  `pending` marker.
- External AI processing needs a documented AVV/DPA decision before a pilot
  with personal data.
- Local plugin gates remain the default until external processing is approved.

## Definition Of Done

An AI-enabled plugin, workflow or usecase is release-ready only when:

1. the artifact is included in the AI-SBOM baseline,
2. all minimum clusters are populated or explicitly marked as `pending`,
3. runtime, middleware and hardware minimum requirements are documented,
4. privacy/AVV-DPA status is documented,
5. a human-review owner is named,
6. `python scripts/quality_gate.py --profile strict` passes.
