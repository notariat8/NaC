from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "install_local_plugins.py"


def load_installer_module():
    spec = importlib.util.spec_from_file_location("install_local_plugins", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


installer = load_installer_module()


class InstallLocalPluginsTests(unittest.TestCase):
    def test_copy_mode_mirrors_marketplace_and_plugin_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            target_root = Path(tmp_dir)

            actions = installer.install_plugins(target_root, "copy")

            marketplace_path = target_root / ".agents" / "plugins" / "marketplace.json"
            self.assertTrue(marketplace_path.is_file())
            marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
            plugin_names = [entry["name"] for entry in marketplace["plugins"]]
            self.assertIn("nac-cyberjack-rfid", plugin_names)
            self.assertIn("plugin count", actions[-1])
            for plugin_name in plugin_names:
                manifest = (
                    target_root
                    / "plugins"
                    / plugin_name
                    / ".codex-plugin"
                    / "plugin.json"
                )
                self.assertTrue(manifest.is_file(), plugin_name)

    def test_dry_run_leaves_target_root_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            target_root = Path(tmp_dir)

            actions = installer.install_plugins(target_root, "dry-run")

            self.assertTrue(actions)
            self.assertFalse((target_root / ".agents").exists())
            self.assertFalse((target_root / "plugins").exists())


if __name__ == "__main__":
    unittest.main()
