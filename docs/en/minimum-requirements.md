# Minimum Requirements

Status: binding day-0 baseline
Last content update: 2026-05-15

## Purpose

This chapter defines the minimum requirements for local development, plugin
tests and the later notary workstation. The list is part of SBOM maintenance:
runtime, local middleware, hardware and optional domain systems are treated as
supply-chain components even when they are not committed as repository files.

## Profiles

| Profile | Purpose | Binding level |
| --- | --- | --- |
| `base` | Read the repository, check policies, run Python tests | Mandatory for every productive change |
| `plugin-dev` | Develop plugins, local Actions, packaging and app-adjacent artifacts | Mandatory for plugin and integration work |
| `notary-workstation` | Check XNP, card reader, morris and notary workstation paths | Mandatory before local domain-system tests |

## Base Workspace

The base workspace is the minimum environment for repository work:

| Component | Minimum state | Purpose |
| --- | --- | --- |
| Operating system | Windows 11 or another current maintained developer OS | Local development and GitOps work |
| Git | installed and available in `PATH` | versioning, branches, pull requests |
| GitHub CLI `gh` | installed and authenticated | PR, Actions and repository operations |
| Python | `>= 3.11` | deterministic checks, KG runtime, workflow runtime |
| VS Code or Cursor | recommended | IDE-supported contribution |
| VS Code Copilot extensions | required for the VS Code path | agent and Copilot synchronization |
| `pandoc` | recommended | later document export |

Mandatory check:

```bash
python scripts/startup_check.py --profile base --ide auto --run-tests
```

## Plugin Development Workspace

Plugin and integration development adds the following to the base workspace:

| Component | Minimum state | Purpose |
| --- | --- | --- |
| Node.js | `>= 20` recommended | packaging, local web/action prototypes, validators |
| npm | matching Node.js | package installation and build commands |
| Local loopback access | `127.0.0.1` reachable | local gateways such as morris and XNP test adapters |
| Browser | current Chromium/Edge/Chrome or Firefox | local middleware and admin surfaces |

Mandatory plugin-work check:

```bash
python scripts/nac.py plugins validate
python scripts/nac.py plugins install --mode link
python scripts/startup_check.py --profile plugin-dev --ide auto
```

Then restart Codex or open a new session with workspace `~/NaC`, because active
plugins are loaded at session start. If a workstation does not allow symlinks,
use `--mode copy --force` after approval.

## Notary Workstation For Card And XNP Paths

The notary workstation is a local Windows environment. It is not replaced by
cloud execution or Omnistation while local card, signature or XNP components are
required.

| Component | Minimum state | Purpose |
| --- | --- | --- |
| Operating system | Windows 11 or current supported Windows client | driver, card and XNP compatibility |
| User context | same Windows user for Codex, morris, driver and XNP | consistent local permissions and runtime paths |
| Local admin rights | available for installation/maintenance | driver, morris, XNP, PC/SC |
| Card reader | REINER SCT cyberJack or equivalent security-class-3 reader | BNotK card path and secure PIN entry |
| BNotK chip/signature card | available for domain tests | authentication and signature paths |
| PC/SC service | installed and running | smart-card access for local software |
| REINER SCT DriverPackage | installed, typical path `C:\Program Files\REINER SCT\DriverPackage` | card-reader driver |
| REINER SCT morris | installed, typical path `C:\Program Files (x86)\REINER SCT\morris` | local browser/middleware gateway |
| morris loopback | local response on `127.0.0.1`, default probe `8800` | plugin can test middleware reachability |
| XNP | locally installed | BNotK/register communication |
| SAK lite or XNP card path | installed/configured | card-based XNP access |
| secureFramework | installed/configured if required by the card path | local security component |
| XNotar/exchange path | present when register cases are tested | HRA/HRB and exchange packages |
| AusweisApp | optional for IDaaS/eID paths | eID function check |

A morris test is successful when the middleware responds. Without an attached
or inserted card, a response such as `no card reader attached`, `NoReader` or
`NaCard` is sufficient for the technical binding check. When real hardware,
card, morris and XNP are installed locally, real local hardware-readiness tests
are expected.

Notary-workstation check:

```bash
python scripts/startup_check.py --profile notary-workstation --ide auto
python scripts/nac.py plugins card-readiness --manual-card-present yes --manual-rfid-off yes --probe-morris-api --json
python scripts/nac.py plugins xnp-reader-prompt --manual-card-present yes --manual-rfid-off yes --probe-morris-api --json
```

## Privacy And Operating Boundaries

- Do not store PINs, card serial numbers, certificate contents, mandate data or
  real personal data in the repository.
- Card and XNP tests may check local hardware, middleware and XNP reachability
  when real hardware is installed. PIN capture, raw card data, secrets, mandate
  data, signing and productive actions remain blocked.
- External processing with personal data requires documented AVV/DPA status
  before a pilot.
- Local domain systems remain local dependencies and must appear in the SBOM
  and AI-SBOM as infrastructure/runtime components.

## SBOM Requirement

Every component in this chapter must be represented in one of the following
artifacts or explicitly tracked as `pending`:

- `policies/sbom-policy.yaml`
- `sbom/ai/nac-ai-sbom-draft.json`
- later CycloneDX/SPDX exports under `out/sbom/`

For every new plugin, workflow or usecase dependency:

1. document the minimum requirement,
2. add the SBOM/AI-SBOM entry,
3. provide a local check or manual verification note,
4. update `roadmap/GANTT.md`.
