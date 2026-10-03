# Aktenleserecht durch Mitgliedschaft im Notar-Team

Status: Spezifikation vom Owner freigegeben; lokale test-first Umsetzung, keine Live-Freigabe.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: team-member-matter-read-620
leading_issue: https://github.com/notariat8/NaC/issues/620
risk_gate: Policy
delivery_mode: Protected PR
plan: docs/de/superpowers/plans/2026-10-03-team-member-matter-read.md
acceptance_ids:
  - AC-TEAMREAD-01
  - AC-TEAMREAD-02
  - AC-TEAMREAD-03
  - AC-TEAMREAD-04
  - AC-TEAMREAD-05
  - AC-TEAMREAD-06
validation_commands:
  - python -m unittest discover -s tests -p test_nac_bff_team_membership.py
  - python -m unittest discover -s tests -p test_nac_bff_workbench_endpoint.py
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_doc_links.py
```

## Zweck und fachliche Wahrheit

Ein Team pro Notar. Alle Mitglieder dürfen alle Akten dieses Teams sehen und
öffnen. Mitgliedschaft ist das Aktenleserecht. Die bisherige zusätzliche
Zuordnung als federführender Notar, Sachbearbeitung oder Vertretung ist keine
Voraussetzung für diesen Lesezugriff. Der aktuelle HTTP-403-Clientbeleg beweist
die Ablehnung, nicht deren konkreten serverseitigen Prüfgrund.

## Scope und Randbedingungen

Die Regel gilt für die Akten des jeweils zugeordneten Notar-Teams, nicht für
andere Teams. Der erste ausführbare Nachweis bleibt beim bestehenden
synthetischen MVP-Workspace und seiner Testakte. Diese Änderung behauptet
weder eine fertige Mehraktennavigation noch eine allgemeine Mehrmandanten-Runtime.
Technischer Benutzer-Owner, persönliche Anmeldung, Tenantgrenze und bestehende
API-Zielgrenzen bleiben erhalten. Mitgliedschaft erteilt keine notarielle
Qualifikation, Freigabe, Schreibberechtigung oder Vertretung.

## Ansätze und Entscheidung

1. Einzelzuordnungen aus Team-Mitgliedern spiegeln: verworfen; doppelte
   Berechtigungsdaten und Drift, außerdem keine Umsetzung der Owner-Regel.
2. Serverseitig aktuelle Mitgliedschaft am gebundenen Team prüfen: empfohlen;
   eine Berechtigungsquelle, klare Teamgrenze, bei fehlendem Nachweis gesperrt.
3. Browserangaben oder ungeprüfte Gruppen-Claims vertrauen: verworfen;
   unzureichende Aktualität und Zielbindung.

## Design

- Vertrauenswürdige Konfiguration verbindet Workspace, Team, SharePoint-Site
  und Aktenquelle. Teamnamen und Clientparameter sind keine Berechtigungsbelege.
- Die validierte Entra-Benutzer-ID und Tenant-ID werden serverseitig gegen
  die aktuelle direkte Mitgliedschaft im gebundenen Team geprüft. Die genaue
  GET-Kante und ihre Runtime-Berechtigung werden im Plan festgelegt und getestet;
  keine stillschweigende Ausweitung von Graph-Berechtigungen.
- Mitgliedschaftsnachweis muss vollständig, begrenzt und eindeutig sein.
  Paging darf nicht ignoriert werden. Fehler, fehlende Rechte, falscher Tenant,
  fehlende Mitgliedschaft oder unklare Team-/Sitebindung öffnen keine Akte.
- Aktenquelle und Akte müssen zum geprüften Team gehören. Mitgliedschaft
  anderer Teams und eine technische Owner-Rollenbezeichnung reichen nicht aus.
- Eine neutrale Leseberechtigung wird durch BFF, DTO, Projektion und SPFx
  geführt. Mitglieder dürfen nicht künstlich als Notar oder Sachbearbeitung
  bezeichnet werden, um bestehende Rollenprüfungen zu umgehen.
- Die zusätzliche Entra-/SharePoint-Personenpaarung darf Team-Lesezugriff nicht
  blockieren; sie bleibt dort, wo fachliche Personenfelder sie wirklich benötigen.
- Positive Berechtigungsnachweise werden nur im aktuellen Request genutzt;
  kein neuer langlebiger Positivcache. Bestehende Entscheidungs-Leases bleiben
  höchstens 300 Sekunden gültig. Entzug wirkt beim nächsten frischen Zugriff.
- Historische Negativtests mit einem Teammitglied werden ersetzt durch echte
  Nichtmitglieder beziehungsweise Benutzer eines anderen Teams. Neue positive
  Testfälle dürfen nicht durch zusätzliche Aktenzuordnung vorbereitet werden.

## Akzeptanzkriterien

- AC-TEAMREAD-01: Ein gültig angemeldetes Mitglied kann eine Akte seines Teams
  ohne Einzelzuordnung und ohne Vertretungsfreigabe lesen.
- AC-TEAMREAD-02: Ein Nichtmitglied oder Mitglied ausschließlich eines anderen
  Teams bekommt weder Akteninhalt noch eine Existenzoffenbarung.
- AC-TEAMREAD-03: Falscher Tenant, manipulierte IDs, unvollständige Antworten,
  Transportfehler und fehlende Runtime-Rechte stoppen ohne positiven Zugriff.
- AC-TEAMREAD-04: Ein neutraler Teamleser erhält keine notarielle Rolle und
  keine zusätzlichen Schreib-, Freigabe- oder Vertretungsaktionen.
- AC-TEAMREAD-05: Team-Lesezugriff funktioniert ohne SharePoint-Personenmapping;
  bestehende fachliche Personen- und Vertretungsprüfungen bleiben isoliert.
- AC-TEAMREAD-06: Policies, DE/EN-Dokumentation, Agentenspiegel, Contracts,
  CLI-Bedienkante und Tests stimmen überein. Synthetische Tests belegen nicht
  die Live-Reparatur; diese verlangt getrennt geprüfte Runtime-Rechte,
  Release-/Deploymentbindung und einen echten Teams-Test.

## Risiken, Prüfplan und Nicht-Ziele

Die Scope-Prüfung bindet die Umsetzung an `live_access_decision.py`,
`composition.py`, `synthetic_workspace_graph.py`, `test_environment.py`,
`workbench_endpoint.py`, `workbench_projection.py` und die SPFx-Verbraucher.
Der bisher ausschließlich auf Site-Pfade begrenzte Graph-Transport bekommt
keine offene Team-Pfadfreigabe, sondern eine exakt gebundene Mitgliedschaftskante.
Die Verträge für Generic Workbench, Workbench Live Read Binding,
Matter Access Delegation und Teams/SharePoint Data Plane werden synchronisiert.
AC-620-05 im MVP-Abnahmevertrag unterscheidet künftig Nichtmitglieder von
nicht einzeln zugeordneten Mitgliedern. GitHub-Repository-Zugriffsregeln werden
nicht in M365-Teamregeln umgedeutet oder pauschal entfernt.

Größtes Risiko ist die Vermischung von Leserecht und Fachrolle. Dazu werden
Endpoint-, Projektions- und Aktionsgrenzentests vor der Implementierung
ergänzt. Weitere Negativtests prüfen Cross-Team/Cross-Tenant, Mitgliedsentzug,
Paging, fehlerhafte Antworten und fehlende Graph-Rechte. Bestehende
Personenbindungs-, Vertretungs- und Schreibpfadtests bleiben erhalten.

Keine Tenant-Schreibaktion, neue Anmeldung, neue Berechtigung, automatische
Team-Migration oder Deployment durch diese Spezifikation. Keine Abschwächung
von Secretschutz, fachlichen Freigaben, #739-Quarantäne oder #632-Gates.

Nächster Schritt nach Spec-Review: DE/EN-Plan, test-first lokale Umsetzung,
unabhängige Review und fokussierte Tests vor vollständigen Abschlussgates.
