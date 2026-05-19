from __future__ import annotations

import html
import json
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
DC_NS = "http://www.omg.org/spec/DD/20100524/DC"
DI_NS = "http://www.omg.org/spec/DD/20100524/DI"
NAC_NS = "https://github.com/ofunk/NaC/bpmn/nac"

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


@dataclass(frozen=True, slots=True)
class BpmnNode:
    id: str
    type: str
    name: str
    nac: dict[str, str]
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True, slots=True)
class BpmnFlow:
    id: str
    name: str
    source: str
    target: str
    waypoints: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class BpmnModel:
    stem: str
    path: str
    process_id: str
    name: str
    has_diagram: bool
    nodes: tuple[BpmnNode, ...]
    flows: tuple[BpmnFlow, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "stem": self.stem,
            "path": self.path,
            "process_id": self.process_id,
            "name": self.name,
            "has_diagram": self.has_diagram,
            "nodes": [asdict(node) for node in self.nodes],
            "flows": [asdict(flow) for flow in self.flows],
        }


def list_bpmn_models(repo_root: Path) -> list[BpmnModel]:
    return [load_bpmn_model(path, repo_root) for path in sorted((repo_root / "bpmn").glob("*.bpmn"))]


def find_bpmn_model(repo_root: Path, stem: str) -> BpmnModel:
    safe_stem = Path(stem).name
    path = repo_root / "bpmn" / f"{safe_stem}.bpmn"
    if not path.exists():
        raise KeyError(f"Unknown BPMN model: {stem}")
    return load_bpmn_model(path, repo_root)


def load_bpmn_model(path: Path, repo_root: Path) -> BpmnModel:
    root = ET.parse(path).getroot()
    process = root.find("bpmn:process", _ns())
    if process is None:
        raise ValueError(f"{_display_path(path, repo_root)} enthält keinen bpmn:process")

    shape_bounds = _shape_bounds(root)
    raw_nodes = _raw_nodes(process)
    bounds = _with_fallback_layout(raw_nodes, shape_bounds)
    nodes = tuple(_node_from_xml(child, bounds[child.attrib["id"]]) for child in raw_nodes if child.attrib.get("id"))
    flows = tuple(_flow_from_xml(flow, root, bounds) for flow in process.findall("bpmn:sequenceFlow", _ns()))

    return BpmnModel(
        stem=path.stem,
        path=_display_path(path, repo_root),
        process_id=str(process.attrib.get("id", "")),
        name=str(process.attrib.get("name", path.stem)),
        has_diagram=bool(shape_bounds),
        nodes=nodes,
        flows=flows,
    )


def render_bpmn_svg(model: BpmnModel) -> str:
    if not model.nodes:
        return "<svg role=\"img\" aria-label=\"Leeres BPMN-Modell\"></svg>"

    min_x = min(node.x for node in model.nodes) - 80
    min_y = min(node.y for node in model.nodes) - 80
    max_x = max(node.x + node.width for node in model.nodes) + 100
    max_y = max(node.y + node.height for node in model.nodes) + 100
    width = max(640, int(max_x - min_x))
    height = max(320, int(max_y - min_y))

    parts = [
        f'<svg class="bpmn-svg" viewBox="{min_x:g} {min_y:g} {width:g} {height:g}" role="img" aria-label="{html.escape(model.name)}">',
        "<defs>",
        '<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">',
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#41516b"/>',
        "</marker>",
        "</defs>",
    ]
    parts.extend(_render_flow(flow) for flow in model.flows)
    parts.extend(_render_node(node) for node in model.nodes)
    parts.append("</svg>")
    return "\n".join(parts)


def bpmn_model_json(model: BpmnModel) -> str:
    return json.dumps(model.to_dict(), ensure_ascii=False, indent=2)


def _ns() -> dict[str, str]:
    return {
        "bpmn": BPMN_NS,
        "bpmndi": BPMNDI_NS,
        "dc": DC_NS,
        "di": DI_NS,
    }


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _shape_bounds(root: ET.Element) -> dict[str, tuple[float, float, float, float]]:
    bounds: dict[str, tuple[float, float, float, float]] = {}
    for shape in root.findall(".//bpmndi:BPMNShape", _ns()):
        element_id = shape.attrib.get("bpmnElement")
        bound = shape.find("dc:Bounds", _ns())
        if not element_id or bound is None:
            continue
        bounds[element_id] = (
            float(bound.attrib.get("x", "0")),
            float(bound.attrib.get("y", "0")),
            float(bound.attrib.get("width", "120")),
            float(bound.attrib.get("height", "70")),
        )
    return bounds


def _raw_nodes(process: ET.Element) -> list[ET.Element]:
    nodes: list[ET.Element] = []
    for child in process:
        tag_name = child.tag.rsplit("}", maxsplit=1)[-1]
        if tag_name in FLOW_NODE_NAMES and child.attrib.get("id"):
            nodes.append(child)
    return nodes


def _with_fallback_layout(
    raw_nodes: list[ET.Element],
    shape_bounds: dict[str, tuple[float, float, float, float]],
) -> dict[str, tuple[float, float, float, float]]:
    bounds = dict(shape_bounds)
    for index, child in enumerate(raw_nodes):
        element_id = child.attrib.get("id", "")
        if element_id in bounds:
            continue
        tag_name = child.tag.rsplit("}", maxsplit=1)[-1]
        width, height = (44, 44) if tag_name in {"startEvent", "endEvent"} else (150, 76)
        bounds[element_id] = (120 + index * 190, 140, width, height)
    return bounds


def _node_from_xml(child: ET.Element, bounds: tuple[float, float, float, float]) -> BpmnNode:
    x, y, width, height = bounds
    nac = {
        key.rsplit("}", maxsplit=1)[-1]: value
        for key, value in child.attrib.items()
        if key.startswith(f"{{{NAC_NS}}}")
    }
    return BpmnNode(
        id=str(child.attrib.get("id", "")),
        type=child.tag.rsplit("}", maxsplit=1)[-1],
        name=str(child.attrib.get("name", "")),
        nac=nac,
        x=x,
        y=y,
        width=width,
        height=height,
    )


def _flow_from_xml(
    flow: ET.Element,
    root: ET.Element,
    bounds: dict[str, tuple[float, float, float, float]],
) -> BpmnFlow:
    flow_id = str(flow.attrib.get("id", ""))
    waypoints = _edge_waypoints(root, flow_id)
    source = str(flow.attrib.get("sourceRef", ""))
    target = str(flow.attrib.get("targetRef", ""))
    if not waypoints and source in bounds and target in bounds:
        sx, sy, sw, sh = bounds[source]
        tx, ty, _tw, th = bounds[target]
        waypoints = ((sx + sw, sy + sh / 2), (tx, ty + th / 2))
    return BpmnFlow(
        id=flow_id,
        name=str(flow.attrib.get("name", "")),
        source=source,
        target=target,
        waypoints=tuple(waypoints),
    )


def _edge_waypoints(root: ET.Element, flow_id: str) -> tuple[tuple[float, float], ...]:
    for edge in root.findall(".//bpmndi:BPMNEdge", _ns()):
        if edge.attrib.get("bpmnElement") != flow_id:
            continue
        return tuple(
            (
                float(point.attrib.get("x", "0")),
                float(point.attrib.get("y", "0")),
            )
            for point in edge.findall("di:waypoint", _ns())
        )
    return ()


def _render_flow(flow: BpmnFlow) -> str:
    if len(flow.waypoints) < 2:
        return ""
    points = " ".join(f"{x:g},{y:g}" for x, y in flow.waypoints)
    label = ""
    if flow.name:
        mid = flow.waypoints[len(flow.waypoints) // 2]
        label = f'<text class="flow-label" x="{mid[0]:g}" y="{mid[1] - 8:g}">{html.escape(flow.name)}</text>'
    return f'<polyline class="flow" points="{points}" marker-end="url(#arrow)"/>{label}'


def _render_node(node: BpmnNode) -> str:
    label = _render_text(node.name, node.x + node.width / 2, node.y + node.height / 2, max_chars=22)
    badge = _render_badge(node)
    if node.type in {"startEvent", "endEvent"}:
        css_class = "event end" if node.type == "endEvent" else "event start"
        return (
            f'<g class="node {css_class}">'
            f'<circle cx="{node.x + node.width / 2:g}" cy="{node.y + node.height / 2:g}" r="{min(node.width, node.height) / 2:g}"/>'
            f"{label}{badge}</g>"
        )
    if "Gateway" in node.type:
        cx = node.x + node.width / 2
        cy = node.y + node.height / 2
        points = f"{cx:g},{node.y:g} {node.x + node.width:g},{cy:g} {cx:g},{node.y + node.height:g} {node.x:g},{cy:g}"
        return f'<g class="node gateway"><polygon points="{points}"/>{label}{badge}</g>'
    return (
        f'<g class="node task {html.escape(node.type)}">'
        f'<rect x="{node.x:g}" y="{node.y:g}" width="{node.width:g}" height="{node.height:g}" rx="8"/>'
        f"{label}{badge}</g>"
    )


def _render_text(value: str, x: float, y: float, max_chars: int) -> str:
    words = value.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        if len(candidate) > max_chars and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    if not lines:
        lines = [""]
    start_y = y - (len(lines) - 1) * 8
    return "".join(
        f'<text class="node-label" x="{x:g}" y="{start_y + index * 16:g}">{html.escape(line)}</text>'
        for index, line in enumerate(lines[:3])
    )


def _render_badge(node: BpmnNode) -> str:
    role = node.nac.get("role")
    if not role:
        return ""
    return (
        f'<text class="node-badge" x="{node.x + node.width / 2:g}" '
        f'y="{node.y + node.height + 18:g}">{html.escape(role)}</text>'
    )
