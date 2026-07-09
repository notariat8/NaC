# First-Wave BPMN Outline

This decision note describes the offline artifact for the first wave of deep
BPMN and ontology modeling.

## Purpose

`nac kg first-wave-bpmn-outline --format json` binds the four first-wave cases
from deep-process routing to existing sources:

- usecase-local `knowledge-graph.graph.json`
- existing BPMN files under [bpmn/](../../../bpmn)
- ontology projection plan without matter values
- later SharePoint field-gap plan without live apply
- later verification contract before any productive action

## First Wave

The first wave currently contains:

- `online-gmbh-gruendung`
- `immobilienkaufvertrag`
- `handelsregisteranmeldung`
- `vorsorgevollmacht-patientenverfuegung`

This selection does not mean that all other business cases are unimportant. It
only bounds the next deep-modeling batch so ontology, BPMN and SharePoint
projection do not grow without control.

## Boundaries

The outline artifact is offline-only:

- no Microsoft Graph requests
- no SharePoint writes
- no SharePoint schema changes
- no document-content reads
- no matter values in Git or ontology
- no secrets

The validator
[scripts/validate_first_wave_bpmn_outline.py](../../../scripts/validate_first_wave_bpmn_outline.py)
checks these boundaries in the strict quality gate.
