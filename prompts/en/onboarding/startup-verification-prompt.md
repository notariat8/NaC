# Onboarding Prompt: Startup Verification

Use this prompt in Cursor or Copilot before the first content change.

```text
Run a structured startup check for this repository.

1) Read:
- docs/en/START_HERE.md
- docs/en/startup-verification.md
- policies/startup-requirements.yaml
- policies/data-protection-policy.yaml
- policies/role-model-policy.yaml

2) Propose the exact commands for my local check:
- python scripts/startup_check.py --ide auto
- python scripts/startup_check.py --ide auto --run-tests

3) Interpret the results in three classes:
- OK
- WARN
- BLOCKER

4) Then create a short to-do list for fixing all BLOCKER items.

Important:
- Do not recommend productive process changes while BLOCKER items are open.
```
