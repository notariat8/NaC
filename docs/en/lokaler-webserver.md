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
