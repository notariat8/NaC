from __future__ import annotations

from pathlib import Path
import shutil
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from validate_m365_azure_bff_live_activation import _validate_windows_portability


class WindowsPortabilityValidatorTests(unittest.TestCase):
    def _fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        for relative in (
            "src/nac_bff/activation_security_backend.py",
            "src/nac_bff/activation_security_windows.py",
            "src/nac_bff/azure_activation_contract.py",
            "src/nac_bff/azure_activation_facade.py",
            "src/nac_m365_graph/mvp_test_environment_deploy.py",
            "tests/test_activation_security_windows.py",
            "tests/test_windows_offline_cli_portability.py",
            "tests/test_m365_bff_failed_partial_safe_completion.py",
            ".github/workflows/windows-portability.yml",
        ):
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO_ROOT / relative, destination)
        return temporary, root

    def test_repository_workflow_and_coverage_markers_pass(self) -> None:
        errors: list[str] = []
        _validate_windows_portability(REPO_ROOT, errors)
        self.assertEqual(errors, [])

    def test_path_filter_weakening_is_rejected(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        workflow = root / ".github/workflows/windows-portability.yml"
        workflow.write_text(
            workflow.read_text(encoding="utf-8").replace(
                "  pull_request:\n", "  pull_request:\n    paths:\n      - tests/**\n"
            ),
            encoding="utf-8",
        )
        errors: list[str] = []
        _validate_windows_portability(root, errors)
        self.assertIn(
            "Windows portability workflow must not use path filters", errors
        )

    def test_optional_or_live_workflow_weakening_is_rejected(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        workflow = root / ".github/workflows/windows-portability.yml"
        workflow.write_text(
            workflow.read_text(encoding="utf-8")
            + "\n# continue-on-error\n# az login\n",
            encoding="utf-8",
        )
        errors: list[str] = []
        _validate_windows_portability(root, errors)
        self.assertIn(
            "Windows portability workflow contains forbidden marker: continue-on-error",
            errors,
        )
        self.assertIn(
            "Windows portability workflow contains forbidden marker: az login",
            errors,
        )

    def test_trigger_and_execution_pins_are_enforced(self) -> None:
        mutations = (
            ("  push:\n", "", "Windows portability workflow trigger missing: push"),
            (
                "uses: actions/checkout@v7",
                "uses: actions/checkout@main",
                "Windows portability checkout pin differs",
            ),
            (
                'python-version: "3.11"',
                'python-version: "3.x"',
                "Windows portability Python 3.11 pin missing",
            ),
            (
                "persist-credentials: false",
                "persist-credentials: true",
                "Windows portability checkout credentials must not persist",
            ),
        )
        for old, new, expected in mutations:
            with self.subTest(expected=expected):
                temporary, root = self._fixture()
                self.addCleanup(temporary.cleanup)
                workflow = root / ".github/workflows/windows-portability.yml"
                workflow.write_text(
                    workflow.read_text(encoding="utf-8").replace(old, new),
                    encoding="utf-8",
                )
                errors: list[str] = []
                _validate_windows_portability(root, errors)
                self.assertIn(expected, errors)

    def test_child_guard_and_public_edge_weakening_is_rejected(self) -> None:
        mutations = (
            (
                "subprocess.Popen = blocked",
                "subprocess.Popen = subprocess.Popen",
                "Windows portability child guard missing: subprocess.Popen = blocked",
            ),
            (
                "fake_runner.reconcile_azure_bff_live_activation_lock = touch_all_side_effects",
                "fake_runner.reconcile_azure_bff_live_activation_lock = lambda: None",
                "Windows portability facade guard wiring missing: fake_runner.reconcile_azure_bff_live_activation_lock = touch_all_side_effects",
            ),
            (
                '"NAC_ALLOW_WINDOWS_LIVE": "1"',
                '"NAC_ALLOW_WINDOWS_LIVE": "0"',
                'Windows portability forged platform hint missing: "NAC_ALLOW_WINDOWS_LIVE": "1"',
            ),
            (
                '"bff-azure-function-deployment-reconcile",',
                '"bff-azure-function-deployment-reconcile-removed",',
                "Windows portability exact live command missing: bff-azure-function-deployment-reconcile",
            ),
        )
        for old, new, expected in mutations:
            with self.subTest(expected=expected):
                temporary, root = self._fixture()
                self.addCleanup(temporary.cleanup)
                test_path = root / "tests/test_windows_offline_cli_portability.py"
                test_path.write_text(
                    test_path.read_text(encoding="utf-8").replace(old, new),
                    encoding="utf-8",
                )
                errors: list[str] = []
                _validate_windows_portability(root, errors)
                self.assertIn(expected, errors)

    def test_exact_blocked_payload_is_enforced(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        facade = root / "src/nac_bff/azure_activation_facade.py"
        facade.write_text(
            facade.read_text(encoding="utf-8").replace(
                '"writes_started": False', '"writes_started": True'
            ),
            encoding="utf-8",
        )
        errors: list[str] = []
        _validate_windows_portability(root, errors)
        self.assertIn(
            'Windows portability exact blocked payload differs: "writes_started": False',
            errors,
        )

    def test_noop_child_blocker_is_rejected(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        test_path = root / "tests/test_windows_offline_cli_portability.py"
        test_path.write_text(
            test_path.read_text(encoding="utf-8").replace(
                'def blocked(*args, **kwargs):\n    raise AssertionError(\\"network-or-subprocess-access\\")',
                'def blocked(*args, **kwargs):\n    return None',
            ),
            encoding="utf-8",
        )
        errors: list[str] = []
        _validate_windows_portability(root, errors)
        self.assertIn("Windows portability child blocker is not fail-closed", errors)

    def test_dead_branch_child_blocker_is_rejected(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        test_path = root / "tests/test_windows_offline_cli_portability.py"
        test_path.write_text(
            test_path.read_text(encoding="utf-8").replace(
                'def blocked(*args, **kwargs):\n    raise AssertionError(\\"network-or-subprocess-access\\")',
                'def blocked(*args, **kwargs):\n    if False:\n        raise AssertionError(\\"network-or-subprocess-access\\")\n    return None',
            ),
            encoding="utf-8",
        )
        errors: list[str] = []
        _validate_windows_portability(root, errors)
        self.assertIn("Windows portability child blocker is not fail-closed", errors)

    def test_pathlib_guard_removal_is_rejected(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        test_path = root / "tests/test_windows_offline_cli_portability.py"
        test_path.write_text(
            test_path.read_text(encoding="utf-8").replace(
                "io.open = guarded_open", "io.open = io.open"
            ),
            encoding="utf-8",
        )
        errors: list[str] = []
        _validate_windows_portability(root, errors)
        self.assertIn(
            "Windows portability child guard missing: io.open = guarded_open", errors
        )

    def test_bracket_secret_expression_is_rejected(self) -> None:
        temporary, root = self._fixture()
        self.addCleanup(temporary.cleanup)
        workflow = root / ".github/workflows/windows-portability.yml"
        workflow.write_text(
            workflow.read_text(encoding="utf-8")
            + '\nenv:\n  TOKEN: "${{ secrets [\'TOKEN\'] }}"\n',
            encoding="utf-8",
        )
        errors: list[str] = []
        _validate_windows_portability(root, errors)
        self.assertIn(
            "Windows portability workflow contains forbidden secret expression", errors
        )


if __name__ == "__main__":
    unittest.main()
