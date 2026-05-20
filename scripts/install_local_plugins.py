from __future__ import annotations

import argparse
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
INSTALL_MARKETPLACE = Path(".agents") / "plugins" / "marketplace.json"
INSTALL_PLUGINS = Path("plugins")
MODES = ("dry-run", "link", "copy")


@dataclass(frozen=True)
class PluginEntry:
    name: str
    source_path: Path
    source_root: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mirror repo-local NaC Codex plugins into a home-local plugin root."
    )
    parser.add_argument(
        "--mode",
        choices=MODES,
        default="dry-run",
        help="dry-run only reports actions; link creates symlinks; copy copies plugin folders.",
    )
    parser.add_argument(
        "--target-root",
        type=Path,
        default=default_target_root(),
        help="Home-local plugin root. Defaults to NAC_PLUGIN_HOME or the user home.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing mirrored plugin folders or marketplace files.",
    )
    return parser.parse_args()


def default_target_root() -> Path:
    return Path(os.environ.get("NAC_PLUGIN_HOME", Path.home())).expanduser()


def load_marketplace() -> dict:
    return json.loads(MARKETPLACE.read_text(encoding="utf-8"))


def plugin_entries(marketplace: dict) -> list[PluginEntry]:
    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        raise ValueError("Marketplace has no plugin entries.")

    entries: list[PluginEntry] = []
    for plugin in plugins:
        name = plugin.get("name")
        source = plugin.get("source", {})
        source_path = Path(str(source.get("path", "")))
        if not isinstance(name, str) or not name:
            raise ValueError("Marketplace entry without plugin name.")
        if source.get("source") != "local":
            raise ValueError(f"{name}: only local plugin sources can be mirrored.")
        expected_path = Path("plugins") / name
        if source_path != expected_path:
            raise ValueError(f"{name}: source path must be ./{expected_path.as_posix()}.")

        source_root = (REPO_ROOT / source_path).resolve()
        if not source_root.is_dir():
            raise ValueError(f"{name}: source folder is missing: {source_root}")
        manifest = source_root / ".codex-plugin" / "plugin.json"
        if not manifest.is_file():
            raise ValueError(f"{name}: plugin manifest is missing: {manifest}")
        entries.append(PluginEntry(name=name, source_path=source_path, source_root=source_root))
    return entries


def target_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def remove_existing(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    if path.is_dir():
        shutil.rmtree(path)


def mirror_marketplace(target_root: Path, mode: str, force: bool, actions: list[str]) -> None:
    target = target_root / INSTALL_MARKETPLACE
    if mode == "dry-run":
        actions.append(f"would write marketplace: {target}")
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    if target_exists(target):
        if target.is_file() and target.read_bytes() == MARKETPLACE.read_bytes():
            actions.append(f"marketplace already current: {target}")
            return
        if not force:
            raise FileExistsError(f"Marketplace already exists: {target} (use --force)")
        remove_existing(target)
    shutil.copy2(MARKETPLACE, target)
    actions.append(f"wrote marketplace: {target}")


def mirror_plugin(
    entry: PluginEntry,
    target_root: Path,
    mode: str,
    force: bool,
    actions: list[str],
) -> None:
    target = target_root / INSTALL_PLUGINS / entry.name
    if mode == "dry-run":
        actions.append(f"would {mode_plugin_action(mode)} {entry.source_root} -> {target}")
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    if target_exists(target):
        if target.is_symlink() and target.resolve() == entry.source_root:
            actions.append(f"plugin link already current: {target}")
            return
        if not force:
            raise FileExistsError(f"Plugin target already exists: {target} (use --force)")
        remove_existing(target)

    if mode == "link":
        target.symlink_to(entry.source_root, target_is_directory=True)
        actions.append(f"linked plugin: {target} -> {entry.source_root}")
        return
    if mode == "copy":
        shutil.copytree(entry.source_root, target)
        actions.append(f"copied plugin: {target}")
        return
    raise ValueError(f"Unsupported install mode: {mode}")


def mode_plugin_action(mode: str) -> str:
    if mode == "link":
        return "link"
    if mode == "copy":
        return "copy"
    return "mirror"


def install_plugins(target_root: Path, mode: str, force: bool = False) -> list[str]:
    if mode not in MODES:
        raise ValueError(f"Mode must be one of: {', '.join(MODES)}")
    if not MARKETPLACE.is_file():
        raise FileNotFoundError(f"Marketplace is missing: {MARKETPLACE}")

    target_root = target_root.expanduser().resolve()
    marketplace = load_marketplace()
    entries = plugin_entries(marketplace)

    actions: list[str] = []
    mirror_marketplace(target_root, mode, force, actions)
    for entry in entries:
        mirror_plugin(entry, target_root, mode, force, actions)
    actions.append(f"plugin count: {len(entries)}")
    return actions


def main() -> int:
    args = parse_args()
    try:
        actions = install_plugins(args.target_root, args.mode, args.force)
    except (FileExistsError, FileNotFoundError, OSError, ValueError) as exc:
        print(f"Local plugin install failed: {exc}")
        if isinstance(exc, OSError):
            print(
                "Check whether the target root is writable. Managed Codex sessions "
                "may mount ~/.agents read-only; run this on the host workspace or "
                "choose a writable --target-root for a dry integration check."
            )
        return 1

    print("Local plugin mirror result:")
    for action in actions:
        print(f"- {action}")
    if args.mode == "dry-run":
        print("No files changed. Run with --mode link or --mode copy to install.")
    else:
        print("Restart Codex or open a new session so plugin discovery can reload.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
