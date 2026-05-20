from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
MARKETPLACE_NAME = "nac-regulierung"
REQUIRED_PLUGIN_FIELDS = ["name", "version", "description", "author", "homepage", "repository", "license", "skills", "interface"]
REQUIRED_INTERFACE_FIELDS = ["displayName", "shortDescription", "longDescription", "developerName", "category", "capabilities", "defaultPrompt", "brandColor"]
REQUIRED_MARKETPLACE_ORDER = ["nac-cyberjack-rfid", "nac-bnotk-xnp", "nac-handelsregister"]
REQUIRED_PLUGIN_LICENSE = "AGPL-3.0-or-later"
REQUIRED_DEVELOPER_NAME = "funktion8 / ofunk"
MAX_DISPLAY_NAME_CHARS = 22
MAX_SHORT_DESCRIPTION_CHARS = 64
MIN_PLUGIN_ASSET_PX = 64
GERMAN_UX_MARKERS = (
    " für ",
    " und ",
    " ohne ",
    " mit ",
    "lokal",
    "erstelle",
    "plane",
    "erzeuge",
    "prüf",
    "begleit",
    "bereit",
    "nachweis",
    "betriebsdrift",
    "arbeitsablauf",
    "schutzplanken",
    "regulier",
    "funktion8",
    "notar",
    "handelsregister",
    "register",
    "grundbuch",
    "zertifikat",
    "karte",
    "karten",
    "postfach",
    "elster",
    "oci",
)
ENGLISH_UX_MARKERS = (
    " gate",
    " evidence",
    " readiness",
    " workflow",
    " companion",
    " guardrail",
    " regulated-industry",
    " local ",
    " shared ",
    " create ",
    " prepare ",
    " review ",
    " inspect ",
    " check ",
    " run ",
)
PLUGIN_UX_FIELDS = ("description", "displayName", "shortDescription", "longDescription", "category")


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


def normalized_text(value: str) -> str:
    return f" {value.lower().replace('-', ' ')} "


def looks_german(value: str) -> bool:
    text = normalized_text(value)
    return any(marker in text for marker in GERMAN_UX_MARKERS)


def contains_english_ux_marker(value: str) -> str | None:
    text = normalized_text(value)
    for marker in ENGLISH_UX_MARKERS:
        if marker in text:
            return marker.strip()
    return None


def validate_german_plugin_ux(name: str, label: str, value: object) -> list[str]:
    errors: list[str] = []
    values = value if isinstance(value, list) else [value]
    for item in values:
        if not isinstance(item, str):
            errors.append(f"{name}: {label} must be a string or list of strings")
            continue
        if not looks_german(item):
            errors.append(f"{name}: {label} must be German-led human-facing text")
        marker = contains_english_ux_marker(item)
        if marker:
            errors.append(f"{name}: {label} contains English UX marker: {marker}")
    return errors


def png_dimensions(path: Path) -> tuple[int, int] | None:
    header = path.read_bytes()[:24]
    if not header.startswith(b"\x89PNG\r\n\x1a\n") or len(header) < 24:
        return None
    return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")


def validate_plugin_asset(name: str, asset_path: Path) -> list[str]:
    errors: list[str] = []
    if not asset_path.exists():
        return [f"{name}: missing {asset_path.relative_to(REPO_ROOT).as_posix()}"]
    dimensions = png_dimensions(asset_path)
    rel_path = asset_path.relative_to(REPO_ROOT).as_posix()
    if dimensions is None:
        errors.append(f"{name}: {rel_path} must be a PNG image")
    elif min(dimensions) < MIN_PLUGIN_ASSET_PX:
        errors.append(f"{name}: {rel_path} must be at least {MIN_PLUGIN_ASSET_PX}px on each side")
    if asset_path.stat().st_size < 256:
        errors.append(f"{name}: {rel_path} must not be a blank placeholder asset")
    return errors


def validate() -> list[str]:
    errors: list[str] = []
    if not MARKETPLACE.exists():
        return [f"Missing marketplace: {MARKETPLACE.relative_to(REPO_ROOT)}"]

    marketplace = load_json(MARKETPLACE)
    if contains_todo(marketplace):
        errors.append("Marketplace contains TODO placeholders")
    if marketplace.get("name") != MARKETPLACE_NAME:
        errors.append(f"Marketplace name must be {MARKETPLACE_NAME}")
    marketplace_display = marketplace.get("interface", {}).get("displayName")
    errors.extend(
        validate_german_plugin_ux(
            "marketplace",
            "interface.displayName",
            marketplace_display,
        )
    )

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
        errors.extend(validate_german_plugin_ux(name, "marketplace.category", entry.get("category")))

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
        if manifest.get("license") != REQUIRED_PLUGIN_LICENSE:
            errors.append(f"{name}: manifest license must be {REQUIRED_PLUGIN_LICENSE}")
        author = manifest.get("author", {})
        if not isinstance(author, dict) or author.get("name") != REQUIRED_DEVELOPER_NAME:
            errors.append(f"{name}: author.name must be {REQUIRED_DEVELOPER_NAME}")
        interface = manifest.get("interface", {})
        for field in REQUIRED_INTERFACE_FIELDS:
            if field not in interface:
                errors.append(f"{name}: missing interface field {field}")
        if interface.get("developerName") != REQUIRED_DEVELOPER_NAME:
            errors.append(f"{name}: interface.developerName must be {REQUIRED_DEVELOPER_NAME}")
        errors.extend(validate_german_plugin_ux(name, "description", manifest.get("description")))
        for field in PLUGIN_UX_FIELDS[1:]:
            errors.extend(validate_german_plugin_ux(name, f"interface.{field}", interface.get(field)))
        display_name = interface.get("displayName")
        if isinstance(display_name, str) and display_name.startswith("NaC "):
            errors.append(f"{name}: interface.displayName must omit the NaC prefix because the marketplace already names NaC")
        if isinstance(display_name, str) and len(display_name) > MAX_DISPLAY_NAME_CHARS:
            errors.append(f"{name}: interface.displayName must be <= {MAX_DISPLAY_NAME_CHARS} chars for card readability")
        short_description = interface.get("shortDescription")
        if isinstance(short_description, str) and len(short_description) > MAX_SHORT_DESCRIPTION_CHARS:
            errors.append(
                f"{name}: interface.shortDescription must be <= {MAX_SHORT_DESCRIPTION_CHARS} chars for card readability"
            )
        readme_path = plugin_root / "README.md"
        if not readme_path.exists():
            errors.append(f"{name}: missing README.md")
        elif isinstance(display_name, str):
            expected_heading = f"# {display_name}"
            first_line = readme_path.read_text(encoding="utf-8").splitlines()[0:1]
            if first_line != [expected_heading]:
                errors.append(f"{name}: README.md must start with {expected_heading}")
        prompts = interface.get("defaultPrompt", [])
        if not isinstance(prompts, list) or len(prompts) > 3:
            errors.append(f"{name}: defaultPrompt must contain at most three entries")
        for prompt in prompts:
            if not isinstance(prompt, str) or len(prompt) > 128:
                errors.append(f"{name}: defaultPrompt entries must be strings <= 128 chars")
        errors.extend(validate_german_plugin_ux(name, "interface.defaultPrompt", prompts))

        skills_dir = plugin_root / "skills"
        if not any(skills_dir.glob("*/SKILL.md")):
            errors.append(f"{name}: missing skills/<skill>/SKILL.md")
        if not (plugin_root / "contracts" / "security-boundary.json").exists():
            errors.append(f"{name}: missing contracts/security-boundary.json")
        for asset in ["assets/icon.png", "assets/logo.png"]:
            errors.extend(validate_plugin_asset(name, plugin_root / asset))

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
