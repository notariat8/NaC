from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
REQUIRED_PLUGIN_FIELDS = ["name", "version", "description", "author", "homepage", "repository", "license", "skills", "interface"]
REQUIRED_INTERFACE_FIELDS = ["displayName", "shortDescription", "longDescription", "developerName", "category", "capabilities", "defaultPrompt", "brandColor"]
REQUIRED_MARKETPLACE_ORDER = ["oac-cyberjack-rfid", "oac-bnotk-xnp", "oac-handelsregister"]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def contains_todo(value: object) -> bool:
    if isinstance(value, str):
        return "[TODO" in value
    if isinstance(value, list):
        return any(contains_todo(item) for item in value)
    if isinstance(value, dict):
        return any(contains_todo(item) for item in value.values())
    return False


def validate() -> list[str]:
    errors: list[str] = []
    if not MARKETPLACE.exists():
        return [f"Missing marketplace: {MARKETPLACE.relative_to(REPO_ROOT)}"]

    marketplace = load_json(MARKETPLACE)
    if contains_todo(marketplace):
        errors.append("Marketplace contains TODO placeholders")
    if marketplace.get("name") != "oac-regulated-industry":
        errors.append("Marketplace name must be oac-regulated-industry")

    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        errors.append("Marketplace must contain at least one plugin entry")
        return errors

    seen: set[str] = set()
    plugin_names: list[str] = []
    for entry in plugins:
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            errors.append("Marketplace entry missing name")
            continue
        plugin_names.append(name)
        if name in seen:
            errors.append(f"Duplicate marketplace plugin entry: {name}")
        seen.add(name)

        source = entry.get("source", {})
        if source.get("source") != "local":
            errors.append(f"{name}: source must be local")
        expected_path = f"./plugins/{name}"
        if source.get("path") != expected_path:
            errors.append(f"{name}: source.path must be {expected_path}")
        policy = entry.get("policy", {})
        if policy.get("installation") != "AVAILABLE":
            errors.append(f"{name}: installation policy must be AVAILABLE")
        if policy.get("authentication") != "ON_INSTALL":
            errors.append(f"{name}: authentication policy must be ON_INSTALL")

        plugin_root = REPO_ROOT / "plugins" / name
        manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
        if not manifest_path.exists():
            errors.append(f"{name}: missing .codex-plugin/plugin.json")
            continue
        manifest = load_json(manifest_path)
        if contains_todo(manifest):
            errors.append(f"{name}: manifest contains TODO placeholders")
        if manifest.get("name") != name:
            errors.append(f"{name}: manifest name mismatch")
        for field in REQUIRED_PLUGIN_FIELDS:
            if field not in manifest:
                errors.append(f"{name}: missing manifest field {field}")
        interface = manifest.get("interface", {})
        for field in REQUIRED_INTERFACE_FIELDS:
            if field not in interface:
                errors.append(f"{name}: missing interface field {field}")
        prompts = interface.get("defaultPrompt", [])
        if not isinstance(prompts, list) or len(prompts) > 3:
            errors.append(f"{name}: defaultPrompt must contain at most three entries")
        for prompt in prompts:
            if not isinstance(prompt, str) or len(prompt) > 128:
                errors.append(f"{name}: defaultPrompt entries must be strings <= 128 chars")

        skills_dir = plugin_root / "skills"
        if not any(skills_dir.glob("*/SKILL.md")):
            errors.append(f"{name}: missing skills/<skill>/SKILL.md")
        if not (plugin_root / "contracts" / "security-boundary.json").exists():
            errors.append(f"{name}: missing contracts/security-boundary.json")
        for asset in ["assets/icon.png", "assets/logo.png"]:
            if not (plugin_root / asset).exists():
                errors.append(f"{name}: missing {asset}")

    for before, after in zip(REQUIRED_MARKETPLACE_ORDER, REQUIRED_MARKETPLACE_ORDER[1:]):
        if before in plugin_names and after in plugin_names and plugin_names.index(before) > plugin_names.index(after):
            errors.append(f"Marketplace order must place {before} before {after}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Plugin validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Plugin validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
