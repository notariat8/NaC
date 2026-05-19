# Local Web Server For Graphical Outputs

Status: first local web server implemented on 2026-05-19

## Purpose

NaC should not scatter graphical outputs across unrelated files. The local web
server is the shared surface for:

- BPMN process views,
- KG editor views,
- later bpmn-js editing,
- later validation reports, diffs and approval views.

The server is local by design. It binds to `127.0.0.1` by default and reads only
files from the current repository.

## Start

```bash
python scripts/nac_web.py --repo-root . --host 127.0.0.1 --port 8765
```

Then open in the browser:

```text
http://127.0.0.1:8765/
```

Optional:

```bash
python scripts/nac_web.py --repo-root . --open
```

## Current Routes

| Route | Content |
| --- | --- |
| `/` | Local dashboard with BPMN and KG links. |
| `/bpmn/<model>` | SVG view of a local BPMN model. |
| `/kg/<slug>` | Safe KG editor view without `value` fields. |
| `/api/bpmn/<model>` | JSON structure of the BPMN model. |
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

The current server already renders BPMN locally as an SVG preview. The next step
is to embed a bpmn-js editor into this local surface:

1. restricted palette,
2. NaC properties panel from [bpmn/nac-moddle.json](../../bpmn/nac-moddle.json),
3. save as BPMN XML,
4. validate with [scripts/validate_bpmn_models.py](../../scripts/validate_bpmn_models.py),
5. pull request instead of direct change.

This makes bpmn-js the operating surface while Python and Git remain the
checkable governance layer.
