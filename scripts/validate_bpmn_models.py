from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BPMN_ROOT = REPO_ROOT / "bpmn"
NAC_MODDLE = BPMN_ROOT / "nac-moddle.json"

BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
NAC_NS = "https://github.com/ofunk/NaC/bpmn/nac"
NAC_PROFILE = "nac-bpmn/v0.1"

FLOW_NODE_NAMES = {
    "startEvent",
    "endEvent",
    "task",
    "userTask",
    "manualTask",
    "serviceTask",
    "businessRuleTask",
    "scriptTask",
    "sendTask",
    "receiveTask",
    "callActivity",
    "subProcess",
    "exclusiveGateway",
    "inclusiveGateway",
    "parallelGateway",
    "eventBasedGateway",
}

TASK_NAMES = {
    "task",
    "userTask",
    "manualTask",
    "serviceTask",
    "businessRuleTask",
    "scriptTask",
    "sendTask",
    "receiveTask",
    "callActivity",
}

ALLOWED_DATA_CLASSES = {
    "metadata",
    "public_reference",
    "confidential_placeholder",
    "no_mandate_data",
}
ALLOWED_APPROVALS = {"none", "human", "four_eyes"}
ALLOWED_EVIDENCE = {"none", "optional", "required"}
FORBIDDEN_NAME_PARTS = ("passwort", "password", "pin", "secret", "token", "api-key", "apikey")


@dataclass(frozen=True)
class BpmnElement:
    path: Path
    xml: ET.Element

    @property
    def tag_name(self) -> str:
        return self.xml.tag.rsplit("}", maxsplit=1)[-1]

    @property
    def element_id(self) -> str:
        return self.xml.attrib.get("id", "<missing-id>")

    @property
    def name(self) -> str:
        return self.xml.attrib.get("name", "")

    def nac_attr(self, key: str) -> str | None:
        return self.xml.attrib.get(f"{{{NAC_NS}}}{key}")

    def location(self) -> str:
        return f"{display_path(self.path)}:{self.element_id}"


def qname(namespace: str, local_name: str) -> str:
    return f"{{{namespace}}}{local_name}"


def display_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def parse_xml(path: Path) -> ET.Element | None:
    try:
        return ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"{display_path(path)} ist kein gültiges XML: {exc}") from exc


def children_by_tag(parent: ET.Element, local_name: str) -> list[ET.Element]:
    return list(parent.findall(f"bpmn:{local_name}", {"bpmn": BPMN_NS}))


def all_process_children(process: ET.Element) -> list[ET.Element]:
    return [child for child in process if child.tag.startswith(f"{{{BPMN_NS}}}")]


def flow_nodes(process: ET.Element, path: Path) -> list[BpmnElement]:
    return [
        BpmnElement(path, child)
        for child in all_process_children(process)
        if child.tag.rsplit("}", maxsplit=1)[-1] in FLOW_NODE_NAMES
    ]


def sequence_flows(process: ET.Element) -> list[ET.Element]:
    return children_by_tag(process, "sequenceFlow")


def validate_moddle_descriptor() -> list[str]:
    errors: list[str] = []
    if not NAC_MODDLE.exists():
        return ["bpmn/nac-moddle.json fehlt"]

    try:
        payload = json.loads(NAC_MODDLE.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"bpmn/nac-moddle.json ist kein gültiges JSON: {exc}"]

    if payload.get("prefix") != "nac":
        errors.append("bpmn/nac-moddle.json muss prefix=nac setzen")
    if payload.get("uri") != NAC_NS:
        errors.append(f"bpmn/nac-moddle.json muss uri={NAC_NS} setzen")

    properties: set[str] = set()
    for entry in payload.get("types", []):
        for prop in entry.get("properties", []):
            if prop.get("isAttr"):
                properties.add(prop.get("name", ""))

    required = {"profile", "owner", "binding", "role", "dataClass", "approval", "evidence", "plugin", "localExecution", "kgRef"}
    missing = sorted(required - properties)
    for name in missing:
        errors.append(f"bpmn/nac-moddle.json fehlt NaC-Attribut: {name}")
    return errors


def validate_basic_bpmn(path: Path, root: ET.Element) -> list[str]:
    errors: list[str] = []
    rel_path = display_path(path)
    if root.tag != qname(BPMN_NS, "definitions"):
        return [f"{rel_path}: Root-Element muss bpmn:definitions sein"]

    processes = children_by_tag(root, "process")
    if not processes:
        errors.append(f"{rel_path}: mindestens ein bpmn:process ist erforderlich")

    for process in processes:
        process_id = process.attrib.get("id", "<missing-id>")
        if not process.attrib.get("id"):
            errors.append(f"{rel_path}: process ohne id")
        if not process.attrib.get("name"):
            errors.append(f"{rel_path}:{process_id}: process braucht name")

        ids = {
            child.attrib.get("id")
            for child in all_process_children(process)
            if child.attrib.get("id")
        }
        for flow in sequence_flows(process):
            flow_id = flow.attrib.get("id", "<missing-id>")
            source = flow.attrib.get("sourceRef")
            target = flow.attrib.get("targetRef")
            if source not in ids:
                errors.append(f"{rel_path}:{flow_id}: sourceRef zeigt auf unbekanntes Element {source!r}")
            if target not in ids:
                errors.append(f"{rel_path}:{flow_id}: targetRef zeigt auf unbekanntes Element {target!r}")

        starts = children_by_tag(process, "startEvent")
        ends = children_by_tag(process, "endEvent")
        if not starts:
            errors.append(f"{rel_path}:{process_id}: mindestens ein Start-Ereignis fehlt")
        if not ends:
            errors.append(f"{rel_path}:{process_id}: mindestens ein Ende-Ereignis fehlt")

        for node in flow_nodes(process, path):
            if not node.name:
                errors.append(f"{node.location()}: sichtbarer Name fehlt")
            lowered_name = node.name.lower()
            forbidden = next((part for part in FORBIDDEN_NAME_PARTS if part in lowered_name), None)
            if forbidden:
                errors.append(f"{node.location()}: Name enthält verbotenen Geheimnis-Hinweis {forbidden!r}")

        for gateway in [
            node
            for node in flow_nodes(process, path)
            if node.tag_name in {"exclusiveGateway", "inclusiveGateway", "eventBasedGateway"}
        ]:
            outgoing_ids = [child.text for child in gateway.xml.findall("bpmn:outgoing", {"bpmn": BPMN_NS}) if child.text]
            if len(outgoing_ids) > 1:
                flow_names = {
                    flow.attrib.get("id"): flow.attrib.get("name", "")
                    for flow in sequence_flows(process)
                }
                for outgoing_id in outgoing_ids:
                    if not flow_names.get(outgoing_id):
                        errors.append(f"{gateway.location()}: ausgehender Pfad {outgoing_id} braucht eine sichtbare Beschriftung")
    return errors


def validate_nac_profile(path: Path, root: ET.Element) -> list[str]:
    errors: list[str] = []
    rel_path = display_path(path)
    diagrams = root.findall(f"bpmndi:BPMNDiagram", {"bpmndi": BPMNDI_NS})

    for process in children_by_tag(root, "process"):
        profile = process.attrib.get(f"{{{NAC_NS}}}profile")
        if profile is None:
            continue
        process_id = process.attrib.get("id", "<missing-id>")
        if profile != NAC_PROFILE:
            errors.append(f"{rel_path}:{process_id}: nac:profile muss {NAC_PROFILE} sein")
        if not process.attrib.get(f"{{{NAC_NS}}}owner"):
            errors.append(f"{rel_path}:{process_id}: nac:owner fehlt")
        if not process.attrib.get(f"{{{NAC_NS}}}binding"):
            errors.append(f"{rel_path}:{process_id}: nac:binding fehlt")
        if not diagrams:
            errors.append(f"{rel_path}:{process_id}: bpmn-js-taugliche BPMNDI-Diagrammfläche fehlt")

        for node in flow_nodes(process, path):
            if not node.nac_attr("role"):
                errors.append(f"{node.location()}: nac:role fehlt")
            data_class = node.nac_attr("dataClass")
            if data_class not in ALLOWED_DATA_CLASSES:
                errors.append(f"{node.location()}: nac:dataClass ist ungültig: {data_class!r}")
            approval = node.nac_attr("approval")
            if approval not in ALLOWED_APPROVALS:
                errors.append(f"{node.location()}: nac:approval ist ungültig: {approval!r}")
            evidence = node.nac_attr("evidence")
            if evidence not in ALLOWED_EVIDENCE:
                errors.append(f"{node.location()}: nac:evidence ist ungültig: {evidence!r}")
            if not node.nac_attr("kgRef"):
                errors.append(f"{node.location()}: nac:kgRef fehlt")
            if node.tag_name == "serviceTask" and node.nac_attr("localExecution") != "true":
                errors.append(f"{node.location()}: serviceTask braucht nac:localExecution=true")
            if node.tag_name in TASK_NAMES and data_class == "no_mandate_data" and approval == "four_eyes":
                errors.append(f"{node.location()}: four_eyes passt nicht zu no_mandate_data")
    return errors


def validate_file(path: Path) -> list[str]:
    try:
        root = parse_xml(path)
    except ValueError as exc:
        return [str(exc)]
    if root is None:
        return [f"{display_path(path)} konnte nicht gelesen werden"]
    errors = validate_basic_bpmn(path, root)
    errors.extend(validate_nac_profile(path, root))
    return errors


def validate() -> list[str]:
    errors = validate_moddle_descriptor()
    bpmn_files = sorted(BPMN_ROOT.rglob("*.bpmn"))
    if not bpmn_files:
        errors.append("bpmn/ enthält keine BPMN-Dateien")
        return errors
    for path in bpmn_files:
        errors.extend(validate_file(path))
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("BPMN validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("BPMN validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
