# Technischer Team-Owner statt Fachnutzer-Owner

Status: Owner-Klarstellung vom 02.10.2026, lokale Umsetzung freigegeben.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: technical-team-owner-766
leading_issue: https://github.com/notariat8/NaC/issues/766
risk_gate: Policy
delivery_mode: Protected PR
plan: docs/de/superpowers/plans/2026-10-02-technical-team-owner.md
acceptance_ids:
  - AC-OWNER-01
  - AC-OWNER-02
  - AC-OWNER-03
  - AC-OWNER-04
  - AC-OWNER-05
validation_commands:
  - python -m unittest tests.test_m365_technical_team_owner tests.test_teams_sharepoint_graph_data_plane tests.test_customer_tenant_onboarding
  - python scripts/validate_teams_sharepoint_graph_data_plane.py
  - python scripts/validate_governance_sync.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_spec_traceability.py
  - python scripts/nac.py doctor --profile strict
```

## Ziel und Grenze

Das in der [Team-Ownership-Policy](../../../../policies/m365-team-ownership-policy.json)
exakt gebundene technische Benutzerkonto ist der alleinige
Team-Owner der von NaC angelegten Teams. Fachnutzer melden sich mit eigenen
Konten an und sind ausschließlich Mitglieder. „Application User“ bezeichnet
hier einen technischen Benutzer, nicht OAuth-App-only. Delegierte technische
Verwaltung, Anwendungs-Runtime und notarielle Freigabe bleiben getrennt.

## Akzeptanzkriterien

- AC-OWNER-01: Der Offline-Erstellungsplan enthält genau einen expliziten
  technischen Owner und keine implizite Owner-Zuweisung an den aufrufenden
  Fachnutzer. Fachnutzer dürfen keine Owner-Rolle erhalten.
- AC-OWNER-02: Die technische Team-Eigentümerschaft verleiht weder notarielle
  Qualifikation noch NaC-/fachliche Aktenberechtigung oder einen zweiten natürlichen Principal.
  Der delegierte Verwaltungsnachweis über `GET /me` bleibt erhalten.
- AC-OWNER-03: Vor dem ersten Write müssen Gruppen-Owner und Teams-Owner dem
  exakt aufgelösten technischen Benutzer entsprechen. Fehlende, zusätzliche,
  falsch gebundene, doppelte, nicht benutzerbezogene, malformed oder paginierte
  Owner-Daten stoppen fail-closed; Folgeseiten werden nicht aufgerufen. Es gibt
  keine automatische Owner-Migration oder Entfernung.
- AC-OWNER-04: Historische Applied-Evidence wird nicht geändert. Alte
  Fachnutzer-Owner-Nachweise sind keine Konformitätsbelege des neuen Modells.
  Fehlende aktuelle Evidence bleibt als ungeprüft sichtbar.
- AC-OWNER-05: Policy, Vertrag, Konfiguration, Code, Negativtests, DE/EN-Doku
  und Codex-/pi-Regelspiegel werden gemeinsam validiert.

Diese Korrektur führt keine Microsoft-Abfrage, Anmeldung, Token-Erneuerung,
Tenant-Änderung, App-Berechtigungsänderung, Bereitstellung oder Live-Abnahme aus.
Lizenz-/Nutzungsprüfung, Principal-Gates, Sites.Selected und Aktenrechte bleiben
unverändert. Bestehende Teams werden erst in einem getrennten Auftrag geändert.
Microsoft-Plattformrechte eines Team-Owners werden nicht als beseitigt
behauptet. Kundenfreigabe der Rollenzuweisung und AVV-Grenzen bleiben erhalten.
