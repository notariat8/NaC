# NaC Runtime-Smoke Evidence

Evidence-Status: nur Vorlage
Template-Version: 2026-06-30
Contract-Status: `ready_owner_gated_not_executed`

## Umfang

- Zielhost: `notoclaw01-host`
- Target-Control-Pfad: `/home/ubuntu/nac-target-control`
- Runtime-Familie: `NemoClaw/OpenClaw`
- Modus: `runtime_smoke_read_only`
- Evidence-Zielpfad: `/home/ubuntu/nac-target-control/evidence/nac-runtime-smoke-YYYY-MM-DD.md`

## Owner-Apply-Referenz

- Owner-Apply-Freigabe:
- Freigegebene Aktion:
- Freigegeben durch:
- Freigabezeitpunkt:

## Vorbedingungen

- [ ] NaC-Vertragsstatus geprüft.
- [ ] Owner-Apply liegt vor.
- [ ] Kein Installations-, Onboarding-, Rebuild- oder Policy-Apply-Auftrag.
- [ ] Public-Origin-Konfiguration wurde explizit über `NAC_PUBLIC_ORIGIN`
      oder `config/public-origin` bereitgestellt.
- [ ] Keine Secrets, personenbezogenen Daten, PINs, Gateway-Tokens,
      Dashboard-Auth-URLs, Schlüssel, Zertifikatsmaterialien oder Mandatsdaten.
- [ ] Kein GitHub-Write vom Zielsystem.
- [ ] Kein OCI-Write vom Zielsystem.

## Erlaubte Prüfung

Nur nicht-sensitive Statuswerte erfassen:

- Target-Control-Pfad vorhanden:
- `bin/nac-target-smoke` Ergebnis:
- `bin/nac-runtime-smoke --summary-only` Ergebnis:
- Public-Origin-Quelle: `NAC_PUBLIC_ORIGIN | config/public-origin | missing`
- Public-Origin-Ergebnis: `reachable | unreachable | not_checked | redacted`
- `nemoclaw` CLI erkannt:
- Sandbox-Status: `running | stopped | not_found | not_checked | redacted`
- Gateway-/Dashboard-Status: `reachable | unreachable | not_checked | redacted`
- Dashboard-Auth-Link gespeichert: `no`
- OpenClaw-Workspace geprüft: `yes | no | not_checked`
- Policy-/Egress-Status: `ok | blocked | not_checked | redacted`

## Ergebnis

- Ergebnis: `not_run | passed | blocked_missing_runtime | blocked_missing_cli | blocked_missing_public_origin | blocked_policy`
- Zusammenfassung:
- Folgearbeit erforderlich:
- Erforderlicher NaC-Repo-Change:
- Owner-Eingabe erforderlich:

## Bestätigung Verbotener Inhalte

Diese Evidence-Datei darf nicht enthalten:

- echte personenbezogene Daten,
- Mandats- oder Dokumentinhalte,
- Secrets oder API-Schlüssel,
- private Schlüssel oder Zertifikatsmaterialien,
- PINs, Kartendaten oder Gateway-Tokens,
- authentifizierte Dashboard-URLs,
- für die Prüfung nicht erforderliche Konto-Kennungen.
