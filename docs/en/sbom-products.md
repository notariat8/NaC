# SBOM Products And License Model

## Ziel

This page defines which products are used for SBOM work and which of them are
open source or subscription-based.

## Short Answer

- `Python`: open source, no subscription required.
- `GitHub license`: free and paid tiers exist; plain SBOM generation does not
  require an additional subscription.

## Binding SBOM Stack In This Repository

| Area | Product | Standard/format | Open source | Subscription required |
| --- | --- | --- | --- | --- |
| Python component SBOM | `cyclonedx-python` | CycloneDX JSON | Yes | No |
| Filesystem/artifact SBOM | `syft` | SPDX JSON | Yes | No |
| CI execution | GitHub Actions | Artifact export | No (platform service) | No (basic use) |
| Extended security analysis | GitHub Advanced Security | Security features | No | Yes (optional) |

## SBOM For AI

Classic SBOMs are not enough for AI systems. NaC therefore introduces an
additional `SBOM for AI` track in `docs/en/sbom-for-ai.md` and
`policies/sbom-policy.yaml`.

Initial artifacts:

- `sbom/ai/nac-ai-sbom-draft.json`
- `scripts/validate_ai_sbom.py`

This track applies repository-wide to AI-enabled plugins, workflows, usecases,
prompts and external model calls.

Local minimum requirements such as Python, Node.js/npm, GitHub CLI, morris,
REINER SCT drivers, card reader, PC/SC and XNP are also SBOM-relevant
runtime/infrastructure components. The binding list is maintained in
`docs/en/minimum-requirements.md` and mirrored in
`sbom/ai/nac-ai-sbom-draft.json`.

## Recommendation For This Repository

1. Generate at least two SBOM artifacts:
   - CycloneDX JSON (Python view)
   - SPDX JSON (overall filesystem view)
2. Store artifacts as CI artifacts under `out/sbom/`.
3. Bind release tags to the matching SBOM artifacts.
4. Track local workstation, hardware and middleware dependencies in the
   AI-SBOM until they are fully exported through CycloneDX/SPDX.

## Mandatory vs. Optional

- Mandatory:
  - SBOM generation in open standard formats
  - versioned storage per release
- Optional:
  - GitHub Advanced Security
  - additional proprietary compliance products

## Notes For Companies

- Teams that want to start with an open-source-only stack can do so.
- Teams that later need additional security features can optionally activate
  paid GitHub features without changing the core SBOM process.
