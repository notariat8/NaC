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

from nac_web.bpmn import (
    BpmnSaveConflict,
    bpmn_model_json,
    bpmn_xml_document,
    find_bpmn_model,
    list_bpmn_models,
    render_bpmn_svg,
    save_bpmn_xml,
)
from notary_kg.catalog import all_case_summaries, load_catalogs
from notary_kg.editor import build_editor_view


STATUS_LABELS_DE = {
    "active_intake": "aktive Aufnahme",
    "draft": "Entwurf",
    "legacy_alias": "Altbezeichnung",
    "open": "offen",
}

ROLE_LABELS_DE = {
    "applicant": "Antragsteller",
    "association": "Verein",
    "client": "Mandant",
    "compliance": "Compliance",
    "developer": "Entwicklung",
    "founder": "Gründer",
    "notary": "Notarin/Notar",
    "notary_clerk": "Notariatsfachkraft",
    "principal": "Vollmachtgeber",
    "spouses": "Ehegatten",
    "system_betreuer": "Systembetreuung",
    "tax_clerk": "Steuerfachkraft",
    "testator": "Erblasser",
}


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
            if route == "/api/bpmn-moddle":
                return _json_text_response((self.repo_root / "bpmn" / "nac-moddle.json").read_text(encoding="utf-8"))
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

    def handle_post(self, path: str, body: bytes) -> tuple[int, str, bytes]:
        parsed = urlparse(path)
        route = unquote(parsed.path)
        try:
            if route.startswith("/api/bpmn/"):
                return self._bpmn_api_post(route.removeprefix("/api/bpmn/"), body)
        except KeyError as exc:
            return _json_response({"error": str(exc)}, HTTPStatus.NOT_FOUND)
        except BpmnSaveConflict as exc:
            return _json_response({"error": str(exc)}, HTTPStatus.CONFLICT)
        except ValueError as exc:
            return _json_response({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        return _json_response({"error": "Diese lokale NaC-POST-Route gibt es nicht."}, HTTPStatus.NOT_FOUND)

    def _bpmn_route(self, stem: str) -> tuple[int, str, bytes]:
        if stem.endswith("/edit"):
            model = find_bpmn_model(self.repo_root, _safe_segment(stem.removesuffix("/edit")))
            return _html_response(build_bpmn_editor_page(model))
        model = find_bpmn_model(self.repo_root, _safe_segment(stem))
        return _html_response(build_bpmn_page(model))

    def _kg_route(self, slug: str) -> tuple[int, str, bytes]:
        view = build_editor_view(self.repo_root, _safe_segment(slug))
        return _html_response(build_kg_page(view))

    def _bpmn_api_route(self, stem: str) -> tuple[int, str, bytes]:
        if stem.endswith("/xml"):
            return _json_response(bpmn_xml_document(self.repo_root, _safe_segment(stem.removesuffix("/xml"))))
        model = find_bpmn_model(self.repo_root, _safe_segment(stem))
        return _json_text_response(bpmn_model_json(model))

    def _bpmn_api_post(self, stem: str, body: bytes) -> tuple[int, str, bytes]:
        if not stem.endswith("/xml"):
            return _json_response({"error": "Nur /api/bpmn/<modell>/xml nimmt POST entgegen."}, HTTPStatus.NOT_FOUND)
        try:
            payload = json.loads(body.decode("utf-8"))
        except ValueError as exc:
            raise ValueError(f"Request Body ist kein gültiges JSON: {exc}") from exc
        xml = payload.get("xml")
        base_sha256 = payload.get("base_sha256")
        if not isinstance(xml, str):
            raise ValueError("xml muss ein String sein")
        if not isinstance(base_sha256, str):
            raise ValueError("base_sha256 muss ein String sein")
        return _json_response(save_bpmn_xml(self.repo_root, _safe_segment(stem.removesuffix("/xml")), xml, base_sha256))

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

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            status, content_type, body = app.handle_post(self.path, self.rfile.read(length))
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
        f'<span>{html.escape(model.path)} · <a class="inline-link" href="/bpmn/{html.escape(model.stem)}/edit">bearbeiten</a></span></li>'
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
        f'<td data-label="Name">{html.escape(node.name)}</td>'
        f'<td data-label="Typ">{html.escape(node.type)}</td>'
        f'<td data-label="Rolle">{html.escape(node.nac.get("role", ""))}</td>'
        f'<td data-label="Kanal">{html.escape(node.nac.get("channel", ""))}</td>'
        f'<td data-label="Datenklasse">{html.escape(node.nac.get("dataClass", ""))}</td>'
        f'<td data-label="Freigabe">{html.escape(node.nac.get("approval", ""))}</td>'
        f'<td data-label="Nachweis">{html.escape(node.nac.get("evidence", ""))}</td>'
        "</tr>"
        for node in model.nodes
    )
    body = f"""
    <nav class="topline"><a href="/">← Übersicht</a><span><a href="/bpmn/{html.escape(model.stem)}/edit">Bearbeiten</a><a href="/api/bpmn/{html.escape(model.stem)}">JSON</a></span></nav>
    <section class="hero">
      <p class="eyebrow">BPMN-Modell</p>
      <h1>{html.escape(model.name)}</h1>
      <p>{html.escape(model.path)} · {"bpmn-js-Diagrammfläche vorhanden" if model.has_diagram else "Fallback-Layout"}</p>
    </section>
    <section class="canvas bpmn-diagram-panel"><div class="diagram-scroll">{render_bpmn_svg(model)}</div></section>
    <section>
      <h2>NaC-Schritte</h2>
      <div class="table-scroll responsive-table">
        <table>
          <thead><tr><th>Name</th><th>Typ</th><th>Rolle</th><th>Kanal</th><th>Datenklasse</th><th>Freigabe</th><th>Nachweis</th></tr></thead>
          <tbody>{node_rows}</tbody>
        </table>
      </div>
    </section>
    """
    return _layout(f"BPMN: {model.name}", body)


def build_bpmn_editor_page(model) -> str:
    stem = html.escape(model.stem)
    node_menu = _bpmn_editor_node_menu(model)
    body = f"""
    <nav class="topline"><a href="/">← Übersicht</a><span><a href="/kg/{stem}">Checkliste</a><a href="/bpmn/{stem}">Ansicht</a><a href="/api/bpmn/{stem}/xml">XML API</a></span></nav>
    <section class="hero">
      <p class="eyebrow">BPMN-js Editor</p>
      <h1>{html.escape(model.name)}</h1>
      <p>{html.escape(model.path)} · Änderungen werden erst als BPMN-XML im Repository gespeichert und danach über Git validiert.</p>
    </section>
    <section class="bpmn-editor-shell">
      <div class="editor-commandbar" role="toolbar" aria-label="BPMN Editor Menü">
        <div class="command-group">
          <button id="save-model" type="button">Speichern</button>
          <button id="reload-model" type="button">Neu laden</button>
          <button id="validate-model" type="button">Prüfen</button>
        </div>
        <div class="command-group">
          <button id="undo-model" type="button">Rückgängig</button>
          <button id="redo-model" type="button">Wiederholen</button>
          <button id="delete-element" type="button">Löschen</button>
        </div>
        <div class="command-group">
          <button data-create-kind="bpmn:Task" type="button">Aufgabe</button>
          <button data-create-kind="bpmn:UserTask" type="button">Person</button>
          <button data-create-kind="bpmn:ServiceTask" type="button">Service</button>
          <button data-create-kind="bpmn:ExclusiveGateway" type="button">Entscheidung</button>
          <button data-create-kind="bpmn:EndEvent" type="button">Ende</button>
        </div>
        <div class="command-group">
          <button id="fit-model" type="button">Einpassen</button>
          <button id="zoom-in-model" type="button">Zoom +</button>
          <button id="zoom-out-model" type="button">Zoom -</button>
          <button id="toggle-xml" type="button">XML</button>
        </div>
      </div>
      <div class="editor-statusbar">
        <span id="editor-status">lade Editor ...</span>
        <span id="dirty-state">unverändert</span>
      </div>
      <div class="editor-workbench">
        <aside class="editor-side-panel">
          <h2>Schritte</h2>
          <div class="step-list">{node_menu}</div>
        </aside>
        <div class="editor-canvas-region">
          <div id="bpmn-canvas" class="modeler-canvas"></div>
        </div>
        <aside class="editor-properties-panel">
          <h2>Eigenschaften</h2>
          <form id="properties-form">
            <div class="selected-element" id="selected-element">Kein Element ausgewählt</div>
            <label for="element-name">Name</label>
            <input id="element-name" name="name" type="text" autocomplete="off">
            <label for="nac-role">Rolle</label>
            <select id="nac-role" name="role">
              <option value=""></option>
              <option value="notary_clerk">Notariatsfachkraft</option>
              <option value="notary">Notarin/Notar</option>
              <option value="system_betreuer">Systembetreuung</option>
              <option value="client">Mandant</option>
              <option value="compliance">Compliance</option>
            </select>
            <label for="nac-channel">Kanal</label>
            <input id="nac-channel" name="channel" type="text" autocomplete="off">
            <label for="nac-data-class">Datenklasse</label>
            <input id="nac-data-class" name="dataClass" type="text" autocomplete="off">
            <label for="nac-approval">Freigabe</label>
            <input id="nac-approval" name="approval" type="text" autocomplete="off">
            <label for="nac-evidence">Nachweis</label>
            <input id="nac-evidence" name="evidence" type="text" autocomplete="off">
            <label for="nac-plugin">Plugin</label>
            <input id="nac-plugin" name="plugin" type="text" autocomplete="off">
            <label for="nac-kg-ref">KG-Referenz</label>
            <input id="nac-kg-ref" name="kgRef" type="text" autocomplete="off">
            <label class="check-label" for="nac-local-execution">
              <input id="nac-local-execution" name="localExecution" type="checkbox">
              lokal ausführen
            </label>
            <button id="apply-properties" type="submit">Übernehmen</button>
          </form>
        </aside>
      </div>
      <div id="xml-panel" class="xml-panel is-hidden">
        <div class="xml-toolbar">
          <label class="xml-label" for="xml-editor">BPMN XML</label>
          <button id="import-xml" type="button">XML anwenden</button>
        </div>
        <textarea id="xml-editor" spellcheck="false"></textarea>
      </div>
    </section>
    <script>{_bpmn_editor_script(model.stem)}</script>
    """
    return _layout(f"BPMN bearbeiten: {model.name}", body, head_extra=_bpmn_editor_head())


def _bpmn_editor_head() -> str:
    return """
  <link rel="stylesheet" href="https://unpkg.com/bpmn-js@17.11.1/dist/assets/diagram-js.css">
  <link rel="stylesheet" href="https://unpkg.com/bpmn-js@17.11.1/dist/assets/bpmn-font/css/bpmn-embedded.css">
"""


def _bpmn_editor_node_menu(model) -> str:
    if not model.nodes:
        return '<p class="empty-state">Keine Schritte.</p>'
    return "".join(
        '<button class="step-button" type="button" '
        f'data-select-element="{html.escape(node.id, quote=True)}">'
        f'<span>{html.escape(node.name or node.id)}</span>'
        f'<small>{html.escape(_bpmn_node_type_label(node.type))}</small>'
        "</button>"
        for node in model.nodes
    )


def _bpmn_node_type_label(node_type: str) -> str:
    labels = {
        "businessRuleTask": "Regel",
        "callActivity": "Aufruf",
        "endEvent": "Ende",
        "exclusiveGateway": "Entscheidung",
        "manualTask": "Manuell",
        "parallelGateway": "Parallel",
        "receiveTask": "Empfang",
        "scriptTask": "Skript",
        "sendTask": "Versand",
        "serviceTask": "Service",
        "startEvent": "Start",
        "subProcess": "Teilprozess",
        "task": "Aufgabe",
        "userTask": "Person",
    }
    return labels.get(node_type, node_type)


def _bpmn_editor_script(stem: str) -> str:
    replacements = {
        "__ENDPOINT__": json.dumps(f"/api/bpmn/{stem}/xml"),
        "__MODDLE_ENDPOINT__": json.dumps("/api/bpmn-moddle"),
    }
    script = r"""
    const endpoint = __ENDPOINT__;
    const moddleEndpoint = __MODDLE_ENDPOINT__;
    const modelerScript = "https://unpkg.com/bpmn-js@17.11.1/dist/bpmn-modeler.production.min.js";
    const nacKeys = ["role", "channel", "dataClass", "approval", "evidence", "plugin", "kgRef"];
    let baseSha256 = "";
    let loadedXml = "";
    let modeler = null;
    let selectedElement = null;
    let wired = false;

    const statusEl = document.getElementById("editor-status");
    const dirtyEl = document.getElementById("dirty-state");
    const xmlEditor = document.getElementById("xml-editor");
    const xmlPanel = document.getElementById("xml-panel");
    const propertiesForm = document.getElementById("properties-form");
    const selectedEl = document.getElementById("selected-element");
    const buttons = {
      save: document.getElementById("save-model"),
      reload: document.getElementById("reload-model"),
      validate: document.getElementById("validate-model"),
      undo: document.getElementById("undo-model"),
      redo: document.getElementById("redo-model"),
      delete: document.getElementById("delete-element"),
      fit: document.getElementById("fit-model"),
      zoomIn: document.getElementById("zoom-in-model"),
      zoomOut: document.getElementById("zoom-out-model"),
      toggleXml: document.getElementById("toggle-xml"),
      importXml: document.getElementById("import-xml")
    };

    function setStatus(value) {
      statusEl.textContent = value;
    }

    function setDirty(value) {
      dirtyEl.textContent = value ? "ungespeichert" : "unverändert";
      dirtyEl.classList.toggle("is-dirty", value);
    }

    function setBusy(value) {
      document.querySelectorAll(".editor-commandbar button, #import-xml")
        .forEach((button) => { button.disabled = value; });
      if (value) document.getElementById("apply-properties").disabled = true;
    }

    function loadScript(src) {
      return new Promise((resolve, reject) => {
        if (window.BpmnJS) {
          resolve();
          return;
        }
        const script = document.createElement("script");
        script.src = src;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
      });
    }

    async function loadDocument() {
      const response = await fetch(endpoint);
      if (!response.ok) throw new Error(await response.text());
      const payload = await response.json();
      baseSha256 = payload.sha256;
      loadedXml = payload.xml;
      xmlEditor.value = payload.xml;
      setDirty(false);
      setStatus("geladen · " + payload.sha256.slice(0, 12));
    }

    async function createModeler() {
      if (modeler) return;
      await loadScript(modelerScript);
      const descriptor = await fetch(moddleEndpoint).then((response) => response.json());
      modeler = new window.BpmnJS({
        container: "#bpmn-canvas",
        keyboard: { bindTo: document },
        moddleExtensions: { nac: descriptor }
      });
      wireModeler();
    }

    function wireModeler() {
      if (wired) return;
      wired = true;
      const eventBus = modeler.get("eventBus");
      eventBus.on("selection.changed", (event) => {
        selectedElement = event.newSelection[0] || null;
        renderProperties();
        markStepSelection();
      });
      eventBus.on("element.changed", (event) => {
        if (selectedElement && event.element && event.element.id === selectedElement.id) {
          selectedElement = event.element;
          renderProperties();
        }
      });
      eventBus.on("commandStack.changed", async () => {
        await syncXmlFromCanvas();
        updateCommandState();
      });
    }

    async function importXml(xml) {
      await createModeler();
      await modeler.importXML(xml);
      modeler.get("canvas").zoom("fit-viewport");
      selectedElement = null;
      renderProperties();
      updateCommandState();
      setStatus("Editor bereit · Änderungen bleiben lokal bis Speichern");
    }

    async function syncXmlFromCanvas() {
      if (!modeler) return;
      const saved = await modeler.saveXML({ format: true });
      xmlEditor.value = saved.xml;
      setDirty(saved.xml !== loadedXml);
    }

    function updateCommandState() {
      if (!modeler) return;
      const commandStack = modeler.get("commandStack");
      buttons.undo.disabled = !commandStack.canUndo();
      buttons.redo.disabled = !commandStack.canRedo();
      buttons.delete.disabled = !selectedElement;
    }

    function markStepSelection() {
      document.querySelectorAll("[data-select-element]").forEach((button) => {
        button.classList.toggle("is-selected", selectedElement && button.dataset.selectElement === selectedElement.id);
      });
    }

    function selectElement(id) {
      if (!modeler) return;
      const registry = modeler.get("elementRegistry");
      const selection = modeler.get("selection");
      const element = registry.get(id);
      if (!element) return;
      selection.select(element);
      focusElement(element);
    }

    function focusElement(element) {
      const canvas = modeler.get("canvas");
      const viewbox = canvas.viewbox();
      canvas.viewbox({
        x: element.x + element.width / 2 - viewbox.width / 2,
        y: element.y + element.height / 2 - viewbox.height / 2,
        width: viewbox.width,
        height: viewbox.height
      });
    }

    function getNacValue(businessObject, key) {
      if (!businessObject) return "";
      if (typeof businessObject.get === "function") {
        const namespaced = businessObject.get("nac:" + key);
        if (namespaced !== undefined && namespaced !== null) return String(namespaced);
        const plain = businessObject.get(key);
        if (plain !== undefined && plain !== null) return String(plain);
      }
      if (businessObject.$attrs && businessObject.$attrs["nac:" + key] !== undefined) {
        return String(businessObject.$attrs["nac:" + key]);
      }
      return "";
    }

    function canHaveNacProperties(businessObject) {
      if (!businessObject || !businessObject.$type) return false;
      return !businessObject.$type.includes("SequenceFlow") && !businessObject.$type.includes("Participant");
    }

    function renderProperties() {
      const businessObject = selectedElement && selectedElement.businessObject;
      const hasSelection = Boolean(businessObject);
      const hasNac = canHaveNacProperties(businessObject);
      selectedEl.textContent = hasSelection
        ? selectedElement.id + " · " + businessObject.$type.replace("bpmn:", "")
        : "Kein Element ausgewählt";
      document.getElementById("element-name").value = hasSelection ? (businessObject.name || "") : "";
      nacKeys.forEach((key) => {
        const fieldId = "nac-" + key.replace(/[A-Z]/g, (letter) => "-" + letter.toLowerCase());
        const field = document.getElementById(fieldId);
        if (!field) return;
        field.value = hasSelection ? getNacValue(businessObject, key) : "";
        field.disabled = !hasNac;
      });
      const localExecution = document.getElementById("nac-local-execution");
      localExecution.checked = hasSelection && getNacValue(businessObject, "localExecution") === "true";
      localExecution.disabled = !hasNac;
      document.getElementById("apply-properties").disabled = !hasSelection;
      updateCommandState();
    }

    function applyProperties(event) {
      event.preventDefault();
      if (!modeler || !selectedElement) return;
      const modeling = modeler.get("modeling");
      const props = { name: document.getElementById("element-name").value.trim() };
      if (canHaveNacProperties(selectedElement.businessObject)) {
        nacKeys.forEach((key) => {
          const fieldId = "nac-" + key.replace(/[A-Z]/g, (letter) => "-" + letter.toLowerCase());
          const field = document.getElementById(fieldId);
          props["nac:" + key] = field ? field.value.trim() : "";
        });
        props["nac:localExecution"] = document.getElementById("nac-local-execution").checked;
      }
      modeling.updateProperties(selectedElement, props);
      setStatus("Eigenschaften übernommen");
    }

    function addShape(type) {
      if (!modeler) return;
      const canvas = modeler.get("canvas");
      const elementFactory = modeler.get("elementFactory");
      const modeling = modeler.get("modeling");
      const shape = elementFactory.createShape({ type });
      if (selectedElement && selectedElement.parent && !selectedElement.businessObject.$type.includes("SequenceFlow")) {
        const position = {
          x: selectedElement.x + selectedElement.width + 180,
          y: selectedElement.y + selectedElement.height / 2
        };
        modeling.appendShape(selectedElement, shape, position, selectedElement.parent);
        return;
      }
      const root = canvas.getRootElement();
      const viewbox = canvas.viewbox();
      modeling.createShape(shape, {
        x: viewbox.x + viewbox.width / 2,
        y: viewbox.y + viewbox.height / 2
      }, root);
    }

    async function saveDocument() {
      try {
        setBusy(true);
        setStatus("speichere ...");
        await syncXmlFromCanvas();
        const response = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ xml: xmlEditor.value, base_sha256: baseSha256 })
        });
        const payload = await response.json();
        if (!response.ok) {
          setStatus("nicht gespeichert · " + payload.error);
          return;
        }
        baseSha256 = payload.sha256;
        loadedXml = payload.xml;
        xmlEditor.value = payload.xml;
        setDirty(false);
        setStatus("gespeichert · " + payload.sha256.slice(0, 12));
      } catch (error) {
        setStatus("nicht gespeichert · " + error.message);
      } finally {
        setBusy(false);
        renderProperties();
      }
    }

    async function reloadDocument() {
      if (dirtyEl.classList.contains("is-dirty") && !window.confirm("Ungespeicherte Änderungen verwerfen?")) return;
      try {
        setBusy(true);
        await loadDocument();
        await importXml(xmlEditor.value);
      } catch (error) {
        setStatus("Fehler · " + error.message);
      } finally {
        setBusy(false);
        renderProperties();
      }
    }

    async function validateDocument() {
      try {
        await syncXmlFromCanvas();
        if (!xmlEditor.value.includes("<bpmn:process")) {
          setStatus("Prüfung fehlgeschlagen · bpmn:process fehlt");
          return;
        }
        setStatus("Prüfung ok · XML kann gespeichert werden");
      } catch (error) {
        setStatus("Prüfung fehlgeschlagen · " + error.message);
      }
    }

    buttons.save.addEventListener("click", saveDocument);
    buttons.reload.addEventListener("click", reloadDocument);
    buttons.validate.addEventListener("click", validateDocument);
    buttons.undo.addEventListener("click", () => modeler && modeler.get("commandStack").undo());
    buttons.redo.addEventListener("click", () => modeler && modeler.get("commandStack").redo());
    buttons.delete.addEventListener("click", () => {
      if (modeler && selectedElement) modeler.get("modeling").removeElements([selectedElement]);
    });
    buttons.fit.addEventListener("click", () => modeler && modeler.get("canvas").zoom("fit-viewport"));
    buttons.zoomIn.addEventListener("click", () => modeler && modeler.get("zoomScroll").stepZoom(1));
    buttons.zoomOut.addEventListener("click", () => modeler && modeler.get("zoomScroll").stepZoom(-1));
    buttons.toggleXml.addEventListener("click", () => xmlPanel.classList.toggle("is-hidden"));
    buttons.importXml.addEventListener("click", async () => {
      try {
        await importXml(xmlEditor.value);
        setDirty(xmlEditor.value !== loadedXml);
      } catch (error) {
        setStatus("XML nicht angewendet · " + error.message);
      }
    });
    propertiesForm.addEventListener("submit", applyProperties);
    xmlEditor.addEventListener("input", () => setDirty(xmlEditor.value !== loadedXml));
    document.querySelectorAll("[data-select-element]").forEach((button) => {
      button.addEventListener("click", () => selectElement(button.dataset.selectElement));
    });
    document.querySelectorAll("[data-create-kind]").forEach((button) => {
      button.addEventListener("click", () => addShape(button.dataset.createKind));
    });

    setBusy(true);
    loadDocument()
      .then(() => importXml(xmlEditor.value))
      .catch((error) => setStatus("Fehler · " + error.message))
      .finally(() => {
        setBusy(false);
        renderProperties();
      });
"""
    for key, value in replacements.items():
        script = script.replace(key, value)
    return script


def build_kg_page(view: dict[str, Any]) -> str:
    tabs = "".join(_render_kg_tab(tab) for tab in view["editor_model"]["tabs"])
    status = _status_label(view.get("status", ""))
    body = f"""
    <nav class="topline"><a href="/">← Übersicht</a><a href="/api/kg/{html.escape(view['usecase_slug'])}">JSON</a></nav>
    <section class="hero">
      <p class="eyebrow">KG-Editor-View</p>
      <h1>{html.escape(view['title'])}</h1>
      <p>Status: {html.escape(status)}</p>
    </section>
    <section class="notice">
      <strong>Schutzregel:</strong> Diese Ansicht zeigt keine Mandatswerte.
      Änderungen werden als Vorschlag erfasst und erst nach Validierung, Änderungsvergleich und Review übernommen.
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
        f"<td>{html.escape(_status_label(item.get('status', '')))}</td>"
        f"<td>{html.escape(_role_or_source_label(item))}</td>"
        "</tr>"
        for item in items
    )
    return (
        "<table>"
        "<thead><tr><th>Eintrag</th><th>Status</th><th>Rolle/Quelle</th></tr></thead>"
        f"<tbody>{rows}</tbody>"
        "</table>"
    )


def _status_label(value: Any) -> str:
    raw = str(value or "").strip()
    return STATUS_LABELS_DE.get(raw, _identifier_fallback(raw))


def _role_or_source_label(item: dict[str, Any]) -> str:
    if "owner_role" in item:
        raw = str(item.get("owner_role") or "").strip()
        return ROLE_LABELS_DE.get(raw, _identifier_fallback(raw))
    return str(item.get("source", "") or "").strip()


def _identifier_fallback(value: str) -> str:
    return value.replace("_", " ").replace("-", " ")


def _layout(title: str, body: str, head_extra: str = "") -> str:
    return f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>{_css()}</style>
{head_extra}
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
    main { width: calc(100% - 32px); max-width: 1440px; margin: 0 auto; padding: 28px 0; }
    h1 { margin: 0 0 12px; font-size: 36px; line-height: 1.1; letter-spacing: 0; }
    h2 { margin: 0 0 16px; font-size: 22px; letter-spacing: 0; }
    p { color: var(--muted); line-height: 1.55; overflow-wrap: anywhere; }
    code { background: #eef2f5; border-radius: 4px; padding: 2px 5px; }
    .hero, section { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 22px; margin: 0 0 20px; }
    .eyebrow { margin: 0 0 8px; color: var(--accent); font-weight: 700; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }
    .link-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
    .link-list li { border: 1px solid var(--line); border-radius: 8px; padding: 12px; background: #fff; }
    .link-list a { display: block; color: #0b4f6c; font-weight: 700; text-decoration: none; margin-bottom: 4px; }
    .link-list .inline-link { display: inline; margin: 0; font-weight: 600; }
    .link-list span { color: var(--muted); font-size: 14px; }
    .topline { display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin: 0 0 18px; }
    .topline span { display: flex; gap: 14px; flex-wrap: wrap; }
    .topline a { color: #0b4f6c; font-weight: 700; text-decoration: none; }
    .toolbar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin: 0 0 14px; }
    button { appearance: none; border: 0; border-radius: 6px; background: #0b4f6c; color: #fff; font-weight: 700; padding: 10px 14px; cursor: pointer; }
    button:disabled { opacity: .55; cursor: not-allowed; }
    #editor-status { color: var(--muted); font-size: 14px; }
    .bpmn-editor-shell { padding: 0; overflow: hidden; }
    .editor-commandbar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; padding: 14px; border-bottom: 1px solid var(--line); background: #fff; }
    .command-group { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; padding-right: 10px; border-right: 1px solid var(--line); }
    .command-group:last-child { border-right: 0; }
    .command-group button { background: #254b68; padding: 9px 12px; }
    .command-group [data-create-kind] { background: #2f6b50; }
    .editor-statusbar { display: flex; justify-content: space-between; gap: 14px; align-items: center; padding: 10px 14px; border-bottom: 1px solid var(--line); background: #fbfcfd; }
    #dirty-state { font-size: 13px; color: var(--muted); font-weight: 700; }
    #dirty-state.is-dirty { color: #9a5b00; }
    .editor-workbench { display: grid; grid-template-columns: 250px minmax(520px, 1fr) 300px; min-height: 680px; }
    .editor-side-panel, .editor-properties-panel { border: 0; border-radius: 0; margin: 0; padding: 14px; background: #fbfcfd; overflow: auto; }
    .editor-side-panel { border-right: 1px solid var(--line); }
    .editor-properties-panel { border-left: 1px solid var(--line); }
    .editor-side-panel h2, .editor-properties-panel h2 { font-size: 16px; margin-bottom: 12px; }
    .step-list { display: grid; gap: 8px; }
    .step-button { width: 100%; background: #fff; color: var(--ink); border: 1px solid var(--line); text-align: left; padding: 10px; }
    .step-button span, .step-button small { display: block; }
    .step-button span { font-weight: 700; line-height: 1.25; }
    .step-button small { color: var(--muted); margin-top: 3px; }
    .step-button.is-selected { border-color: var(--accent); box-shadow: inset 3px 0 0 var(--accent); }
    .editor-canvas-region { min-width: 0; background: #fff; }
    .modeler-canvas { height: 68vh; min-height: 680px; border: 0; background: #fff; margin: 0; position: relative; overflow: hidden; }
    .modeler-canvas .djs-container { width: 100% !important; height: 100% !important; }
    .modeler-canvas .djs-palette { top: 16px; left: 16px; }
    .selected-element { min-height: 40px; border: 1px solid var(--line); border-radius: 6px; background: #fff; padding: 9px 10px; color: var(--muted); font-size: 13px; margin-bottom: 12px; overflow-wrap: anywhere; }
    #properties-form { display: grid; gap: 8px; }
    #properties-form label { font-weight: 700; font-size: 13px; }
    #properties-form input, #properties-form select { width: 100%; border: 1px solid var(--line); border-radius: 6px; padding: 8px 9px; font: inherit; background: #fff; }
    #properties-form input:disabled, #properties-form select:disabled { background: #eef2f5; color: var(--muted); }
    .check-label { display: flex; align-items: center; gap: 8px; margin: 2px 0 6px; }
    .check-label input { width: auto; }
    .xml-panel { border-top: 1px solid var(--line); padding: 14px; background: #fff; }
    .xml-panel.is-hidden { display: none; }
    .xml-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 8px; }
    .xml-label { display: block; font-weight: 700; margin: 0 0 8px; }
    textarea { width: 100%; min-height: 280px; resize: vertical; border: 1px solid var(--line); border-radius: 8px; padding: 12px; font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace; font-size: 13px; line-height: 1.45; }
    .canvas { overflow: hidden; padding: 8px; background: #fbfcfd; }
    .bpmn-diagram-panel { min-height: 220px; }
    .diagram-scroll { width: 100%; overflow-x: auto; overflow-y: hidden; padding: 6px 0 12px; }
    .bpmn-svg { width: auto; max-width: none; height: auto; display: block; }
    .flow { fill: none; stroke: #41516b; stroke-width: 2.2; }
    .flow-label { font-size: 13px; fill: #41516b; text-anchor: middle; font-weight: 700; }
    .node rect, .node circle, .node polygon { fill: #fff; stroke: #2f6f88; stroke-width: 2.2; }
    .node.serviceTask rect { fill: #edf7f4; stroke: #2f6b50; }
    .gateway polygon { fill: #fff8e8; stroke: #936e1d; }
    .end circle { stroke: #7b2d26; }
    .node-label { text-anchor: middle; dominant-baseline: middle; font-size: 14px; font-weight: 700; fill: var(--ink); }
    .node-badge { text-anchor: middle; font-size: 12px; fill: var(--muted); }
    .table-scroll { width: 100%; overflow-x: auto; }
    .table-scroll table { min-width: 980px; }
    table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
    th, td { text-align: left; border-bottom: 1px solid var(--line); padding: 10px 12px; vertical-align: top; overflow-wrap: anywhere; }
    th { background: #eef2f5; font-size: 13px; color: #424a53; }
    .notice { border-left: 4px solid var(--accent); }
    @media (max-width: 1040px) { .editor-workbench { grid-template-columns: 1fr; } .editor-side-panel, .editor-properties-panel { border: 0; border-bottom: 1px solid var(--line); } .modeler-canvas { min-height: 560px; } }
    @media (max-width: 760px) { .responsive-table { overflow: visible; } .responsive-table table, .responsive-table thead, .responsive-table tbody, .responsive-table tr, .responsive-table th, .responsive-table td { display: block; width: 100%; min-width: 0; } .responsive-table thead { display: none; } .responsive-table table { min-width: 0; border: 0; background: transparent; } .responsive-table tr { border: 1px solid var(--line); border-radius: 8px; background: #fff; margin: 0 0 10px; padding: 10px 12px; } .responsive-table td { display: grid; grid-template-columns: 116px minmax(0, 1fr); gap: 12px; border: 0; padding: 6px 0; } .responsive-table td::before { content: attr(data-label); color: #424a53; font-size: 13px; font-weight: 700; } }
    @media (max-width: 720px) { main { width: calc(100% - 24px); padding: 16px 0; } h1 { font-size: 28px; } .hero, section { padding: 16px; } .bpmn-editor-shell { padding: 0; } }
    """


def _html_response(text: str, status: HTTPStatus = HTTPStatus.OK) -> tuple[int, str, bytes]:
    return int(status), "text/html; charset=utf-8", text.encode("utf-8")


def _json_response(payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> tuple[int, str, bytes]:
    return _json_text_response(json.dumps(payload, ensure_ascii=False, indent=2), status)


def _json_text_response(text: str, status: HTTPStatus = HTTPStatus.OK) -> tuple[int, str, bytes]:
    return int(status), "application/json; charset=utf-8", text.encode("utf-8")


def _safe_segment(value: str) -> str:
    segment = Path(value).name
    if not segment or segment in {".", ".."}:
        raise KeyError(value)
    return segment
