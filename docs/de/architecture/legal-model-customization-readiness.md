# Legal-Nemotron-Readiness

Status: Readiness-Vertrag ohne Training
Letzte inhaltliche Anpassung: 2026-06-28

## Zweck

Diese Seite beschreibt, wie NaC später ein Legal-Nemotron-Finetuning oder eine
domänenspezifische Modellanpassung vorbereiten darf. Sie startet kein Training,
veröffentlicht keinen Checkpoint und macht aus Modellantworten keine
notarielle Rechtswahrheit.

Der maschinenlesbare Vertrag steht in
[workflows/contracts/legal-model-customization-readiness.contract.json](../../../workflows/contracts/legal-model-customization-readiness.contract.json)
und wird durch
[scripts/validate_legal_model_customization_readiness.py](../../../scripts/validate_legal_model_customization_readiness.py)
geprüft.

## Quellenrolle

Der Vertrag trennt drei Rollen:

- NVIDIA Nemotron Pretraining Legal v1 ist ein englischer Legal-Baseline- und
  Evaluationskandidat, aber keine deutsche Rechtsquelle.
- `recht.bund.de` ist ein amtlicher Veröffentlichungs- und späterer
  Ingest-Kandidat für Bundesgesetzblatt-Daten über ELI, PDF, ZIP und RSS.
- Der Wikipedia-Artikel zu Rechtsquellen ist nur ein begrifflicher Anker für
  Quellenhierarchie, Normenkollision und Rechtserkenntnisquellen.

## Gate-Reihenfolge

Vor jeder ausführbaren Konfiguration braucht NaC:

1. Quelleninventar, Lizenz-, Nutzungs- und TDM-Prüfung.
2. Quellenhierarchie mit Primärquellen, Konzeptreferenzen und
   Kommentar-Ausschlussregeln.
3. Normalisierungsschema mit Zitaterhalt, Deduplizierung und Speichergrenze.
4. Deutschen Rechtsbenchmark mit Holdout-Quellen und Fehler-Taxonomie.
5. Model Card, AI-SBOM, Evaluation und bekannte Grenzen.
6. Owner-Apply mit Kosten-, Runtime-, Rollback- und Sicherheitsnachweis.

## Nemotron-Planung

Die mögliche Nemotron-Kette bleibt rein planerisch:

- `curate/nemo_curator` für spätere Quellenkuratierung,
- `data_prep/pretrain_prep` für spätere Pretraining-Datenvorbereitung,
- `pretrain/automodel` oder `pretrain/megatron_bridge` erst nach Owner-Apply,
- `eval/model_eval` für Evaluation vor Qualitätsbehauptungen,
- `byob/mcq` für einen deutschen Rechtsbenchmark.

Ohne konkretes Modell, genehmigten Korpuspfad, Tokenizer, Sequenzlänge,
Hardwareprofil, Ausführungsprofil, Ausgabepfad und Evaluation-Task-IDs darf
kein runnbarer Trainingsbefehl entstehen.

## Harte Grenzen

- Keine echten Mandatsdaten.
- Keine Verlagsvolltexte im Produktrepo.
- Kein Training ohne Owner-Apply.
- Keine Checkpoint-Veröffentlichung ohne Model Card und AI-SBOM.
- Keine Rechtsantwort ohne menschliche notarielle Prüfung.
