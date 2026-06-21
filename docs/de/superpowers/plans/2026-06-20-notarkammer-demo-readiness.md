# Notarkammer-Demo-Readiness Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Ziel:** Die vorhandenen notariat8/NaC-Fähigkeiten innerhalb von vier Tagen glaubwürdig und live-demo-fähig für eine einstündige Vorstellung bei der Notarkammer machen.

**Architektur:** NaC bleibt die Quelle für notarielle Prozessmodelle, mit BPMN 2.0 als kanonischem Fachmodell und `bpmn-js` als editierbarer Modellierungsoberfläche. `www-n8` wird der verständliche öffentliche Einstieg; `xyflow`-artige Graph-Ansichten dürfen Dauer, Parallelität und kritischen Pfad visualisieren, ersetzen aber nicht BPMN als Quelle.

**Tech Stack:** NaC Python-Validatoren und CLI, BPMN 2.0, bpmn-js, statisches `www-n8` GitHub Pages, `app.notariat8.de` OCI-Functions-Runtime, GitHub Protected PRs, keine Mandatsdaten.

---

## Harte Frist

- Präsentation: vier Tage ab 20. Juni 2026.
- Demo-Ziel: 60 Minuten.
- Zielzustand: vorzeigbar und belastbar, nicht vollständig.
- Planungszeitzone: CEST.

## Nicht Verhandelbarer Scope

- Keine Mandatsdaten in Git, Logs, öffentlichen Seiten oder Demo-URLs.
- Keine Live-Portal-Writes, keine echten Grundbuch-/Registeraktionen, kein Kundenmailversand.
- Kein OCI Apply, Release, Secret Read oder destruktive Git-Aktion ohne separates Owner Gate.
- BPMN 2.0 ist die kanonische Quelle für Geschäftsprozessmodelle.
- `xyflow` ist Overlay/Rendering für Verständlichkeit, keine zweite Fachquelle.
- Dauerwerte sind editierbare Planungsparameter. Sie werden nicht als amtliche Durchschnittswerte dargestellt, solange keine zitierfähige amtliche Statistik vorliegt.

## Demo-These

Notarielle Arbeit ist keine lineare Vier-Schritte-Checkliste. NaC kann ein kontrolliertes, prüfbares und editierbares Prozessmodell zeigen, in dem:

- rechtliche und operative Gates explizit sind,
- parallele Arbeit sichtbar wird,
- Blockaden klar werden,
- der kritische Pfad verständlich ist,
- erwartete Dauer als Planungsparameter gepflegt wird,
- öffentliche Ansichten keine Mandatsdaten enthalten,
- die App erst nach Identitäts-, Sitzungs- und Rollengates öffnet.

## Vier-Tage-Lieferplan

### Tag 1: Quellmodell Und Demo-Schnitt

**Ziel:** Die Demo-Wahrheit festlegen: zwei Usecases, einer tief und einer kurz.

- [ ] GitHub-Stand für NaC, `www-n8` und `oci-landing-zone` prüfen.
- [ ] Demo-Readiness-Issue in NaC mit Links auf PRs und Gates anlegen.
- [ ] `Immobilienkaufvertrag` als tiefen Hauptprozess modellieren.
- [ ] `Unterschriftsbeglaubigung` als kurzen Vergleichsprozess modellieren.
- [ ] Prozessmetadatenvertrag definieren für:
  - minimale Planungsdauer,
  - maximale Planungsdauer,
  - Zeiteinheit,
  - Abhängigkeiten/Blocker,
  - Parallelgruppe,
  - Kandidat für kritischen Pfad,
  - Rolle,
  - Nachweispflicht.
- [ ] Ersten Vertrag klein genug halten, damit Validierung und Demo verlässlich bleiben.

### Tag 2: Editierbares BPMN Und Visuelle Overlays

**Ziel:** Der Prozess muss editierbar und erklärbar wirken.

- [ ] `bpmn-js` Editor-/Viewer-Route für Demo-Prozessmodelle ergänzen oder sichtbar machen.
- [ ] Editor-Modus klar als Demo/Sandbox kennzeichnen und nicht mit echten Mandatsdaten verbinden.
- [ ] Dauer- und Abhängigkeits-Overlay-Vertrag aus BPMN-/KG-Metadaten ableiten.
- [ ] `xyflow`-artige Kritischer-Pfad-Ansicht nur als abgeleitete Rendering-Schicht ergänzen.
- [ ] Mindestens zeigen:
  - einen parallelen Split,
  - einen Join,
  - ein blockierendes Gate,
  - ein kritisches-Pfad-Segment,
  - einen editierbaren Dauerparameter.

### Tag 3: Öffentliche Demo Polieren

**Ziel:** `www-n8` muss für eine Notarkammer verständlich sein.

- [ ] `www-n8`-Texte auf notarielle Kontrolle statt Softwarejargon ausrichten.
- [ ] "Prozessmodell ansehen" als echten Nutzerpfad gestalten, nicht als GitHub-Sprung.
- [ ] "Dauer und kritischer Pfad" für den Immobilienprozess sichtbar erklären.
- [ ] Abschnitt "Was wird nicht gespeichert" für Vertrauen in öffentliche Ansicht und App ergänzen.
- [ ] Direkten Demo-Pfad herstellen:
  - `notariat8.de`,
  - Vorgangsübersicht,
  - Immobilien-Prozessmodell,
  - App-Login,
  - geschützter Start-/Workspace-Status,
  - Editor/Viewer.

### Tag 4: Probe, Fallbacks Und Skript

**Ziel:** Die Live-Demo muss robust sein.

- [ ] Live-Smoke-Tests für alle Demo-URLs ausführen.
- [ ] Fallback-Screenshots oder statisches HTML für Prozessviewer und App-Status vorbereiten.
- [ ] 60-Minuten-Skript schreiben.
- [ ] 5-Minuten-Kurzversion schreiben.
- [ ] Prüfen, dass öffentliche Seiten keine Oracle-/OCI-/Provider-Begriffe enthalten, außer bewusst in technischen Governance-Abschnitten.
- [ ] Vor jedem Release oder Deploy Gate alle Checks ausführen.

## Parallele Agentische Arbeitspakete

### Paket A: Fachrecherche Und Zeitevidenz

**Owner:** Research Agent.

**Output:** `docs/de/superpowers/specs/2026-06-20-notarkammer-demo-domain-evidence.md`

- [ ] Primäre rechtliche Anker für den Immobilienkaufvollzug sammeln.
- [ ] Typische Blocker und Abhängigkeiten identifizieren:
  - Grundbuchstand,
  - Rang/Priorität,
  - Finanzierung und Grundschuld,
  - öffentlich-rechtliche Genehmigungen,
  - kommunales Vorkaufsrecht,
  - steuerliche Unbedenklichkeit,
  - Kaufpreisfälligkeit,
  - Eigentumsumschreibung.
- [ ] Demo-sichere Dauerklassen definieren:
  - Stunden,
  - Tage,
  - Wochen,
  - Monate.
- [ ] Jeden nicht-amtlichen Dauerwert als "Planwert" oder "Erfahrungswert" kennzeichnen.

### Paket B: BPMN-/KG-Prozesstiefe

**Owner:** NaC BPMN Agent.

**Output:** Protected NaC PR.

- [ ] `Immobilienkaufvertrag` zu einem reichen notariellen Prozess mit 20-35 sinnvollen Schritten erweitern.
- [ ] BPMN-Validität und NaC-BPMN-Profilregeln erhalten.
- [ ] Metadaten nur dort ergänzen, wo Validatoren sie erlauben.
- [ ] Tests für Metadatenextraktion ergänzen oder aktualisieren.
- [ ] `Unterschriftsbeglaubigung` kurz, aber glaubwürdig halten.

### Paket C: Öffentlicher Website-Demo-Pfad

**Owner:** `www-n8` Agent.

**Output:** Protected `www-n8` PR.

- [ ] Homepage-Pfad zum Prozessmodell verbessern.
- [ ] Dauer-/Kritischer-Pfad-Sprache für nichttechnische Nutzer ergänzen.
- [ ] App-Übergang klar machen.
- [ ] Bestehende Content-Tests und Styleguide-Regeln erhalten.
- [ ] Kundennahe Texte frei von OCI-/Provider-/internen Begriffen halten.

### Paket D: Editor- Und Visualisierungsvertrag

**Owner:** App/Editor Agent.

**Output:** Protected NaC PR, kein OCI Apply.

- [ ] Aktuelle Webrouten und sicheren Erweiterungspunkt identifizieren.
- [ ] Editor-/Viewer-Vertrag vor Runtime-Wiring ergänzen.
- [ ] Tests für Fail-Closed-Verhalten und Mandatsdatenfreiheit ergänzen.
- [ ] Abgeleiteten Graph-View-Vertrag für Dauer-/Parallel-/Kritischer-Pfad-Overlay ergänzen.

### Paket E: Demo-Skript Und Fallback-Evidenz

**Owner:** QA/Demo Agent.

**Output:** `docs/de/demo/notarkammer-2026-06-demo-script.md`.

- [ ] 60-Minuten-Skript schreiben.
- [ ] 5-Minuten-Version schreiben.
- [ ] Live-URLs und Fallback-Artefakte listen.
- [ ] Exakte Klickfolge aufnehmen.
- [ ] Stop-Line aufnehmen, falls Login oder IdP langsam ist.

## Immobilienprozess-Skelett Für Tag 1

Der erste detaillierte Prozess soll mindestens diese logischen Blöcke enthalten:

1. Anfrage und Beteiligte aufnehmen.
2. Grundstücks-/Wohnungseigentumsdaten erfassen.
3. Verkäufer-/Käuferidentität und Vertretung prüfen.
4. Aktuellen Grundbuchstand abrufen oder erfassen.
5. Belastungen und Löschungsbedarf prüfen.
6. Finanzierung/Grundschuldbedarf klären.
7. Öffentlich-rechtliche Genehmigungen prüfen.
8. Vorkaufsrechts-/Gemeindeprozess prüfen.
9. Kaufpreis, Fälligkeit, Besitzübergang, Nutzen/Lasten klären.
10. GNotKG-Geschäftswert prüfen.
11. Entwurf erstellen.
12. Verbraucherfrist prüfen, falls einschlägig.
13. Entwurf versenden.
14. Rückfragen/Beteiligtenfreigabe dokumentieren.
15. Beurkundung vorbereiten.
16. Beurkundung durchführen.
17. Ausfertigungen/Abschriften erstellen.
18. Auflassungsvormerkung beantragen.
19. Finanzierungsgrundschuld koordinieren.
20. Löschungsunterlagen/Treuhandauflagen koordinieren.
21. Anzeigen an Finanzamt/Behörden senden.
22. Genehmigungen/Negativzeugnis nachhalten.
23. Steuerliche Unbedenklichkeitsbescheinigung nachhalten.
24. Kaufpreisfälligkeit prüfen.
25. Fälligkeitsmitteilung versenden.
26. Zahlungseingang oder Zahlungsnachweis erfassen.
27. Eigentumsumschreibung beantragen.
28. Grundbuchvollzug prüfen.
29. Kosten/GNotKG-Abrechnung prüfen.
30. Abschlussnachweise und Aktenabschluss dokumentieren.

## Dauer- Und Kritischer-Pfad-Modell

Konservative Darstellung verwenden:

```yaml
duration:
  min: 2
  max: 6
  unit: weeks
  basis: planning_value
critical_path:
  candidate: true
  blocked_by:
    - land_register_priority_notice
    - tax_clearance_certificate
parallel_group: post_notarization_execution
```

Darstellung:

- Grün: kann jetzt beginnen.
- Gelb: kann parallel laufen, wartet aber auf externe Rückmeldung.
- Rot: blockiert den kritischen Pfad.
- Grau: in diesem Fall nicht relevant.

## Einstündiges Demo-Skript

1. **5 min:** Start auf `notariat8.de`; öffentliche, mandatsdatenfreie Prozessreferenz erklären.
2. **10 min:** Immobilienkaufvertrag öffnen; zeigen, dass es keine lineare Checkliste ist.
3. **10 min:** Parallelität und kritischen Pfad zeigen: Grundbuch, Finanzierung, Genehmigungen, Steuer.
4. **10 min:** Editierbare BPMN-/Prozessmodelloberfläche zeigen.
5. **10 min:** App-Login/Protected Start zeigen; Fail-Closed Workspace erklären.
6. **10 min:** Kurzer Vergleich mit Unterschriftsbeglaubigung.
7. **5 min:** Governance-Abschluss: GitHub, Protected PRs, keine Mandatsdaten, kontrollierter Release.

## Erwartete Owner Gates In Den Vier Tagen

Gates möglichst bündeln:

1. PR Review/Merge Gates für NaC und `www-n8`.
2. Release Gates für App/Runtime erst nach bekanntem Merge-Commit.
3. Apply Gates nur, falls neue OCI-Routen/-Konfiguration nötig sind.
4. Keine Secret Gates, solange keine neue Runtime-Integration sie wirklich benötigt.

## Aktueller Tagesmodus Für Große Schritte

Der Standardmodus für die verbleibende Notarkammer-Vorbereitung ist ein
mehrstündiger Multi-Agent-Block. Der Controller startet unabhängige PR-only
Tracks parallel und sammelt die Ergebnisse zu einem Gate-Paket, statt den Owner
für Routine-Evidenz zu unterbrechen.

### Owner-frei während des Blocks

- GitHub PR-, Issue-, Branch-, Check- und Diff-Status lesen.
- Lokale Tests, Dokumentationsvalidatoren und Quality Gates ausführen.
- Nicht-sensitive öffentliche Referenzen und bereits versionierte
  Demo-Artefakte lesen.
- PRs vorbereiten, kommentieren und als Review-Paket zusammenfassen.
- Worktree- und Branch-Hygiene read-only prüfen.

### Owner-Gates bleiben separat

- Design Approval, wenn fachlicher Scope oder Architektur neu ist.
- Review/Merge, sobald ein Protected PR fertig ist.
- Release Approval, sobald ein konkreter Commit live gebaut oder deployed wird.
- Apply Approval, sobald Resource Manager oder OCI-Konfiguration geändert wird.
- Secret-, Credential-, destruktive Git- und echte Live-Daten-Aktionen.

### Parallelisierung

Ein Block soll mindestens drei getrennte Lanes nutzen, wenn der Scope es
erlaubt:

1. `www-n8` öffentliche Demo-Oberfläche.
2. NaC BPMN-/Usecase-Tiefe.
3. Live-Demo-Runbook, Fallbacks und Smoke-Pfade.
4. Optional Governance/Queue-Memory, wenn Reibung im Ablauf sichtbar wird.

Jede Lane arbeitet in einem isolierten Worktree auf eigenem Branch. Nach Merge
wird der Cleanup als eigener, exakter Owner-Gate-Satz ausgegeben, sofern Branch-
oder Worktree-Löschung nötig ist.

## Verifikationsbasis

NaC:

```bash
PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest discover -s tests
git diff --check
```

`www-n8`:

```bash
node --test tests/content.test.js
git diff --check
```

OCI Landing Zone, nur wenn berührt:

```bash
PYTHONPATH=. /home/ubuntu/.venvs/nac/bin/python -m unittest discover -s tests
git diff --check
```

## Erstes Empfohlenes Owner-Paket

Nach den ersten vorbereiteten PRs genau ein Paket anfragen:

```text
Owner Review/Merge for the Notarkammer demo readiness planning PRs:
- NaC process/domain plan PR
- www-n8 public demo path PR
- optional NaC BPMN/editor contract PR
```

Release- und Apply-Gates bleiben separat und müssen exakte Commit-/Image-/Plan-Identifier enthalten.
