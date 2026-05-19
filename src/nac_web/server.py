from __future__ import annotations

import html
import json
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from nac_web.bpmn import bpmn_model_json, find_bpmn_model, list_bpmn_models, render_bpmn_svg
from notary_kg.catalog import all_case_summaries, load_catalogs
from notary_kg.editor import build_editor_view


class NaCLocalWebApp:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()

    def handle(self, path: str) -> tuple[int, str, bytes]:
        parsed = urlparse(path)
        route = unquote(parsed.path)
        try:
            if route == "/" or route == "":
                return _html_response(build_home_page(self.repo_root))
            if route == "/healthz":
                return _json_response({"status": "ok"})
            if route.startswith("/bpmn/"):
                return self._bpmn_route(route.removeprefix("/bpmn/"))
            if route.startswith("/kg/"):
                return self._kg_route(route.removeprefix("/kg/"))
            if route.startswith("/api/bpmn/"):
                return self._bpmn_api_route(route.removeprefix("/api/bpmn/"))
            if route.startswith("/api/kg/"):
                return self._kg_api_route(route.removeprefix("/api/kg/"))
        except KeyError as exc:
            return _html_response(_layout("Nicht Gefunden", f"<p>{html.escape(str(exc))}</p>"), HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            return _html_response(_layout("Ungültiges Modell", f"<p>{html.escape(str(exc))}</p>"), HTTPStatus.BAD_REQUEST)
        return _html_response(_layout("Nicht Gefunden", "<p>Diese lokale NaC-Seite gibt es nicht.</p>"), HTTPStatus.NOT_FOUND)

    def _bpmn_route(self, stem: str) -> tuple[int, str, bytes]:
        model = find_bpmn_model(self.repo_root, _safe_segment(stem))
        return _html_response(build_bpmn_page(model))

    def _kg_route(self, slug: str) -> tuple[int, str, bytes]:
        view = build_editor_view(self.repo_root, _safe_segment(slug))
        return _html_response(build_kg_page(view))

    def _bpmn_api_route(self, stem: str) -> tuple[int, str, bytes]:
        model = find_bpmn_model(self.repo_root, _safe_segment(stem))
        return _json_text_response(bpmn_model_json(model))

    def _kg_api_route(self, slug: str) -> tuple[int, str, bytes]:
        view = build_editor_view(self.repo_root, _safe_segment(slug))
        return _json_response(view)


def run_server(repo_root: Path, host: str, port: int, open_browser: bool = False) -> None:
    app = NaCLocalWebApp(repo_root)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            status, content_type, body = app.handle(self.path)
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            print(f"{self.address_string()} - {format % args}")

    server = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{server.server_port}/"
    print(f"NaC local web server: {url}")
    print("Abbrechen mit Ctrl+C.")
    if open_browser:
        threading.Timer(0.2, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nNaC local web server beendet.")
    finally:
        server.server_close()


def build_home_page(repo_root: Path) -> str:
    bpmn_models = list_bpmn_models(repo_root)
    catalogs = load_catalogs(repo_root)
    cases = all_case_summaries(catalogs)
    bpmn_items = "".join(
        f'<li><a href="/bpmn/{html.escape(model.stem)}">{html.escape(model.name)}</a>'
        f'<span>{html.escape(model.path)}</span></li>'
        for model in bpmn_models
    )
    kg_items = "".join(
        f'<li><a href="/kg/{html.escape(case.slug)}">{html.escape(case.title)}</a>'
        f'<span>{html.escape(case.slug)} · {case.open_required_information} offene Angaben</span></li>'
        for case in cases[:40]
    )
    body = f"""
    <section class="hero">
      <p class="eyebrow">Lokaler NaC-Webserver</p>
      <h1>Grafische Ausgaben lokal prüfen</h1>
      <p>BPMN-Modelle und KG-Editor-Views werden direkt aus dem Repository gelesen.
      Der Server bindet standardmäßig an <code>127.0.0.1</code> und speichert keine Mandatsdaten.</p>
    </section>
    <div class="grid">
      <section>
        <h2>BPMN</h2>
        <ul class="link-list">{bpmn_items}</ul>
      </section>
      <section>
        <h2>Knowledge Graphs</h2>
        <ul class="link-list">{kg_items}</ul>
      </section>
    </div>
    """
    return _layout("NaC Lokaler Webserver", body)


def build_bpmn_page(model) -> str:
    node_rows = "".join(
        "<tr>"
        f"<td>{html.escape(node.name)}</td>"
        f"<td>{html.escape(node.type)}</td>"
        f"<td>{html.escape(node.nac.get('role', ''))}</td>"
        f"<td>{html.escape(node.nac.get('dataClass', ''))}</td>"
        f"<td>{html.escape(node.nac.get('approval', ''))}</td>"
        f"<td>{html.escape(node.nac.get('evidence', ''))}</td>"
        "</tr>"
        for node in model.nodes
    )
    body = f"""
    <nav class="topline"><a href="/">← Übersicht</a><a href="/api/bpmn/{html.escape(model.stem)}">JSON</a></nav>
    <section class="hero">
      <p class="eyebrow">BPMN-Modell</p>
      <h1>{html.escape(model.name)}</h1>
      <p>{html.escape(model.path)} · {"bpmn-js-Diagrammfläche vorhanden" if model.has_diagram else "Fallback-Layout"}</p>
    </section>
    <section class="canvas">{render_bpmn_svg(model)}</section>
    <section>
      <h2>NaC-Schritte</h2>
      <table>
        <thead><tr><th>Name</th><th>Typ</th><th>Rolle</th><th>Datenklasse</th><th>Freigabe</th><th>Nachweis</th></tr></thead>
        <tbody>{node_rows}</tbody>
      </table>
    </section>
    """
    return _layout(f"BPMN: {model.name}", body)


def build_kg_page(view: dict[str, Any]) -> str:
    tabs = "".join(_render_kg_tab(tab) for tab in view["editor_model"]["tabs"])
    body = f"""
    <nav class="topline"><a href="/">← Übersicht</a><a href="/api/kg/{html.escape(view['usecase_slug'])}">JSON</a></nav>
    <section class="hero">
      <p class="eyebrow">KG-Editor-View</p>
      <h1>{html.escape(view['title'])}</h1>
      <p>{html.escape(view['usecase_slug'])} · {html.escape(view['status'])}</p>
    </section>
    <section class="notice">
      <strong>Schutzregel:</strong> Diese Ansicht zeigt keine <code>value</code>-Felder.
      Änderungen laufen später über Patch, Validierung, Diff und Pull Request.
    </section>
    {tabs}
    """
    return _layout(f"KG: {view['title']}", body)


def _render_kg_tab(tab: dict[str, Any]) -> str:
    if "groups" in tab:
        content = "".join(_render_kg_items(group["label_de"], group.get("items", [])) for group in tab["groups"])
    else:
        content = _render_kg_items(tab["label_de"], tab.get("items", []))
    return f"<section><h2>{html.escape(tab['label_de'])}</h2>{content}</section>"


def _render_kg_items(label: str, items: list[dict[str, Any]]) -> str:
    if not items:
        return f"<p>{html.escape(label)}: keine Einträge.</p>"
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('label', item.get('id', ''))))}</td>"
        f"<td>{html.escape(str(item.get('status', '')))}</td>"
        f"<td>{html.escape(str(item.get('owner_role', item.get('source', ''))))}</td>"
        "</tr>"
        for item in items
    )
    return (
        "<table>"
        "<thead><tr><th>Eintrag</th><th>Status</th><th>Rolle/Quelle</th></tr></thead>"
        f"<tbody>{rows}</tbody>"
        "</table>"
    )


def _layout(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>{_css()}</style>
</head>
<body>
  <main>{body}</main>
</body>
</html>
"""


def _css() -> str:
    return """
    :root { color-scheme: light; --ink: #1f2328; --muted: #636c76; --line: #d8dee4; --bg: #f6f8fa; --panel: #fff; --accent: #2f6f88; }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: var(--ink); background: var(--bg); }
    main { max-width: 1180px; margin: 0 auto; padding: 28px; }
    h1 { margin: 0 0 12px; font-size: 36px; line-height: 1.1; letter-spacing: 0; }
    h2 { margin: 0 0 16px; font-size: 22px; letter-spacing: 0; }
    p { color: var(--muted); line-height: 1.55; }
    code { background: #eef2f5; border-radius: 4px; padding: 2px 5px; }
    .hero, section { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 22px; margin: 0 0 20px; }
    .eyebrow { margin: 0 0 8px; color: var(--accent); font-weight: 700; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }
    .link-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
    .link-list li { border: 1px solid var(--line); border-radius: 8px; padding: 12px; background: #fff; }
    .link-list a { display: block; color: #0b4f6c; font-weight: 700; text-decoration: none; margin-bottom: 4px; }
    .link-list span { color: var(--muted); font-size: 14px; }
    .topline { display: flex; justify-content: space-between; gap: 16px; margin: 0 0 18px; }
    .topline a { color: #0b4f6c; font-weight: 700; text-decoration: none; }
    .canvas { overflow: auto; padding: 8px; background: #fbfcfd; }
    .bpmn-svg { width: 100%; min-width: 840px; height: auto; display: block; }
    .flow { fill: none; stroke: #41516b; stroke-width: 2.2; }
    .flow-label { font-size: 13px; fill: #41516b; text-anchor: middle; font-weight: 700; }
    .node rect, .node circle, .node polygon { fill: #fff; stroke: #2f6f88; stroke-width: 2.2; }
    .node.serviceTask rect { fill: #edf7f4; stroke: #2f6b50; }
    .gateway polygon { fill: #fff8e8; stroke: #936e1d; }
    .end circle { stroke: #7b2d26; }
    .node-label { text-anchor: middle; dominant-baseline: middle; font-size: 14px; font-weight: 700; fill: var(--ink); }
    .node-badge { text-anchor: middle; font-size: 12px; fill: var(--muted); }
    table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
    th, td { text-align: left; border-bottom: 1px solid var(--line); padding: 10px 12px; vertical-align: top; }
    th { background: #eef2f5; font-size: 13px; color: #424a53; }
    .notice { border-left: 4px solid var(--accent); }
    @media (max-width: 720px) { main { padding: 16px; } h1 { font-size: 28px; } .hero, section { padding: 16px; } }
    """


def _html_response(text: str, status: HTTPStatus = HTTPStatus.OK) -> tuple[int, str, bytes]:
    return int(status), "text/html; charset=utf-8", text.encode("utf-8")


def _json_response(payload: dict[str, Any]) -> tuple[int, str, bytes]:
    return _json_text_response(json.dumps(payload, ensure_ascii=False, indent=2))


def _json_text_response(text: str) -> tuple[int, str, bytes]:
    return int(HTTPStatus.OK), "application/json; charset=utf-8", text.encode("utf-8")


def _safe_segment(value: str) -> str:
    segment = Path(value).name
    if not segment or segment in {".", ".."}:
        raise KeyError(value)
    return segment
