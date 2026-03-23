# Onboarding-Prompt: Startup Verification

Nutze diesen Prompt in Cursor oder Copilot vor der ersten inhaltlichen Arbeit.

```text
Fuehre einen strukturierten Startcheck fuer dieses Repository durch.

1) Lies:
- docs/START_HERE.md
- docs/startup-verification.md
- policies/startup-requirements.yaml
- policies/data-protection-policy.yaml
- policies/role-model-policy.yaml

2) Schlage die genauen Befehle fuer meinen lokalen Check vor:
- python scripts/startup_check.py --ide auto
- python scripts/startup_check.py --ide auto --run-tests

3) Interpretiere die Ergebnisse in drei Klassen:
- OK
- WARN
- BLOCKER

4) Erstelle danach eine kurze To-do-Liste fuer die Behebung aller BLOCKER.

Wichtig:
- Keine produktiven Prozessaenderungen empfehlen, solange BLOCKER offen sind.
```
