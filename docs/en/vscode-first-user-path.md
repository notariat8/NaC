# VS Code: First-User Path

## Do I Need To Read Everything?

No. You do not need to read every Markdown file.

Recommended minimum path:

1. [docs/en/START_HERE.md](START_HERE.md)
2. [docs/en/vscode-copilot-start.md](vscode-copilot-start.md)
3. Start with the form wizard instead of reading everything.

## Step 1: Clarify Start Question

First clarify:

- formation (`founding`) or existing organization (`existing`)?

This decision controls the rest of the question path.

## Step 2: Start Stateful Onboarding

Start the wizard:

```bash
python scripts/onboarding_wizard.py start --session out/onboarding/session.json --actor-name "Max Example" --actor-role "prozessverantwortung" --github-login "ofunk-nvidia" --mode existing
```

Check progress:

```bash
python scripts/onboarding_wizard.py status --session out/onboarding/session.json
```

Export plan:

```bash
python scripts/onboarding_wizard.py export-plan --session out/onboarding/session.json --output out/onboarding/plan.md
```

Finalize audit bundle, immutable evidence with hash:

```bash
python scripts/onboarding_wizard.py finalize --session out/onboarding/session.json --output-dir out/onboarding/final --export-pdf
```

## Step 3: Collaborate Across Several Days

- Every contribution is stored with role, name and timestamp.
- Several people can continue the same session file.
- The role and qualification model remains binding.

## Step 4: From Analysis To Pilot

When all questions are answered:

1. Define pilot processes.
2. Finalize roles and qualifications.
3. Create the first pull request for the pilot.
