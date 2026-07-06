# GitHub-First Agentic Operating Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** GitHub becomes the operational work and progress surface for nontrivial agentic NaC changes without replacing repository policies, checks and evidence.

**Architecture:** The implementation consists of a GitHub organization Project, one leading issue, a policy extension, synchronized agent/rule mirrors and structured issue/PR templates. The machine-readable policy remains authoritative; tests and validators prevent mirrors or templates from drifting from the policy.

**Tech Stack:** GitHub CLI `gh` 2.92.0, GitHub Projects, YAML/Markdown, Python `unittest`, existing NaC validators.

---

## File Structure

- Create: `tests/test_github_first_operating_model.py`
  - Responsibility: enforce the new GitHub-first policy markers, mirror text, operations docs and templates.
- Modify: `tests/test_governance_sync.py`
  - Responsibility: verify `validate_governance_sync.py` rejects a process policy without `github_first_operating_model`.
- Modify: `scripts/validate_governance_sync.py`
  - Responsibility: make `github_first_operating_model:` a mandatory process-policy section.
- Modify: `policies/process-policy.yaml`
  - Responsibility: define the machine-readable GitHub-first operating model.
- Modify: `policies/data-protection-policy.yaml`
  - Responsibility: make the no-secret/no-matter-data rule explicit for issues, pull requests and Projects.
- Modify: `AGENTS.md`, `.codex/agents/`
  - Responsibility: mirror the operating rule to agent-facing surfaces.
- Modify: `docs/de/regelarchitektur.md`, `docs/en/regelarchitektur.md`
  - Responsibility: explain hardness and completion meaning for GitHub-first work.
- Modify: `docs/de/issues/operations.md`, `docs/en/issues/operations.md`
  - Responsibility: define Project fields, views, leading-issue rules and autonomy requirements.
- Modify: `docs/de/operations/README.md`, `docs/en/operations/README.md`
  - Responsibility: link the GitHub-first operating model from the Operations index.
- Modify: `.github/ISSUE_TEMPLATE/bug_report.md`, `.github/ISSUE_TEMPLATE/feature_request.md`, `.github/ISSUE_TEMPLATE/compliance_change.md`, `.github/PULL_REQUEST_TEMPLATE.md`
  - Responsibility: collect Project, Delivery Mode, Risk Gate, validation and no-secret evidence.

## Task 1: Bootstrap GitHub Control Surface

**Files:**
- External: GitHub organization Project under `notariat8`
- External: leading GitHub issue in `notariat8/NaC`
- Local branch: `agent/<issue-number>-github-first-operating-model`

- [ ] **Step 1: Confirm no existing Project**

Run:

```bash
gh project list --owner notariat8 --format json --limit 20
```

Expected: either `{"projects":[],"totalCount":0}` or a list that already contains `NaC Control Plane`.

- [ ] **Step 2: Create Project if missing**

Run only if `NaC Control Plane` is absent:

```bash
gh project create --owner notariat8 --title "NaC Control Plane" --format json
```

Expected: JSON containing a project `number`, `title` equal to `NaC Control Plane`, and a GitHub URL.

- [ ] **Step 3: Record Project number**

Run:

```bash
gh project list --owner notariat8 --format json --limit 20 --jq '.projects[] | select(.title=="NaC Control Plane") | .number'
```

Expected: one integer, used below as `<PROJECT_NUMBER>`.

- [ ] **Step 4: Create required fields that are not already present**

Run:

```bash
gh project field-list <PROJECT_NUMBER> --owner notariat8 --format json --limit 100 --jq '.fields[].name'
```

Create each missing field:

```bash
gh project field-create <PROJECT_NUMBER> --owner notariat8 --name "Track" --data-type SINGLE_SELECT --single-select-options "Governance,Runtime,KG,BPMN,Operator,Plugins,Security,Docs,CI,Release"
gh project field-create <PROJECT_NUMBER> --owner notariat8 --name "Work Type" --data-type SINGLE_SELECT --single-select-options "Feature,Bug,Governance,Spike,Ops,Security,Docs"
gh project field-create <PROJECT_NUMBER> --owner notariat8 --name "Risk Gate" --data-type SINGLE_SELECT --single-select-options "None,Privacy,Secrets,Workflow,Policy,External Service,Human Approval"
gh project field-create <PROJECT_NUMBER> --owner notariat8 --name "Delivery Mode" --data-type SINGLE_SELECT --single-select-options "Owner Direct,Protected PR,Sync PR"
gh project field-create <PROJECT_NUMBER> --owner notariat8 --name "Priority" --data-type SINGLE_SELECT --single-select-options "P0,P1,P2,P3"
gh project field-create <PROJECT_NUMBER> --owner notariat8 --name "Size" --data-type SINGLE_SELECT --single-select-options "S,M,L"
gh project field-create <PROJECT_NUMBER> --owner notariat8 --name "Due Date" --data-type DATE
```

Expected: each command returns JSON with the created field. Use the default GitHub `Status` field as `Status`; set item status values manually in the UI until a later automation task standardizes status options through GraphQL.

- [ ] **Step 5: Create leading issue**

Run:

```bash
gh issue create --repo notariat8/NaC --title "Implement GitHub-first agentic operating model" --label compliance --body-file /tmp/nac-github-first-issue.md
```

Create `/tmp/nac-github-first-issue.md` with:

```markdown
## Goal

GitHub becomes the operational control surface for nontrivial agentic NaC work.

## Scope

- Extend the process policy with `github_first_operating_model`.
- Synchronize agent and rule mirrors.
- Extend issue/PR templates with Project, Delivery Mode, Risk Gate and validation information.
- Create GitHub organization Project `NaC Control Plane` as the progress surface.

## Non-Goals

- No real matter data in GitHub.
- No secrets, PINs, tokens or private document content in issues, pull requests, Projects or comments.
- No bypassing review, secret scanning or quality gates.

## Acceptance Criteria

- `github_first_operating_model` is machine-readable in `policies/process-policy.yaml`.
- Tests check policy, mirrors, operations documents and templates.
- `NaC Control Plane` exists in `notariat8`.
- This work runs through branch and draft PR.
- Required GitHub checks are green.

## Risk / Privacy / Secrets

Risk Gate: `Policy`

The change affects governance surfaces. It processes no matter data and no secrets.

## Delivery Mode

`Protected PR`

## Validation Plan

- `python -m unittest tests/test_github_first_operating_model.py tests/test_governance_sync.py`
- `python scripts/validate_governance_sync.py`
- `python scripts/validate_language_parity.py`
- `python scripts/validate_doc_links.py`
- `python scripts/privacy_lint.py`
- `python scripts/quality_gate.py --profile strict`
- GitHub remote checks
```

Expected: `gh issue create` returns an issue URL. Extract the issue number as `<ISSUE_NUMBER>`.

- [ ] **Step 6: Add issue to Project**

Run:

```bash
gh project item-add <PROJECT_NUMBER> --owner notariat8 --url https://github.com/notariat8/NaC/issues/<ISSUE_NUMBER> --format json
```

Expected: JSON containing the added item ID.

- [ ] **Step 7: Create implementation branch**

Run:

```bash
git switch -c agent/<ISSUE_NUMBER>-github-first-operating-model
```

Expected: branch switch succeeds and `git status --short --branch` shows the new branch.

## Task 2: Write Failing Governance Tests

**Files:**
- Create: `tests/test_github_first_operating_model.py`
- Modify: `tests/test_governance_sync.py`

- [ ] **Step 1: Add the new test file**

Create `tests/test_github_first_operating_model.py`:

```python
from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class GithubFirstOperatingModelTest(unittest.TestCase):
    def test_process_policy_defines_github_first_operating_model(self) -> None:
        policy = (REPO_ROOT / "policies" / "process-policy.yaml").read_text(
            encoding="utf-8"
        )

        for marker in (
            "github_first_operating_model:",
            "project_owner: notariat8",
            "project_title: NaC Control Plane",
            "require_leading_issue_for_nontrivial_work: true",
            "project_required_for_nontrivial_work: true",
            "allow_owner_direct_with_issue_project_trail: true",
            "completion_requires_remote_ci_checks: true",
            "forbid_secrets_and_matter_data_in_github_surfaces: true",
            "- Status",
            "- Track",
            "- Work Type",
            "- Risk Gate",
            "- Delivery Mode",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, policy)

    def test_agent_surfaces_mirror_github_first_rule(self) -> None:
        files = (
            "AGENTS.md",
            ".codex/agents",
        )

        for rel_path in files:
            text = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
            with self.subTest(path=rel_path):
                self.assertIn("GitHub-first", text)
                self.assertIn("Project", text)
                self.assertIn("Issue", text)
                self.assertIn("remote_ci_checks", text)

    def test_issue_operations_documents_define_project_fields_and_views(self) -> None:
        expected_markers = (
            "NaC Control Plane",
            "`Status`",
            "`Track`",
            "`Risk Gate`",
            "`Delivery Mode`",
            "`Owner Board`",
            "`Blocked`",
        )

        for rel_path in ("docs/de/issues/operations.md", "docs/en/issues/operations.md"):
            text = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
            with self.subTest(path=rel_path):
                for marker in expected_markers:
                    self.assertIn(marker, text)

    def test_templates_capture_project_delivery_risk_and_validation(self) -> None:
        template_paths = (
            ".github/ISSUE_TEMPLATE/bug_report.md",
            ".github/ISSUE_TEMPLATE/feature_request.md",
            ".github/ISSUE_TEMPLATE/compliance_change.md",
            ".github/PULL_REQUEST_TEMPLATE.md",
        )
        expected_markers = ("Project", "Delivery Mode", "Risk Gate", "Validierung", "Secrets")

        for rel_path in template_paths:
            text = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
            with self.subTest(path=rel_path):
                for marker in expected_markers:
                    self.assertIn(marker, text)

    def test_data_protection_policy_covers_github_surfaces(self) -> None:
        policy = (REPO_ROOT / "policies" / "data-protection-policy.yaml").read_text(
            encoding="utf-8"
        )

        self.assertIn("github_surfaces:", policy)
        self.assertIn("forbid_secrets_and_matter_data: true", policy)
        self.assertIn("issues", policy)
        self.assertIn("pull_requests", policy)
        self.assertIn("projects", policy)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Extend governance sync test**

Add this test to `tests/test_governance_sync.py`:

```python
    def test_process_policy_reports_missing_github_first_operating_model(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            policy_text = "\n".join(
                (
                    "change_management:",
                    "  delivery_modes:",
                    "    protected_pr:",
                    "    owner_direct_main:",
                    "rule_architecture:",
                    "  human_explanation_de: docs/de/regelarchitektur.md",
                    "  human_explanation_en: docs/en/regelarchitektur.md",
                )
            )
            self._write_minimal_repo(root, policy_text)
            validate_governance_sync.REPO_ROOT = root

            errors = validate_governance_sync.validate_process_policy_file()

        self.assertIn(
            "Pflichtabschnitt fehlt in process-policy: github_first_operating_model:",
            errors,
        )
```

- [ ] **Step 3: Run tests and verify RED**

Run:

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests/test_github_first_operating_model.py tests/test_governance_sync.py
```

Expected: FAIL. At least one failure mentions missing `github_first_operating_model:` or missing GitHub-first markers.

## Task 3: Implement Policy And Validator

**Files:**
- Modify: `scripts/validate_governance_sync.py`
- Modify: `policies/process-policy.yaml`
- Modify: `policies/data-protection-policy.yaml`

- [ ] **Step 1: Update mandatory process-policy keys**

In `scripts/validate_governance_sync.py`, add `"github_first_operating_model:"` to `MANDATORY_PROCESS_POLICY_KEYS`.

- [ ] **Step 2: Add process-policy section**

Append this section after `issue_governance` in `policies/process-policy.yaml`:

```yaml
github_first_operating_model:
  enabled: true
  project_owner: notariat8
  project_title: NaC Control Plane
  project_scope: organization
  project_required_for_nontrivial_work: true
  require_leading_issue_for_nontrivial_work: true
  require_project_fields_for_nontrivial_work: true
  allow_owner_direct_with_issue_project_trail: true
  completion_requires_remote_ci_checks: true
  forbid_secrets_and_matter_data_in_github_surfaces: true
  required_project_fields:
    - Status
    - Track
    - Work Type
    - Risk Gate
    - Delivery Mode
    - Priority
    - Size
    - Iteration
    - Due Date
  required_statuses:
    - Inbox
    - Ready
    - In Progress
    - Review
    - Blocked
    - Done
  required_views:
    - Owner Board
    - Now
    - Blocked
    - Governance And Security
    - Release Readiness
    - My Agent Work
  delivery_modes:
    - Owner Direct
    - Protected PR
    - Sync PR
  branch_prefixes:
    agent: "agent/<issue-number>-<short-slug>"
    sync: "sync/<issue-number>-<short-slug>"
    hotfix: "hotfix/<issue-number>-<short-slug>"
```

- [ ] **Step 3: Add data-protection GitHub surface rule**

Append this section to `policies/data-protection-policy.yaml`:

```yaml
github_surfaces:
  forbid_secrets_and_matter_data: true
  applies_to:
    - issues
    - pull_requests
    - projects
    - project_fields
    - comments
  allowed_content:
    - synthetic_examples
    - policy_references
    - validation_evidence_without_secret_values
    - links_to_authorized_evidence_without_private_payload
```

- [ ] **Step 4: Run targeted tests and verify GREEN for policy layer**

Run:

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests/test_governance_sync.py tests/test_github_first_operating_model.py
```

Expected: governance-sync missing-section tests pass; remaining failures point only to missing mirror, docs or template markers.

## Task 4: Update Mirrors And Operations Docs

**Files:**
- Modify: `AGENTS.md`
- Modify: `.codex/agents/`
- Modify: `docs/de/regelarchitektur.md`
- Modify: `docs/en/regelarchitektur.md`
- Modify: `docs/de/issues/operations.md`
- Modify: `docs/en/issues/operations.md`
- Modify: `docs/de/operations/README.md`
- Modify: `docs/en/operations/README.md`

- [ ] **Step 1: Mirror core agent rule**

Add one concise GitHub-first paragraph to `AGENTS.md` and the Codex agent profiles:

```markdown
- GitHub-first gilt für nichttriviale agentische Arbeit: ein führendes Issue beschreibt Auftrag, Scope, Akzeptanzkriterien, Risk Gate, Delivery Mode und Validierung; das Organization Project `NaC Control Plane` zeigt Status und Blocker; ein Update ist erst nach dem jeweiligen Delivery Mode und erfolgreichen `remote_ci_checks` fertig.
```

- [ ] **Step 2: Mirror no-secret rule**

Add this sentence to the Codex-facing agent rules:

```markdown
Issues, Pull Requests, Project-Felder und Kommentare sind GitHub-Oberflächen und dürfen keine Secrets, PINs, Tokens, privaten Dokumentinhalte oder echten Mandatsdaten enthalten.
```

- [ ] **Step 3: Extend German rule architecture**

In `docs/de/regelarchitektur.md`, add a row to the rule-group table:

```markdown
| GitHub-first Arbeitssteuerung | Macht agentische Arbeit über Issues, PRs und Project sichtbar, ohne Policies zu ersetzen. | Arbeitsregel plus harte Abschlusskopplung | führendes Issue, `NaC Control Plane`, PR/Owner-Direct-Modus, `remote_ci_checks` |
```

Add a short section:

```markdown
## GitHub-first Arbeitssteuerung

Nichttriviale agentische Arbeit hat ein führendes Issue und ein Item im Organization Project `NaC Control Plane`. Das Project zeigt Status, Track, Risk Gate, Delivery Mode, Priorität, Größe und Blocker. Repo-Policies, Commits, Reviews, Checks und Event-Journal bleiben führend für die prüfbare Wahrheit.
```

- [ ] **Step 4: Extend English rule architecture**

In `docs/en/regelarchitektur.md`, add the translated table row and section:

```markdown
| GitHub-first work control | Makes agentic work visible through issues, pull requests and Project without replacing policies. | work rule plus hard completion coupling | leading issue, `NaC Control Plane`, PR/owner-direct mode, `remote_ci_checks` |
```

```markdown
## GitHub-First Work Control

Nontrivial agentic work has a leading issue and an item in the organization Project `NaC Control Plane`. The Project shows status, track, risk gate, delivery mode, priority, size and blockers. Repository policies, commits, reviews, checks and the event journal remain the auditable truth.
```

- [ ] **Step 5: Extend Issue operations docs**

Add a `GitHub-first agentic work` section to `docs/de/issues/operations.md` and `docs/en/issues/operations.md`. Include the required fields and views from the spec with exact field names: `Status`, `Track`, `Work Type`, `Risk Gate`, `Delivery Mode`, `Priority`, `Size`, `Iteration`, `Due Date`, `Owner Board`, `Now`, `Blocked`, `Governance And Security`, `Release Readiness`, `My Agent Work`.

- [ ] **Step 6: Link from Operations README files**

Add this German bullet to `docs/de/operations/README.md`:

```markdown
- [../superpowers/specs/2026-05-26-github-first-agentic-operating-model-design.md](../superpowers/specs/2026-05-26-github-first-agentic-operating-model-design.md): GitHub-first Arbeitssteuerung für agentische Issues, PRs und Projects.
```

Add this English bullet to `docs/en/operations/README.md`:

```markdown
- [../superpowers/specs/2026-05-26-github-first-agentic-operating-model-design.md](../superpowers/specs/2026-05-26-github-first-agentic-operating-model-design.md): GitHub-first work control for agentic issues, pull requests and Projects.
```

- [ ] **Step 7: Run targeted mirror tests**

Run:

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests/test_github_first_operating_model.py
```

Expected: remaining failures point only to templates if templates are not yet updated.

## Task 5: Update Issue And PR Templates

**Files:**
- Modify: `.github/ISSUE_TEMPLATE/bug_report.md`
- Modify: `.github/ISSUE_TEMPLATE/feature_request.md`
- Modify: `.github/ISSUE_TEMPLATE/compliance_change.md`
- Modify: `.github/PULL_REQUEST_TEMPLATE.md`

- [ ] **Step 1: Add shared GitHub-first block to each issue template**

Add this block after the front matter in each issue template:

```markdown
## GitHub-first Steuerung

- Project: `NaC Control Plane`
- Delivery Mode: `Owner Direct | Protected PR | Sync PR`
- Risk Gate: `None | Privacy | Secrets | Workflow | Policy | External Service | Human Approval`
- Track: `Governance | Runtime | KG | BPMN | Operator | Plugins | Security | Docs | CI | Release`
- Validierung:
- Secrets/Mandatsdaten: keine Secrets, PINs, Tokens, privaten Dokumentinhalte oder echten Mandatsdaten enthalten
```

- [ ] **Step 2: Add PR template block**

Add this block to `.github/PULL_REQUEST_TEMPLATE.md` before `## Validierung`:

```markdown
## GitHub-first Steuerung

- Führendes Issue:
- Project: `NaC Control Plane`
- Delivery Mode: `Owner Direct | Protected PR | Sync PR`
- Risk Gate: `None | Privacy | Secrets | Workflow | Policy | External Service | Human Approval`
- Project-Status:
- Blocker:
```

- [ ] **Step 3: Run template tests**

Run:

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests/test_github_first_operating_model.py
```

Expected: PASS.

## Task 6: Full Local Verification

**Files:**
- Verify-only task.

- [ ] **Step 1: Run unit tests**

Run:

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest
```

Expected: all tests pass.

- [ ] **Step 2: Run governance sync**

Run:

```bash
/home/ubuntu/.venvs/nac/bin/python scripts/validate_governance_sync.py
```

Expected: `STATUS: PASSED`.

- [ ] **Step 3: Run language parity**

Run:

```bash
/home/ubuntu/.venvs/nac/bin/python scripts/validate_language_parity.py
```

Expected: `STATUS: PASSED`.

- [ ] **Step 4: Run doc links**

Run:

```bash
/home/ubuntu/.venvs/nac/bin/python scripts/validate_doc_links.py
```

Expected: `STATUS: PASSED`.

- [ ] **Step 5: Run privacy lint**

Run:

```bash
/home/ubuntu/.venvs/nac/bin/python scripts/privacy_lint.py
```

Expected: `Privacy lint passed.`

- [ ] **Step 6: Run strict quality gate**

Run:

```bash
/home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
```

Expected: `STATUS: PASSED`.

## Task 7: Publish Draft PR And Project Status

**Files:**
- Git branch and GitHub PR only.

- [ ] **Step 1: Commit implementation**

Run:

```bash
git status --short
git add tests/test_github_first_operating_model.py tests/test_governance_sync.py scripts/validate_governance_sync.py policies/process-policy.yaml policies/data-protection-policy.yaml AGENTS.md .codex/agents docs/de/regelarchitektur.md docs/en/regelarchitektur.md docs/de/issues/operations.md docs/en/issues/operations.md docs/de/operations/README.md docs/en/operations/README.md .github/ISSUE_TEMPLATE/bug_report.md .github/ISSUE_TEMPLATE/feature_request.md .github/ISSUE_TEMPLATE/compliance_change.md .github/PULL_REQUEST_TEMPLATE.md
git commit -m "feat: add github first operating model controls"
```

Expected: commit succeeds.

- [ ] **Step 2: Push branch**

Run:

```bash
git push -u origin agent/<ISSUE_NUMBER>-github-first-operating-model
```

Expected: branch is pushed.

- [ ] **Step 3: Open draft PR**

Run:

```bash
gh pr create --repo notariat8/NaC --base main --head agent/<ISSUE_NUMBER>-github-first-operating-model --draft --title "Add GitHub-first agentic operating controls" --body-file /tmp/nac-github-first-pr.md
```

Create `/tmp/nac-github-first-pr.md` with validation evidence from Task 6 and `Closes #<ISSUE_NUMBER>`.

- [ ] **Step 4: Add PR to Project**

Run:

```bash
gh project item-add <PROJECT_NUMBER> --owner notariat8 --url https://github.com/notariat8/NaC/pull/<PR_NUMBER> --format json
```

Expected: JSON containing the added PR item ID.

- [ ] **Step 5: Wait for remote checks**

Run:

```bash
gh pr checks <PR_NUMBER> --repo notariat8/NaC --watch
```

Expected: required checks complete successfully or failures are investigated before merge.

## Task 8: Merge Or Hold

**Files:**
- GitHub PR only.

- [ ] **Step 1: If checks pass and review is not required, mark PR ready**

Run:

```bash
gh pr ready <PR_NUMBER> --repo notariat8/NaC
```

Expected: PR leaves draft state.

- [ ] **Step 2: Merge only after the chosen Delivery Mode permits it**

For protected PR mode, merge after checks and owner review:

```bash
gh pr merge <PR_NUMBER> --repo notariat8/NaC --squash --delete-branch
```

Expected: PR merges to `main`, branch is deleted, issue closes.

- [ ] **Step 3: Sync local main and verify final state**

Run:

```bash
git switch main
git pull --ff-only
git status --short --branch
gh api repos/notariat8/NaC/commits/main --jq .sha
```

Expected: workspace is clean and local `main` equals GitHub `main`.

## Self-Review

- Spec coverage: Project bootstrap, leading issue, policy, mirrors, docs, templates, local validation, PR, Project item and remote checks are covered.
- Placeholder scan: no placeholder markers or undefined task references are present.
- Type consistency: `github_first_operating_model`, `NaC Control Plane`, `Risk Gate`, `Delivery Mode`, `remote_ci_checks` and branch naming are consistent across tasks.
