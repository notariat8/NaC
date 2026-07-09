# First-Wave-BPMN-Outline

Diese Decision Note beschreibt das Offline-Artefakt für die erste Welle tiefer
BPMN- und Ontologie-Modellierung.

## Zweck

`nac kg first-wave-bpmn-outline --format json` bindet die vier
First-Wave-Fälle aus dem Deep-Process-Routing an vorhandene Quellen:

- usecase-lokale `knowledge-graph.graph.json`
- vorhandene BPMN-Dateien unter [bpmn/](../../../bpmn)
- Ontologie-Projektionsplan ohne Mandatswerte
- späterer SharePoint-Field-Gap-Plan ohne Live-Apply
- späterer Verification Contract vor jeder produktiven Aktion

## First Wave

Die erste Welle besteht aktuell aus:

- `online-gmbh-gruendung`
- `immobilienkaufvertrag`
- `handelsregisteranmeldung`
- `vorsorgevollmacht-patientenverfuegung`

Diese Auswahl bedeutet nicht, dass alle anderen Geschäftsvorfälle unwichtig
sind. Sie begrenzt nur den nächsten Deep-Modeling-Batch, damit Ontologie,
BPMN und SharePoint-Projektion nicht unkontrolliert wachsen.

## Grenzen

Das Outline-Artefakt ist offline-only:

- keine Microsoft-Graph-Requests
- keine SharePoint-Schreiboperation
- keine SharePoint-Schemaänderung
- keine Dokumentinhaltslesung
- keine Mandatswerte in Git oder Ontologie
- keine Secrets

Der Validator
[scripts/validate_first_wave_bpmn_outline.py](../../../scripts/validate_first_wave_bpmn_outline.py)
prüft diese Grenzen im strikten Quality Gate.
