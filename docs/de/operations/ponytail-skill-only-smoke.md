# Ponytail Skill-Only Smoke

Status: vorbereitet, nicht ausgeführt
Letzte inhaltliche Anpassung: 2026-06-29

## Zweck

Dieses Runbook bereitet einen späteren Ponytail Skill-Only Smoke auf
`notoclaw01` vor. Es installiert Ponytail nicht, aktiviert keine Codex-
Lifecycle-Hooks und startet keine OpenClaw-Runtime-Aktivierung.

Der Smoke darf nur prüfen, ob Ponytail als optionaler Skill-Kandidat in die
NaC-Target-Control-Grenze passt. Maßgeblich bleiben der
[NaC-On-Prem-Agent-Runtime-Vertrag](../architecture/nac-onprem-agent-runtime.md)
und die AI-SBOM-Grenze in [sbom-for-ai.md](../sbom-for-ai.md).

## Erlaubter Umfang

- öffentliche Ponytail-Metadaten gegen die im NaC-Repo erfassten Werte prüfen,
- Zielsystempfade für einen künftigen Skill-Only-Test dokumentieren,
- ein nicht-sensitives Evidence-Dokument aus der Vorlage vorbereiten,
- bestätigen, dass keine Mandatsdaten, Secrets, Hooks oder Runtime-Aktivierung
  im Spiel sind.

## Blockiert

- keine Codex-Plugin-Installation,
- keine Codex- oder Claude-Lifecycle-Hooks,
- keine OpenClaw-Runtime-Aktivierung,
- kein GitHub- oder OCI-Schreibzugriff vom Zielsystem,
- keine echten Mandatsdaten, personenbezogenen Daten, PINs, Tokens,
  Schlüssel oder Zertifikatsmaterialien,
- keine Kürzung von Security-, Datenschutz-, Owner-Gate-, Test- oder
  Validatorpflichten.

## Vor Owner-Apply

Vor einer tatsächlichen Ausführung muss der Project Manager ein Owner-Apply-
Gate einholen. Der Apply-Text muss mindestens enthalten:

- Zielhost `notoclaw01-host`,
- Zielpfad `/home/ubuntu/nac-target-control`,
- Ponytail-Upstream und beobachtete Version,
- geplante Skill-Only-Aktion,
- Bestätigung: keine Hooks, keine Runtime-Aktivierung, keine Secrets, keine
  Mandatsdaten, kein GitHub-/OCI-Write.

## Evidence-Vorlage

Für den späteren Smoke wird die Vorlage
[workflows/evidence-templates/ponytail-skill-only-smoke.md](../../../workflows/evidence-templates/ponytail-skill-only-smoke.md)
genutzt. Ausgefüllte Evidence gehört auf dem Zielsystem in
`/home/ubuntu/nac-target-control/evidence/` und darf nur nicht-sensitive
Metadaten enthalten.

## Abschlusskriterium

Der Smoke ist erst abgeschlossen, wenn die Evidence bestätigt:

- Ponytail bleibt `candidate_not_installed`,
- Lifecycle-Hooks bleiben deaktiviert,
- OpenClaw-Runtime-Aktivierung bleibt blockiert,
- alle NaC-Governance-, Owner-Gate- und Validatorpflichten bleiben wirksam,
- kein NaC-Repo-Change ist aus dem Smoke offen.
