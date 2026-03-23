from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
FLOW_FILE = REPO_ROOT / "policies" / "onboarding-flow.json"
DIAGRAMS_FILE = REPO_ROOT / "policies" / "onboarding-diagrams.json"
IDENTITY_FILE = REPO_ROOT / "policies" / "github-identity-registry.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stateful onboarding wizard for Business-OS.")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="Start or continue an onboarding session.")
    start.add_argument("--session", type=Path, required=True, help="Path to session JSON.")
    start.add_argument("--actor-name", required=True, help="Name of current contributor.")
    start.add_argument("--actor-role", required=True, help="Role of current contributor.")
    start.add_argument("--github-login", required=True, help="GitHub login of current contributor.")
    start.add_argument("--mode", choices=["founding", "existing"], help="Optional onboarding mode.")
    start.add_argument(
        "--answers-file",
        type=Path,
        help="Optional JSON file with non-interactive answers by question_id.",
    )

    status = sub.add_parser("status", help="Show session progress.")
    status.add_argument("--session", type=Path, required=True)

    export_plan = sub.add_parser("export-plan", help="Export current onboarding plan.")
    export_plan.add_argument("--session", type=Path, required=True)
    export_plan.add_argument("--output", type=Path, required=True)

    finalize = sub.add_parser("finalize", help="Create immutable onboarding bundle.")
    finalize.add_argument("--session", type=Path, required=True)
    finalize.add_argument("--output-dir", type=Path, required=True)
    finalize.add_argument("--export-pdf", action="store_true")

    return parser.parse_args()


def init_session(mode: str | None) -> dict[str, Any]:
    return {
        "session_version": 1,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "mode": mode or "",
        "finalized": False,
        "answers": [],
    }


def load_session(path: Path, mode: str | None) -> dict[str, Any]:
    if path.exists():
        return read_json(path)
    return init_session(mode)


def answered_ids(session: dict[str, Any]) -> set[str]:
    return {entry["question_id"] for entry in session.get("answers", [])}


def find_question(flow: dict[str, Any], question_id: str) -> dict[str, Any] | None:
    for question in flow["questions"]:
        if question["id"] == question_id:
            return question
    return None


def normalize_role(identity_registry: dict[str, Any], role: str) -> str:
    aliases = identity_registry.get("role_aliases", {})
    role_key = role.strip().lower()
    return aliases.get(role_key, role_key)


def resolve_identity(identity_registry: dict[str, Any], github_login: str) -> dict[str, Any] | None:
    login = github_login.strip().lower()
    for entry in identity_registry.get("users", []):
        if str(entry.get("github_login", "")).lower() == login:
            return entry
    return None


def print_question_diagram(diagrams: dict[str, Any], question_id: str) -> None:
    question_diagram = diagrams.get("questions", {}).get(question_id)
    if not question_diagram:
        return
    bpmn_ref = question_diagram.get("bpmn_ref", "")
    mermaid_text = question_diagram.get("mermaid", "")
    if bpmn_ref:
        print(f"BPMN-Referenz: {bpmn_ref}")
    if mermaid_text:
        print("Mermaid-Uebersicht:")
        print(mermaid_text)


def run_start(
    session_path: Path,
    actor_name: str,
    actor_role: str,
    github_login: str,
    mode: str | None,
    answers_file: Path | None,
) -> int:
    flow = read_json(FLOW_FILE)
    diagrams = read_json(DIAGRAMS_FILE)
    identity_registry = read_json(IDENTITY_FILE)
    session = load_session(session_path, mode)

    if session.get("finalized", False):
        print("Session ist bereits finalisiert und schreibgeschuetzt.")
        return 1

    identity = resolve_identity(identity_registry, github_login)
    if not identity:
        print(f"GitHub Nutzer {github_login!r} ist nicht im Identity-Register.")
        return 1
    if not identity.get("active", False):
        print(f"GitHub Nutzer {github_login!r} ist im Identity-Register nicht aktiv.")
        return 1

    normalized_actor_role = normalize_role(identity_registry, actor_role)
    identity_role = normalize_role(identity_registry, str(identity.get("technical_role_id", "")))
    if normalized_actor_role != identity_role:
        print(
            f"Rollenkonflikt: angegeben {normalized_actor_role!r}, "
            f"registriert fuer {github_login!r} ist {identity_role!r}."
        )
        return 1

    if mode:
        session["mode"] = mode

    if not session.get("mode"):
        mode_input = input("Modus (founding/existing): ").strip().lower()
        if mode_input not in {"founding", "existing"}:
            print("Ungueltiger Modus.")
            return 1
        session["mode"] = mode_input

    current_mode = session["mode"]
    existing_answers = answered_ids(session)

    questions = [
        q
        for q in flow["questions"]
        if current_mode in q.get("required_for_modes", ["founding", "existing"])
    ]

    non_interactive_answers: dict[str, str] = {}
    if answers_file:
        non_interactive_answers = read_json(answers_file)

    for question in questions:
        if question["id"] in existing_answers:
            continue

        print(f"\n[{question['phase']}] {question['prompt']}")
        print_question_diagram(diagrams, question["id"])
        options = question.get("options", [])
        if options:
            print("Optionen: " + ", ".join(options))

        required_roles = [
            normalize_role(identity_registry, role) for role in question.get("required_roles", [])
        ]
        if required_roles and normalized_actor_role not in required_roles:
            print(
                "Rolle nicht berechtigt fuer diese Frage. "
                f"Erforderlich: {', '.join(required_roles)} | aktuell: {normalized_actor_role}"
            )
            continue

        if question["id"] in non_interactive_answers:
            answer = str(non_interactive_answers[question["id"]]).strip()
            print(f"Antwort (non-interactive): {answer}")
        else:
            answer = input("Antwort: ").strip()
        if not answer:
            print("Leere Antwort uebersprungen.")
            continue

        if options and answer not in options:
            print("Antwort nicht in Optionen, wird trotzdem als Freitext gespeichert.")

        session["answers"].append(
            {
                "question_id": question["id"],
                "answer": answer,
                "actor_name": actor_name,
                "actor_role": normalized_actor_role,
                "github_login": github_login,
                "required_roles_for_question": question.get("required_roles", []),
                "bpmn_ref": diagrams.get("questions", {}).get(question["id"], {}).get("bpmn_ref", ""),
                "timestamp": now_iso(),
            }
        )
        session["updated_at"] = now_iso()
        write_json(session_path, session)
        print(f"Gespeichert: {question['id']}")

    print("\nOnboarding-Session gespeichert.")
    print(f"Datei: {session_path}")
    return 0


def run_status(session_path: Path) -> int:
    if not session_path.exists():
        print("Session-Datei nicht gefunden.")
        return 1

    flow = read_json(FLOW_FILE)
    session = read_json(session_path)
    mode = session.get("mode", "")
    answered = answered_ids(session)

    questions = [
        q
        for q in flow["questions"]
        if mode in q.get("required_for_modes", ["founding", "existing"])
    ]
    total = len(questions)
    done = sum(1 for q in questions if q["id"] in answered)

    print(f"Modus: {mode}")
    print(f"Fortschritt: {done}/{total}")
    print(f"Finalisiert: {session.get('finalized', False)}")

    if done < total:
        print("Offene Fragen:")
        for q in questions:
            if q["id"] not in answered:
                print(f"- {q['id']}: {q['prompt']}")
    else:
        print("Alle Fragen in diesem Modus beantwortet.")
    return 0


def run_export_plan(session_path: Path, output_path: Path) -> int:
    if not session_path.exists():
        print("Session-Datei nicht gefunden.")
        return 1

    flow = read_json(FLOW_FILE)
    diagrams = read_json(DIAGRAMS_FILE)
    session = read_json(session_path)
    answers_by_id = {entry["question_id"]: entry for entry in session.get("answers", [])}
    mode = session.get("mode", "unbekannt")

    lines: list[str] = []
    lines.append("# Onboarding Plan (Export)")
    lines.append("")
    lines.append(f"- Modus: `{mode}`")
    lines.append(f"- Letzte Aktualisierung: `{session.get('updated_at', '')}`")
    lines.append("")

    for phase in flow["phases"]:
        lines.append(f"## {phase['title']}")
        lines.append("")
        phase_questions = [q for q in flow["questions"] if q["phase"] == phase["id"]]
        for q in phase_questions:
            if mode not in q.get("required_for_modes", ["founding", "existing"]):
                continue
            answer = answers_by_id.get(q["id"])
            if answer:
                lines.append(f"- **{q['prompt']}**")
                lines.append(f"  - Antwort: {answer['answer']}")
                lines.append(
                    f"  - Rolle: {answer['actor_role']} ({answer['actor_name']}, GitHub: {answer.get('github_login', 'n/a')})"
                )
                bpmn_ref = diagrams.get("questions", {}).get(q["id"], {}).get("bpmn_ref", "")
                mermaid = diagrams.get("questions", {}).get(q["id"], {}).get("mermaid", "")
                if bpmn_ref:
                    lines.append(f"  - BPMN-Referenz: `{bpmn_ref}`")
                if mermaid:
                    lines.append("")
                    lines.append("```mermaid")
                    lines.append(mermaid)
                    lines.append("```")
            else:
                lines.append(f"- **{q['prompt']}**")
                lines.append("  - Antwort: OFFEN")
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Plan exportiert nach: {output_path}")
    return 0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(8192)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def run_finalize(session_path: Path, output_dir: Path, export_pdf: bool) -> int:
    if not session_path.exists():
        print("Session-Datei nicht gefunden.")
        return 1

    session = read_json(session_path)
    if session.get("finalized", False):
        print("Session ist bereits finalisiert.")
        return 1

    bundle_dir = output_dir / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bundle_dir.mkdir(parents=True, exist_ok=True)

    session_copy = bundle_dir / "session.json"
    plan_md = bundle_dir / "onboarding-plan.md"
    write_json(session_copy, session)
    export_rc = run_export_plan(session_path, plan_md)
    if export_rc != 0:
        return export_rc

    manifest = {
        "generated_at": now_iso(),
        "files": [
            {
                "path": str(session_copy.name),
                "sha256": sha256_file(session_copy),
            },
            {
                "path": str(plan_md.name),
                "sha256": sha256_file(plan_md),
            },
        ],
    }

    if export_pdf:
        pdf_path = bundle_dir / "onboarding-plan.pdf"
        cmd = ["pandoc", str(plan_md), "-o", str(pdf_path)]
        result = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
        if result.returncode == 0 and pdf_path.exists():
            manifest["files"].append(
                {
                    "path": str(pdf_path.name),
                    "sha256": sha256_file(pdf_path),
                }
            )
        else:
            print("WARN: PDF-Export fehlgeschlagen (pandoc nicht verfuegbar oder Fehler).")

    manifest_path = bundle_dir / "manifest.sha256.json"
    write_json(manifest_path, manifest)

    session["finalized"] = True
    session["finalized_at"] = now_iso()
    session["final_bundle"] = str(bundle_dir)
    write_json(session_path, session)

    print(f"Finales Audit-Bundle erstellt: {bundle_dir}")
    print("Session wurde finalisiert (schreibgeschuetzt).")
    return 0


def main() -> int:
    args = parse_args()
    if args.command == "start":
        return run_start(
            args.session,
            args.actor_name,
            args.actor_role,
            args.github_login,
            args.mode,
            args.answers_file,
        )
    if args.command == "status":
        return run_status(args.session)
    if args.command == "export-plan":
        return run_export_plan(args.session, args.output)
    if args.command == "finalize":
        return run_finalize(args.session, args.output_dir, args.export_pdf)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
