# Ponytail Skill-Only Smoke Evidence

Evidence-Status: nur Vorlage
Template-Version: 2026-06-29

## Umfang

- Zielhost: `notoclaw01-host`
- Target-Control-Pfad: `/home/ubuntu/nac-target-control`
- Kandidat: `ponytail`
- Upstream: `https://github.com/DietrichGebert/ponytail`
- Beobachtete Version: `v4.8.4`
- Modus: `skill_only_smoke`

## Owner-Apply-Referenz

- Owner-Apply-Freigabe:
- Freigegebene Aktion:
- Freigegeben durch:
- Freigabezeitpunkt:

## Vorbedingungen

- [ ] NaC-Vertragsstatus geprüft.
- [ ] Ponytail bleibt `candidate_not_installed`.
- [ ] Codex-Lifecycle-Hooks sind nicht aktiviert.
- [ ] OpenClaw-Runtime-Aktivierung ist nicht aktiviert.
- [ ] Kein GitHub-Write vom Zielsystem.
- [ ] Kein OCI-Write vom Zielsystem.
- [ ] Keine Mandatsdaten, personenbezogenen Daten, Secrets, PINs, Tokens,
      Schlüssel oder Zertifikatsmaterialien.

## Erlaubte Prüfung

Nur nicht-sensitive Metadaten erfassen:

- Target-Control-Pfad vorhanden oder nicht vorhanden:
- Skill-Only-Kandidatenpfad geplant:
- öffentliche Upstream-Version beobachtet:
- keine Hook-Dateien kopiert:
- keine Runtime-Aktivierung durchgeführt:

## Ergebnis

- Ergebnis: `not_run | passed | blocked`
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
- PINs oder Kartendaten,
- für die Prüfung nicht erforderliche Konto-Kennungen.
