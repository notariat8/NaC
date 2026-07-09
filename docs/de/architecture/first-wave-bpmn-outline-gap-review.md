# First-Wave-BPMN-Gap-Review

Diese Decision Note beschreibt den Offline-Gap-Review für die vier
First-Wave-BPMN-Outlines.

## Zweck

`nac kg first-wave-gap-review --format json` vergleicht die First-Wave-Outlines
mit der vorhandenen SharePoint-MVP-Schema-Datei, dem Ontologie-Storage-Vertrag
und den bestehenden BPMN-Quellen.

Der Review erzeugt planbare Artefakte für:

- SharePoint-Feldlücken und Choice-/Taxonomie-Reviews
- BPMN-Gaps wie fehlende Critical-Path-Annotationen oder unklare Gate-Abbildung
- Ontologie-Projektionspatches ohne Werte
- spätere Verification Contracts vor jeder Apply-Aktion

## Aktueller Befund

Der aktuelle Offline-Smoke meldet:

- 4 First-Wave-Fälle
- 9 SharePoint-Feldlücken
- 10 BPMN-Gaps
- 12 Ontologie-Projektionspatches

Ein konkreter MVP-Gap ist `Akten.Vorgangstyp`: Die Choice-Liste enthält bereits
mehrere First-Wave-Slugs, aber `vorsorgevollmacht-patientenverfuegung` muss vor
einem Live-Schema-Apply als geplante Erweiterung geprüft werden.

## Grenzen

Der Gap-Review ist offline-only:

- keine Microsoft-Graph-Requests
- keine SharePoint-Schreiboperation
- keine SharePoint-Schemaänderung
- keine BPMN-Mutation
- kein Ontologie-Patch-Apply
- keine Mandatswerte in Git oder Ontologie
- keine Dokumentinhalte
- keine Secrets

Der Validator
[scripts/validate_first_wave_bpmn_outline_gap_review.py](../../../scripts/validate_first_wave_bpmn_outline_gap_review.py)
prüft diese Grenzen im strikten Quality Gate.
