from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = REPO_ROOT / "policies" / "graft-context-layer-policy.yaml"
SETTINGS_PATH = REPO_ROOT / ".pi" / "settings.json"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
STARTUP_PATH = REPO_ROOT / "scripts" / "startup_check.py"
QUALITY_GATE_PATH = REPO_ROOT / "scripts" / "quality_gate.py"
SKILL_PATH = REPO_ROOT / "workflows" / "skills" / "graft-context" / "SKILL.md"
CONTRACT_PATH = (
    REPO_ROOT / "workflows" / "verification-contracts" / "graft-context-layer.verification.json"
)

GRAFT_SKILL_ENTRY = "workflows/skills/graft-context"
AGENTS_MARKER = "graft-context-layer-policy.yaml"
STARTUP_MARKER = "graft"
QUALITY_GATE_MARKER = "validate_graft_context_layer.py"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _validate_policy() -> list[str]:
    if not POLICY_PATH.is_file():
        return [f"Policy fehlt: {POLICY_PATH.relative_to(REPO_ROOT)}"]
    text = _read_text(POLICY_PATH)
    errors: list[str] = []
    if "status: mandatory" not in text:
        errors.append("policies/graft-context-layer-policy.yaml: status muss 'mandatory' sein")
    if "tier_1_structural" not in text:
        errors.append("policies/graft-context-layer-policy.yaml: Tier 1 (structural) fehlt")
    if "graft check" not in text:
        errors.append("policies/graft-context-layer-policy.yaml: 'graft check' Quality-Gate-Check fehlt")
    # pi integration must NOT declare a built-in MCP server (pi has no MCP support).
    # The policy may mention 'mcpServers' only to state that pi has no such field.
    if "method: mcp_server" in text or "mcpServers:" in text:
        errors.append(
            "policies/graft-context-layer-policy.yaml: pi-Integration darf keinen "
            "eingebauten MCP-Server behaupten (pi hat keinen MCP-Support)."
        )
    return errors


def _validate_settings() -> list[str]:
    if not SETTINGS_PATH.is_file():
        return [f".pi/settings.json fehlt"]
    text = _read_text(SETTINGS_PATH)
    if GRAFT_SKILL_ENTRY not in text:
        errors_msg = (
            ".pi/settings.json: Graft-Skill-Eintrag fehlt "
            f"(skills muss '{GRAFT_SKILL_ENTRY}' enthalten)"
        )
        return [errors_msg]
    if "mcpServers" in text:
        return [
            ".pi/settings.json: 'mcpServers' ist kein unterstuetzter pi-Settings-Schluessel; "
            "Graft wird in pi ueber die CLI/den Skill angebunden, nicht ueber MCP."
        ]
    return []


def _validate_agents_block() -> list[str]:
    if not AGENTS_PATH.is_file():
        return ["AGENTS.md fehlt"]
    text = _read_text(AGENTS_PATH)
    if AGENTS_MARKER not in text:
        return [
            "AGENTS.md: Graft-Context-Layer-Block fehlt "
            f"(Verweis auf {AGENTS_MARKER} nicht gefunden)"
        ]
    return []


def _validate_startup() -> list[str]:
    if not STARTUP_PATH.is_file():
        return ["scripts/startup_check.py fehlt"]
    text = _read_text(STARTUP_PATH)
    if STARTUP_MARKER not in text:
        return ["scripts/startup_check.py: graft build/integration fehlt"]
    return []


def _validate_quality_gate() -> list[str]:
    if not QUALITY_GATE_PATH.is_file():
        return ["scripts/quality_gate.py fehlt"]
    text = _read_text(QUALITY_GATE_PATH)
    if QUALITY_GATE_MARKER not in text:
        return [
            "scripts/quality_gate.py: Graft-Validator "
            f"({QUALITY_GATE_MARKER}) ist nicht im strict-Profil gebunden"
        ]
    return []


def _validate_skill() -> list[str]:
    if not SKILL_PATH.is_file():
        return [f"pi-Skill fehlt: {SKILL_PATH.relative_to(REPO_ROOT)}"]
    text = _read_text(SKILL_PATH)
    errors: list[str] = []
    if "name: graft-context" not in text:
        errors.append("workflows/skills/graft-context/SKILL.md: Frontmatter 'name: graft-context' fehlt")
    if "graft build" not in text:
        errors.append("workflows/skills/graft-context/SKILL.md: 'graft build' Anleitung fehlt")
    if "graft check" not in text:
        errors.append("workflows/skills/graft-context/SKILL.md: 'graft check' Anleitung fehlt")
    return errors


def _validate_contract() -> list[str]:
    if not CONTRACT_PATH.is_file():
        return [f"Verification Contract fehlt: {CONTRACT_PATH.relative_to(REPO_ROOT)}"]
    text = _read_text(CONTRACT_PATH)
    errors: list[str] = []
    if "nac.verification-contract/v0.1" not in text:
        errors.append("graft-context-layer.verification.json: schema_version muss nac.verification-contract/v0.1 sein")
    if "validate_graft_context_layer.py" not in text:
        errors.append("graft-context-layer.verification.json: Validator-Check fehlt")
    return errors


def _validate_graft_check() -> list[str]:
    """Run `graft check` (deterministic, $0, no LLM) to detect graph drift."""
    if shutil.which("graft") is None:
        return [
            "graft-CLI nicht installiert; bitte 'npm i -g @nanonets/graft' ausfuehren, "
            "damit der deterministische Drift-Check (Tier 1) laeuft."
        ]
    result = subprocess.run(
        ["graft", "check"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        output = "\n".join(part.strip() for part in [result.stdout, result.stderr] if part and part.strip())
        return [
            "graft check fehlgeschlagen (Graph-Drift erkannt); bitte 'graft build' ausfuehren:\n"
            + output
        ]
    return []


def validate() -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_policy())
    errors.extend(_validate_settings())
    errors.extend(_validate_agents_block())
    errors.extend(_validate_startup())
    errors.extend(_validate_quality_gate())
    errors.extend(_validate_skill())
    errors.extend(_validate_contract())
    errors.extend(_validate_graft_check())
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("STATUS: FAILED")
        for entry in errors:
            print(f"ERROR: {entry}")
        return 1
    print("STATUS: PASSED")
    print("OK: Graft Context Layer (Tier 1) ist verdrahtet und der Code-Graph ist frisch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
