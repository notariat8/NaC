# NaC Runtime-Smoke

Status: vorbereitet, Owner-gated nicht ausgeführt
Letzte inhaltliche Anpassung: 2026-06-30

## Zweck

Dieses Runbook beschreibt den ersten NaC Runtime-Smoke auf `notoclaw01-host`.
Er prüft ausschließlich, ob die vorbereitete NemoClaw/OpenClaw-Zielsystemgrenze
für NaC beobachtbar ist, ohne eine Sandbox zu installieren, neu zu onboarden,
neu zu bauen oder produktive Connectoren zu aktivieren.

Maßgeblich bleiben der
[NaC-On-Prem-Agent-Runtime-Vertrag](../architecture/nac-onprem-agent-runtime.md),
das [NemoClaw-Betriebsmodell](../architecture/nemoclaw-operating-model.md) und
die offizielle NemoClaw-Dokumentation zu
[Quickstart](https://docs.nvidia.com/nemoclaw/latest/user-guide/openclaw/get-started/quickstart.md),
[Sandbox Lifecycle](https://docs.nvidia.com/nemoclaw/latest/user-guide/openclaw/manage-sandboxes/lifecycle.md),
[Runtime Controls](https://docs.nvidia.com/nemoclaw/latest/user-guide/openclaw/manage-sandboxes/runtime-controls.md),
[Monitoring](https://docs.nvidia.com/nemoclaw/latest/user-guide/openclaw/monitoring/monitor-sandbox-activity.md)
und
[Credential Storage](https://docs.nvidia.com/nemoclaw/latest/user-guide/openclaw/security/credential-storage.md).

## Erlaubter Umfang

- Target-Control-Pfad `/home/ubuntu/nac-target-control` prüfen,
- `bin/nac-target-smoke` und `bin/nac-runtime-smoke` nur read-only ausführen,
- vorhandene NemoClaw-Sandboxen mit `nemoclaw list` oder `nemoclaw status`
  statusseitig erfassen,
- für eine benannte Sandbox `nemoclaw <name> status` ausführen,
- OpenClaw-/NemoClaw-Status nur zusammenfassend und redigiert dokumentieren,
- Evidence aus
  [workflows/evidence-templates/nac-runtime-smoke.md](../../../workflows/evidence-templates/nac-runtime-smoke.md)
  unter `/home/ubuntu/nac-target-control/evidence/` ablegen.

## Blockiert

- keine Installation und kein `curl ... | bash`-Installer,
- kein `nemoclaw onboard`, `--recreate-sandbox`, `rebuild`, `policy-add`,
  `recover`, `connect`, `openclaw tui`, `openclaw agent` oder
  `nemoclaw debug`,
- kein Abruf oder Speichern eines authentifizierten Dashboard-Links,
- keine Ausgabe von Gateway-Token, Provider-Namen mit vertraulichem Kontext,
  Environment-Werten, API-Schlüsseln, PINs, Zertifikatsmaterialien oder
  Mandatsdaten,
- kein GitHub- oder OCI-Schreibzugriff vom Zielsystem,
- kein XNP-, Karten-, Register-, Signatur- oder Fachsystem-Apply.

Wenn keine passende Sandbox existiert oder `nemoclaw` nicht verfügbar ist, endet
der Smoke mit `blocked_missing_runtime` oder `blocked_missing_cli`. Das ist ein
zulässiges Ergebnis und darf nicht durch Installation oder Onboarding im selben
Lauf behoben werden.

## Owner-Apply

Vor jeder tatsächlichen Ausführung muss der Project Manager ein Owner-Apply-
Gate einholen. Der Freigabetext muss mindestens lauten:

`Owner Apply Approval for NaC runtime smoke on notoclaw01-host using /home/ubuntu/nac-target-control, read-only NemoClaw/OpenClaw status only, no install, no onboard, no rebuild, no dashboard token capture, no secrets, no mandate data, no GitHub or OCI write`

Diese Freigabe erlaubt nur den Smoke. Sie erlaubt keine spätere
Runtime-Aktivierung, keine Installation, kein Onboarding und keine
Produktivverbindung.

## Erwarteter Ablauf

1. Contract-Stand aus dem NaC-Repo prüfen.
2. `/home/ubuntu/nac-target-control/bin/nac-target-smoke` ausführen.
3. `/home/ubuntu/nac-target-control/bin/nac-runtime-smoke --summary-only`
   ausführen.
4. Falls der Runtime-Smoke eine Sandbox nennt, nur `nemoclaw <name> status`
   read-only prüfen.
5. Evidence mit Ergebnis `passed`, `blocked_missing_runtime`,
   `blocked_missing_cli` oder `blocked_policy` schreiben.
6. Handoff an den Project Manager geben, falls eine NaC-Repo-Änderung,
   Architekturentscheidung, ein Secret oder ein Owner-Gate für den nächsten
   Schritt nötig ist.

## Abschlusskriterium

Der Runtime-Smoke ist erst abgeschlossen, wenn die Evidence bestätigt:

- Owner-Apply lag vor,
- keine Installation, kein Onboarding, kein Rebuild und keine Runtime-Mutation
  wurde durchgeführt,
- kein authentifizierter Dashboard-Link oder Gateway-Token wurde gespeichert,
- keine Secrets, personenbezogenen Daten oder Mandatsdaten wurden erfasst,
- keine GitHub-, OCI- oder Fachsystem-Schreibaktion wurde ausgeführt,
- notwendige Folgearbeit ist als Handoff benannt.
