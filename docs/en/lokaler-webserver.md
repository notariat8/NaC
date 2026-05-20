# Local Web Server For Graphical Outputs

Status: BPMN editor and save surface added on 2026-05-19

## Purpose

NaC should not scatter graphical outputs across unrelated files. The local web
server is the shared surface for:

- BPMN process views,
- KG editor views,
- bpmn-js-adjacent BPMN editing,
- later validation reports, diffs and approval views.

The server is local by design. It binds to `127.0.0.1` by default and reads only
files from the current repository.

For readers without access to the running web app, a screenshot-based
explanation is available at [webapp-ohne-zugriff.md](webapp-ohne-zugriff.md).

## Start

```bash
python scripts/nac.py web
```

Then open in the browser:

```text
http://127.0.0.1:8765/
```

Optional:

```bash
python scripts/nac.py web --open
```

The older direct entry point `python scripts/nac_web.py --repo-root .` remains
compatible. Product documentation uses `nac` so every graphical surface follows
the same central operating path.

The local operator bridge started with `python scripts/nac.py operator --open`
also delegates the same BPMN/KG routes on port `8766`, so the operator webapp
can open the models directly.

## Current Routes

| Route | Content |
| --- | --- |
| `/` | Local dashboard with BPMN and KG links. |
| `/bpmn/<model>` | SVG view of a local BPMN model. |
| `/bpmn/<model>/edit` | Local BPMN editor surface with bpmn-js loading path and XML fallback. |
| `/kg/<slug>` | Safe KG editor view without `value` fields. |
| `/api/bpmn/<model>` | JSON structure of the BPMN model. |
| `/api/bpmn/<model>/xml` | BPMN XML plus SHA-256 for conflict-aware saving. |
| `POST /api/bpmn/<model>/xml` | Saves BPMN XML only when `base_sha256` still matches the current repository state. |
| `/api/bpmn-moddle` | NaC moddle descriptor for bpmn-js. |
| `/api/kg/<slug>` | JSON structure of the KG editor view. |
| `/api/operator-config` | Local operator configuration for the NaC fork Git remote and separate data repository folder. |
| `POST /api/operator-config` | Saves local operator configuration without secrets or mandate data in the user configuration. |
| `/api/matters` | Reads matters/cases from the configured data repository including status counts per use case. |
| `POST /api/matters` | Creates a new demo matter in the configured data repository. |
| `POST /api/matters/status` | Writes status changes for an existing demo matter to the data repository and journal. |
| `/api/import-proposals` | Reads import proposals from the data-repository inbox, e.g. from prompt, scan, email or fax extraction. |
| `POST /api/import-proposals` | Creates a synthetic import proposal, including optional staged test files, in the data-repository inbox. |
| `POST /api/import-proposals/accept` | Accepts a reviewed import proposal as a demo matter and copies staged test files into the document area. |
| `/healthz` | Simple health check. |

## Safety Boundaries

- Do not write real mandate data into the public repository.
- Do not show secrets, PINs, tokens or API keys in the web server.
- Default binding remains `127.0.0.1`.
- No automatic merge, no productive system action, no filing from the local view.
- Later changes stay pull-request-based: patch, validation, diff, confirmation
  and review.

## Relationship To bpmn-js

The server renders BPMN locally as an SVG preview and also exposes an editor
surface at `/bpmn/<model>/edit`. The page loads the current BPMN XML from
`/api/bpmn/<model>/xml`, keeps the loaded SHA-256 and saves only if that hash is
still current. Browser edits therefore remain versionable and conflict-aware.

The editor surface can load bpmn-js with the descriptor
[bpmn/nac-moddle.json](../../bpmn/nac-moddle.json); if bpmn-js is not available
in the browser, the XML fallback remains usable. Before merge, validation with
[scripts/validate_bpmn_models.py](../../scripts/validate_bpmn_models.py)
remains mandatory. Git and review decide, not the browser.

## Operator Web App For The Office

In addition to `nac web`, there is `nac operator --open`. This surface is
usecase-first: it starts with case cards, search, matter management, control
views, an office workflow area, workstation tests and a handbook path.

Technically, [scripts/nac_hw_bridge.py](../../scripts/nac_hw_bridge.py) serves
the static surface from [web/local-operator/](../../web/local-operator) and
delegates BPMN/KG routes to [src/nac_web/server.py](../../src/nac_web/server.py).
This lets the office surface and model views run through the same local port
without writing mandate data or credentials into the repository. The footer
menu `Konfig` stores only local workstation values such as the NaC fork Git URL,
data Git URL and data repository folder in the user configuration; it does not
change Git remotes or clone repositories automatically. The use case cards make
`Akten öffnen` the primary daily action, `Neu` the secondary action,
`Checkliste prüfen` the control action and `Kanzlei-Workflow` the collapsed
office-master-data area; demo matter functions write only to the configured
demo data repository and track the statuses `offen`, `warten` and
`abgeschlossen`.

The `Eingang` area connects prompt, scan, email and fax capture with the web
app. Codex or a local importer first writes only an import proposal under
`eingang/import-vorschlaege/`. The office surface shows that proposal with
recognized metadata and files. Only the explicit `Übernehmen` action creates a
demo matter and journal event from it. For real production data, raw document
storage must stay outside public Git repositories; demo mode only permits
synthetic test data.

For demo operation, the surface can select synthetic image files directly in
the browser, prepare a small metadata preview and save the import proposal into
the separate data repository without a page reload. Visible matter and inbox
data are reloaded on focus changes and periodically, so Codex write actions,
uploads and the web app opened on the side show the same state.

The matter view searches matters and pending import proposals together. If no
matter exists yet for a person such as `Mustermann`, but a matching inbox item
does exist, the surface shows that inbox item directly in the matter area and
offers the explicit accept action. Work areas outside the case list also get
`← Zurück` and `Übersicht` navigation, so every UI action has a visible way
back.

Navigation follows the [operator style guide](operator-styleguide.md): case
cards separate `Aktenverwaltung`, `Kontrolle` and `Kanzlei-Workflow`. Matter
management is the visible daily work, checklists are control views, and flow or
editing functions are approval-relevant office master data. When a matter is
created, the operator bridge therefore writes a `workflow_binding` with
workflow version, artifact hashes and binding timestamp into the matter. It
also creates `checkliste.json` per matter as the frozen case state of the
use-case checklist and returns the next open step to the matter overview.

## Planned End-User Packaging

The current developer start through `python scripts/nac.py operator --open` is
not the target state for standard users. The open roadmap item
`Operator-Endnutzer-Launcher paketieren` packages the local operator web app as
an installed `NaC Operator` with its own runtime, Start-menu entry, internal
health check and guided selection of the separate data repository. Users should
not see a shell, Python commands, Curl checks or Codex sandbox approvals.

Implementation is scheduled after the notary start page has been sharpened
further and before broader pilot distribution. The launcher must still bind
only to `127.0.0.1`, write logs into the user environment, manage operator
configuration under `%LOCALAPPDATA%\NaC`, and keep product code, configuration
and demo or mandate data separate.

## Planned ChatGPT And Codex Integration

For later direct work with ChatGPT or Codex, the browser surface itself is not
the source of subject-matter truth. The web app remains the local office
surface; chat integration talks to a small, reviewed tool layer.

The three technical paths must stay separate:

1. A `Custom GPT` with an Action and HTTPS tunnel is only a demo path for
   synthetic data. A tunnel to `localhost` effectively makes a local API
   publicly reachable and is therefore not the product path for real mandate
   data.
2. `nac-mcp` is the target architecture. A local or tenant-capable MCP server
   exposes reviewed tools such as reading cases, creating an import proposal,
   accepting an import proposal, proposing a BPMN change and running the
   quality gate. Codex can use this MCP server locally; ChatGPT Apps SDK can use
   the same tool contract later with UI components.
3. A chat directly inside the operator web app is an optional additional
   operating channel. In that model, a local backend endpoint calls the OpenAI
   API; the API key stays server-side and the local tools remain the same.

For NaC this means: Actions with OpenAPI and a tunnel may enable short demos,
but the regulated target architecture is MCP/App SDK with explicit
authentication, minimal tool permissions, audit logging, human confirmation for
write actions and strict separation between product code and data repository.
