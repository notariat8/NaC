# Legal-Model-Card-/AI-SBOM-Delta

Status: Delta-Gate ohne Checkpoint
Letzte inhaltliche Anpassung: 2026-06-30

## Zweck

Diese Seite beschreibt das Model-Card- und AI-SBOM-Delta-Gate für spätere
Legal-Nemotron-Modellanpassungen. Sie startet kein Training, führt keine
Modellevaluation aus, veröffentlicht keinen Checkpoint und behauptet keine
juristische Antwortqualität.

Der maschinenlesbare Vertrag steht in
[workflows/contracts/legal-model-card-ai-sbom-delta.contract.json](../../../workflows/contracts/legal-model-card-ai-sbom-delta.contract.json)
und wird durch
[scripts/validate_legal_model_card_ai_sbom_delta.py](../../../scripts/validate_legal_model_card_ai_sbom_delta.py)
geprüft.

## Model-Card-Delta

Vor einer späteren Veröffentlichung muss die Model Card mindestens folgende
Punkte abdecken:

- Basismodell oder Checkpoint-Referenz,
- Zweck und verbotene Nutzung,
- Quelleninventar, Lizenz-/TDM-Status und Datenlinie,
- Evaluationszusammenfassung und bekannte Grenzen,
- menschliches Review-Protokoll,
- AI-SBOM-Referenz und Owner-Apply-Referenz,
- Attestation, dass keine Mandatsdaten genutzt wurden.

## AI-SBOM-Delta

Das AI-SBOM-Delta bleibt ein Planungsnachweis. Es muss spätere Änderungen an
Modell, Dataset-Kandidaten, Rechtsquelleninventar, Trainings- oder
Evaluationsruntime, Drittanbietern, Lizenz-/TDM-Status, Risikokontrollen und
menschlicher Review-Grenze abbilden.

## Harte Grenzen

- Kein Checkpoint ohne vollständige Model Card.
- Kein AI-SBOM-Delta mit Platzhaltern.
- Keine Qualitätsbehauptung ohne Evaluation und menschliche Review.
- Keine Quellentexte, Verlagsvolltexte, Secrets oder Mandatsdaten in Model
  Card oder AI-SBOM.
- Kein Training aus diesem Delta-Gate.
