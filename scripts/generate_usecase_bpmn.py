from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape


REPO_ROOT = Path(__file__).resolve().parents[1]
USECASES_ROOT = REPO_ROOT / "usecases"
BPMN_ROOT = REPO_ROOT / "bpmn"
BPMN_USECASE_ROOT = BPMN_ROOT / "usecases"

NAC_NS = "https://github.com/ofunk/NaC/bpmn/nac"
TARGET_NS = "https://github.com/ofunk/NaC/bpmn/notariat/usecases"

TOP_LEVEL_MODELS = {"immobilienkaufvertrag"}

REGISTER_SLUGS = {
    "geschaeftsanteilsuebertragung-gmbh",
    "gesellschafterbeschluss-gmbh-ug",
    "handelsregisteranmeldung",
    "online-gmbh-gruendung",
    "vereinsregisteranmeldung",
}
LAND_REGISTER_SLUGS = {
    "bautraegervertrag",
    "grundschuld-hypothekenbestellung",
    "grundstueckskaufvertrag",
    "immobilienkaufvertrag",
    "loeschungsbewilligung-grundbuchloeschung",
    "schenkungsvertrag-uebertragungsvertrag",
    "teilungserklaerung-weg",
    "vollmacht-immobilien-gesellschaftsgeschaefte",
}
COURT_OR_ESTATE_SLUGS = {
    "adoption-familienrechtliche-erklaerungen",
    "erbausschlagung",
    "erbscheinsantrag-nachlass",
    "pflichtteilsverzicht-erbverzicht",
    "testament",
    "testament-erbvertrag",
    "vorsorgevollmacht-patientenverfuegung",
}


@dataclass(frozen=True, slots=True)
class Step:
    element_id: str
    kind: str
    name: str
    role: str
    channel: str
    data_class: str
    approval: str
    evidence: str
    plugin: str | None = None
    local_execution: bool = False


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    generated = generate_all(dry_run=args.check)
    if args.check:
        stale = [path for path, changed in generated if changed]
        if stale:
            print("BPMN usecase models are stale:")
            for path in stale:
                print(f"- {display(path)}")
            return 1
        print("BPMN usecase models are current.")
        return 0
    print(f"Generated {len(generated)} BPMN usecase models.")
    for path, _changed in generated:
        print(f"- {display(path)}")
    return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate governed BPMN models for usecase-local KGs.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check whether generated BPMN files are current without writing them.",
    )
    return parser.parse_args(argv)


def generate_all(dry_run: bool = False) -> list[tuple[Path, bool]]:
    usecases = sorted(path for path in USECASES_ROOT.iterdir() if path.is_dir() and (path / "knowledge-graph.graph.json").is_file())
    BPMN_USECASE_ROOT.mkdir(parents=True, exist_ok=True)
    results: list[tuple[Path, bool]] = []
    for usecase_path in usecases:
        payload = json.loads((usecase_path / "knowledge-graph.graph.json").read_text(encoding="utf-8"))
        slug = usecase_path.name
        title = extract_title(usecase_path, payload)
        steps = build_steps(slug)
        xml = render_bpmn(slug=slug, title=title, steps=steps)
        output_path = BPMN_ROOT / f"{slug}.bpmn" if slug in TOP_LEVEL_MODELS else BPMN_USECASE_ROOT / f"{slug}.bpmn"
        current = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
        changed = current != xml
        if changed and not dry_run:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(xml, encoding="utf-8")
        results.append((output_path, changed))
    return results


def extract_title(usecase_path: Path, payload: dict[str, object]) -> str:
    readme = usecase_path / "README.md"
    if readme.is_file():
        for line in readme.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line.removeprefix("# ").strip()
    raw_title = str(payload.get("title", usecase_path.name))
    return raw_title.removeprefix("NaC Usecase-Wissensgraph: ").strip()


def build_steps(slug: str) -> list[Step]:
    if slug == "online-gmbh-gruendung":
        return with_xnp_check(
            slug,
            [
                start("Vorgang im Online-Verfahren übernehmen", "notary_app;email"),
                user(
                    "Task_SachbearbeitungZuweisen",
                    "Sachbearbeitung und Aktenzeichen zuweisen",
                    "Notariat",
                    "notary_app;internal",
                    "metadata",
                    "human",
                    "required",
                ),
                rule("Task_FormUndRegisterPruefen", "Gründung, Satzung und Registerroute prüfen", "register_portal;internal"),
                user(
                    "Task_UnterlagenAbgleichen",
                    "Gründer, Kapital und Unterlagen abgleichen",
                    "Notariatsfachkraft",
                    "notary_app;email;register_portal",
                    "confidential_placeholder",
                    "human",
                    "required",
                ),
                manual(
                    "Task_VideokonferenzVorbereiten",
                    "Videokonferenz und Signaturfähigkeit vorbereiten",
                    "Notariatsfachkraft",
                    "video;notary_app;qualified_e_signature",
                    "confidential_placeholder",
                    "human",
                    "required",
                ),
                manual(
                    "Task_OnlineBeurkundung",
                    "Online-Beurkundung durchführen",
                    "Notarin/Notar",
                    "video;qualified_e_signature;notary_app",
                    "confidential_placeholder",
                    "four_eyes",
                    "required",
                ),
                send("Task_RegisterEinreichen", "Registerpaket digital einreichen", "xnp_local;register_portal;qualified_e_signature"),
                user("Task_NachweiseNachhalten", "Registerrückläufe und Nachweise nachhalten", "Notariatsfachkraft", "register_portal;email;internal"),
                end("Vorgang abgeschlossen"),
            ],
        )

    if slug == "steuer-aas":
        return [
            start("Steuer-Readiness-Auftrag anlegen", "internal"),
            user("Task_MandatAbgrenzen", "Mandat und Steuerrolle abgrenzen", "Steuerfachkraft", "email;phone;internal"),
            rule("Task_DatenschutzUndAVV", "Datenschutz, AVV und Quellen prüfen", "internal"),
            user("Task_UnterlagenPruefen", "Steuerunterlagen und Fristen prüfen", "Steuerfachkraft", "email;tax_portal;internal"),
            user("Task_EntwurfAbstimmen", "Entwurf und Rückfragen abstimmen", "Steuerfachkraft", "email;phone"),
            manual("Task_FreigabeEinholen", "Fachliche Freigabe einholen", "Notariat", "internal;email", "metadata", "human"),
            send("Task_SteuerkanalAusfuehren", "Steuerkanal oder Antwort ausführen", "tax_portal;email"),
            user("Task_NachweisAblage", "Nachweis und Fristen ablegen", "Steuerfachkraft", "internal"),
            end("Steuer-Readiness abgeschlossen"),
        ]

    steps = [
        start("Vorgang anlegen", intake_channel(slug)),
        user("Task_AuftragAufnehmen", "Auftrag und Beteiligte aufnehmen", "Notariatsfachkraft", intake_channel(slug)),
        rule("Task_FormFristenPruefen", "Zuständigkeit, Form und Fristen prüfen", "internal"),
        user("Task_UnterlagenPruefen", documents_label(slug), "Notariatsfachkraft", documents_channel(slug)),
        user("Task_EntwurfAbstimmen", draft_label(slug), "Notariatsfachkraft", draft_channel(slug)),
        manual("Task_IdentitaetVertretung", "Identität und Vertretung prüfen", "Notarin/Notar", identity_channel(slug)),
        manual("Task_Beurkundung", deed_label(slug), "Notarin/Notar", signature_channel(slug), "confidential_placeholder", "four_eyes"),
        send("Task_EinreichungVersand", submission_label(slug), submission_channel(slug)),
        user("Task_NachweiseNachhalten", "Nachweis und Fristen nachhalten", "Notariatsfachkraft", follow_up_channel(slug)),
        end("Vorgang abgeschlossen"),
    ]
    if requires_xnp_check(slug):
        steps = with_xnp_check(slug, steps)
    return steps


def with_xnp_check(slug: str, steps: list[Step]) -> list[Step]:
    check = Step(
        element_id="Task_XnpArbeitsplatzPruefen",
        kind="serviceTask",
        name="Karte, XNP und Signaturpfad lokal prüfen",
        role="IT-Betrieb",
        channel="xnp_local",
        data_class="metadata",
        approval="none",
        evidence="required",
        plugin="nac-cyberjack-rfid",
        local_execution=True,
    )
    insert_after = 3 if slug == "online-gmbh-gruendung" else 4
    return [*steps[:insert_after], check, *steps[insert_after:]]


def start(name: str, channel: str) -> Step:
    return Step("StartEvent_VorgangAnlegen", "startEvent", name, "Notariat", channel, "metadata", "none", "none")


def end(name: str) -> Step:
    return Step("EndEvent_Abgeschlossen", "endEvent", name, "Notariat", "internal", "metadata", "none", "required")


def user(
    element_id: str,
    name: str,
    role: str,
    channel: str,
    data_class: str = "confidential_placeholder",
    approval: str = "human",
    evidence: str = "required",
) -> Step:
    return Step(element_id, "userTask", name, role, channel, data_class, approval, evidence)


def manual(
    element_id: str,
    name: str,
    role: str,
    channel: str,
    data_class: str = "confidential_placeholder",
    approval: str = "human",
    evidence: str = "required",
) -> Step:
    return Step(element_id, "manualTask", name, role, channel, data_class, approval, evidence)


def rule(element_id: str, name: str, channel: str) -> Step:
    return Step(element_id, "businessRuleTask", name, "Notariat", channel, "metadata", "human", "required")


def send(element_id: str, name: str, channel: str) -> Step:
    return Step(element_id, "sendTask", name, "Notariatsfachkraft", channel, "metadata", "human", "required")


def intake_channel(slug: str) -> str:
    if slug in REGISTER_SLUGS:
        return "email;phone;register_portal"
    if slug in LAND_REGISTER_SLUGS:
        return "personal;email;phone;post"
    if slug in COURT_OR_ESTATE_SLUGS:
        return "personal;email;phone;post;fax"
    return "personal;email;phone;fax"


def documents_channel(slug: str) -> str:
    if slug in REGISTER_SLUGS:
        return "register_portal;email;internal"
    if slug in LAND_REGISTER_SLUGS:
        return "land_register_portal;email;post;internal"
    if slug in COURT_OR_ESTATE_SLUGS:
        return "email;fax;post;court;internal"
    return "email;fax;post;internal"


def draft_channel(slug: str) -> str:
    if slug in REGISTER_SLUGS:
        return "email;register_portal;internal"
    if slug in LAND_REGISTER_SLUGS:
        return "email;post;land_register_portal;internal"
    if slug in COURT_OR_ESTATE_SLUGS:
        return "email;fax;post;personal;internal"
    return "email;fax;post;internal"


def identity_channel(slug: str) -> str:
    if slug in REGISTER_SLUGS:
        return "personal;qualified_e_signature;xnp_local"
    return "personal;paper_signature"


def signature_channel(slug: str) -> str:
    if slug in REGISTER_SLUGS:
        return "paper_signature;qualified_e_signature;xnp_local"
    return "personal;paper_signature"


def submission_channel(slug: str) -> str:
    if slug in REGISTER_SLUGS:
        return "xnp_local;register_portal;qualified_e_signature"
    if slug in LAND_REGISTER_SLUGS:
        return "land_register_portal;post;email"
    if slug in {"testament", "testament-erbvertrag"}:
        return "post;fax;court;ben"
    if slug == "vorsorgevollmacht-patientenverfuegung":
        return "post;fax;email;authority"
    if slug in COURT_OR_ESTATE_SLUGS:
        return "post;fax;court;email"
    return "email;fax;post"


def follow_up_channel(slug: str) -> str:
    if slug in REGISTER_SLUGS:
        return "register_portal;email;internal"
    if slug in LAND_REGISTER_SLUGS:
        return "land_register_portal;email;internal"
    if slug in COURT_OR_ESTATE_SLUGS:
        return "court;email;internal"
    return "email;internal"


def documents_label(slug: str) -> str:
    if slug in REGISTER_SLUGS:
        return "Registerstand und Anlagen prüfen"
    if slug in LAND_REGISTER_SLUGS:
        return "Grundbuchstand und Unterlagen prüfen"
    if slug in {"testament", "testament-erbvertrag"}:
        return "Verfügungen und Verwahrungsweg prüfen"
    if slug == "erbscheinsantrag-nachlass":
        return "Nachlassangaben und Nachweise prüfen"
    return "Unterlagen und Nachweise prüfen"


def draft_label(slug: str) -> str:
    if slug in REGISTER_SLUGS:
        return "Anmeldung und Anlagen entwerfen"
    if slug in LAND_REGISTER_SLUGS:
        return "Urkundenentwurf und Vollzugshinweise abstimmen"
    return "Entwurf und Abstimmung erstellen"


def deed_label(slug: str) -> str:
    if slug in REGISTER_SLUGS:
        return "Beglaubigung oder Beurkundung durchführen"
    if slug == "unterschriftsbeglaubigung":
        return "Unterschrift öffentlich beglaubigen"
    return "Beurkundung oder Erklärung durchführen"


def submission_label(slug: str) -> str:
    if slug in REGISTER_SLUGS:
        return "Registereinreichung ausführen"
    if slug in LAND_REGISTER_SLUGS:
        return "Vollzug und Grundbuchkommunikation ausführen"
    if slug in {"testament", "testament-erbvertrag"}:
        return "Verwahrung und Benachrichtigung ausführen"
    if slug == "vorsorgevollmacht-patientenverfuegung":
        return "Registrierung oder Versand ausführen"
    return "Einreichung oder Versand ausführen"


def requires_xnp_check(slug: str) -> bool:
    return slug in REGISTER_SLUGS or slug in {
        "bautraegervertrag",
        "grundschuld-hypothekenbestellung",
        "immobilienkaufvertrag",
        "loeschungsbewilligung-grundbuchloeschung",
        "teilungserklaerung-weg",
        "vollmacht-immobilien-gesellschaftsgeschaefte",
    }


def render_bpmn(slug: str, title: str, steps: list[Step]) -> str:
    definitions_id = f"Definitions_{safe_id(slug)}"
    process_id = f"Process_{safe_id(slug)}"
    diagram_id = f"BPMNDiagram_{safe_id(slug)}"
    plane_id = f"BPMNPlane_{safe_id(slug)}"
    flows = [(f"Flow_{index:02d}", steps[index].element_id, steps[index + 1].element_id) for index in range(len(steps) - 1)]
    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<bpmn:definitions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
        '                  xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"',
        '                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"',
        '                  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"',
        '                  xmlns:di="http://www.omg.org/spec/DD/20100524/DI"',
        f'                  xmlns:nac="{NAC_NS}"',
        f'                  id="{definitions_id}"',
        f'                  targetNamespace="{TARGET_NS}">',
        f'  <bpmn:process id="{process_id}"',
        f'                name="{xattr(title)}"',
        '                isExecutable="false"',
        '                nac:profile="nac-bpmn/v0.1"',
        '                nac:owner="funktion8 / ofunk"',
        '                nac:binding="Git Pull Request">',
        "    <bpmn:documentation>Generiert aus usecase-lokalem KG, BNotK-XNP-Onlinehilfe fuer lokale XNP-Schnittstelle und BNotK-Onlineverfahren-Onlinehilfe fuer Vorgangseingang/Videokonferenz. Keine Mandatswerte im Repo.</bpmn:documentation>",
    ]
    for index, step in enumerate(steps):
        incoming = flows[index - 1][0] if index > 0 else None
        outgoing = flows[index][0] if index < len(flows) else None
        xml.extend(render_step(step, slug, incoming, outgoing))
    for flow_id, source, target in flows:
        xml.append(f'    <bpmn:sequenceFlow id="{flow_id}" sourceRef="{source}" targetRef="{target}"/>')
    xml.extend(
        [
            "  </bpmn:process>",
            f'  <bpmndi:BPMNDiagram id="{diagram_id}">',
            f'    <bpmndi:BPMNPlane id="{plane_id}" bpmnElement="{process_id}">',
        ]
    )
    layout = step_layout(steps)
    for step in steps:
        x, y, width, height = layout[step.element_id]
        xml.extend(
            [
                f'      <bpmndi:BPMNShape id="Shape_{step.element_id}" bpmnElement="{step.element_id}">',
                f'        <dc:Bounds x="{x}" y="{y}" width="{width}" height="{height}"/>',
                "      </bpmndi:BPMNShape>",
            ]
        )
    for flow_id, source, target in flows:
        sx, sy, sw, sh = layout[source]
        tx, ty, _tw, th = layout[target]
        xml.extend(
            [
                f'      <bpmndi:BPMNEdge id="Edge_{flow_id}" bpmnElement="{flow_id}">',
                f'        <di:waypoint x="{sx + sw}" y="{sy + sh // 2}"/>',
                f'        <di:waypoint x="{tx}" y="{ty + th // 2}"/>',
                "      </bpmndi:BPMNEdge>",
            ]
        )
    xml.extend(
        [
            "    </bpmndi:BPMNPlane>",
            "  </bpmndi:BPMNDiagram>",
            "</bpmn:definitions>",
            "",
        ]
    )
    return "\n".join(xml)


def render_step(step: Step, slug: str, incoming: str | None, outgoing: str | None) -> list[str]:
    attrs = [
        f'id="{step.element_id}"',
        f'name="{xattr(step.name)}"',
        f'nac:role="{xattr(step.role)}"',
        f'nac:channel="{xattr(step.channel)}"',
        f'nac:dataClass="{step.data_class}"',
        f'nac:approval="{step.approval}"',
        f'nac:evidence="{step.evidence}"',
    ]
    if step.plugin:
        attrs.append(f'nac:plugin="{xattr(step.plugin)}"')
    if step.local_execution:
        attrs.append('nac:localExecution="true"')
    attrs.append(f'nac:kgRef="{slug}"')
    lines = [f"    <bpmn:{step.kind} {attrs[0]}"]
    for attr in attrs[1:]:
        lines.append(f"                     {attr}")
    if not incoming and not outgoing:
        lines[-1] += "/>"
        return lines
    lines[-1] += ">"
    if incoming:
        lines.append(f"      <bpmn:incoming>{incoming}</bpmn:incoming>")
    if outgoing:
        lines.append(f"      <bpmn:outgoing>{outgoing}</bpmn:outgoing>")
    lines.append(f"    </bpmn:{step.kind}>")
    return lines


def step_layout(steps: list[Step]) -> dict[str, tuple[int, int, int, int]]:
    bounds: dict[str, tuple[int, int, int, int]] = {}
    for index, step in enumerate(steps):
        if step.kind in {"startEvent", "endEvent"}:
            bounds[step.element_id] = (130 + index * 215, 160, 36, 36)
        else:
            bounds[step.element_id] = (115 + index * 215, 138, 160, 80)
    return bounds


def safe_id(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:6]
    return f"{normalized}_{digest}" if normalized and normalized[0].isdigit() else normalized or digest


def xattr(value: str) -> str:
    return escape(value, {'"': "&quot;"})


def display(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
