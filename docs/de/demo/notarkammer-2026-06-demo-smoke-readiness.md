# Notarkammer-Demo 2026-06: Smoke-Readiness

Smoke-ID: `NK-DEMO-SMOKE-2026-06`
Version: `1.0.0`
Status: Protected PR, Review/Merge Gate, no OCI apply.

Scope: `docs/de/demo/`, `docs/en/demo/`, `src/nac_observability/`,
`scripts/notarkammer_demo_smoke.py` und `tests/`. Dieses Artefakt ist ein
runbook smoke check für die Vorführung, kein Monitoring; no live network test
in Unit-Tests. Keine Secrets, keine Mandatsdaten, keine OCI- oder
IdP-Schreiboperation, keine Infrastruktur- oder Runtime-Änderung. Alle
Beispiele verwenden synthetic Demo-Daten, einen Testnutzer (test user) und
vorab freigegebene Demo-Sichten.

## T-15 Minuten Smoke Check

| Check | Manuelle Sichtprüfung | Erwartung | Fallback |
| --- | --- | --- | --- |
| www-n8 Prozessmodell | `https://notariat8.de/prozessmodell.html` im frischen oder bereits geladenen Browser-Tab öffnen. | Prozessmodell ist erreichbar; Immobilienkaufvertrag, Gate und kritischer Pfad sind sichtbar. | Bereits geladenen Tab oder cached screenshot zeigen; nicht live deployen. |
| App Health | `https://app.notariat8.de/healthz` per Browser oder read-only curl öffnen. | Kurz, nicht-sensitiv, kein Secret, kein Mandatsbezug. | Health-Tab schließen und Workspace-Grenze zeigen. |
| Workspace ohne Session | `https://app.notariat8.de/workspace` ohne Session öffnen. | Erwartet sind `401`, `403` oder eine geschlossene Sicht: fail-closed, no workspace content, keine Workspace-Inhalte, keine Mandatsdaten. | Fail-closed als Sicherheitsnachweis erklären. |
| Login/OIDC | `https://app.notariat8.de/login` nur mit freigegebenem Testnutzer (test user) fortsetzen. | Login/OIDC bleibt Demo-gebunden; keine echten Zugangsdaten, keine echten Akten. | Wenn OCI oder IdP kalt oder langsam ist: do not debug live, nicht live debuggen; zum Prozessmodell und zur Workspace-Grenze wechseln. |

Optionaler maschinenlesbarer Vorabcheck, nur read-only:

```bash
python scripts/notarkammer_demo_smoke.py --timeout-seconds 15
```

Das Script prüft nur die festgelegten Demo-URLs, akzeptiert den geschlossenen
Workspace als erwartete Fail-Closed-Grenze und redigiert Query-Werte sowie
Login-/Callback-Antworten in der JSON-Ausgabe.

## Sprecherlinien

- Speaker line: This public process view is the audited demo path.
- Speaker line: The app entry stays protected until the approved demo sign-in is complete.
- Speaker line: A closed workspace is the expected safety result before sign-in.
- Speaker line: If sign-in is slow, we continue with the process model and the protected boundary.

## Guardrails

- Kundentexte und Speaker line-Einträge nennen nur notariat8, Demo-Pfad,
  Prozessmodell, App-Einstieg und geschützten Workspace.
- Interne Provider-, OCI-, IdP-, ATP-, Vault-, Wallet-, Tenant- und
  Secret-Details bleiben aus Kundentexten heraus.
- Kein Live-Debugging im Termin; kein Wechsel in OCI-Konsole, IdP-Konsole,
  Secrets, Wallets, ATP-Schema oder produktive Logs.
- Kein Apply, kein Release, keine Runtime-Aktion und keine Cloud-Änderung.
- Evidence für den Protected PR besteht nur aus Branch, Commit-SHA,
  Testausgabe, Review/Merge Gate und diesem versionierten Runbook.

## Kalter oder Langsamer OCI-/IdP-Pfad

Wenn OCI oder IdP cold or slow ist, wird nicht gewartet und nicht live
debuggt:

1. Bereits geladenen Tab oder cached screenshot des Prozessmodells zeigen.
2. `https://app.notariat8.de/workspace` ohne Session zeigen.
3. Workspace boundary als Fail-Closed-Ergebnis erklären.
4. Im PR nur `manual_review` oder `blocked` dokumentieren, ohne Secrets oder
   Mandatsdaten zu kopieren.
