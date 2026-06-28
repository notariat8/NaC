# Legal-Model-Evaluationsbenchmark

Status: Benchmark-Blueprint ohne Datensatz
Letzte inhaltliche Anpassung: 2026-06-28

## Zweck

Diese Seite beschreibt den späteren deutschen Rechtsbenchmark für
Legal-Nemotron-Modellanpassungen. Sie erzeugt keinen Benchmark-Datensatz,
ruft kein Modell auf und behauptet keine juristische Qualität.

Der maschinenlesbare Vertrag steht in
[workflows/contracts/legal-model-evaluation-benchmark.contract.json](../../../workflows/contracts/legal-model-evaluation-benchmark.contract.json)
und wird durch
[scripts/validate_legal_model_evaluation_benchmark.py](../../../scripts/validate_legal_model_evaluation_benchmark.py)
geprüft.

## Bewertungsziel

Der Benchmark soll später prüfen, ob ein Modell:

- Primärquellen, Konzeptreferenzen und Kommentare sauber trennt,
- Fundstellen und Quellenklassen richtig zitiert,
- aktuelle, geänderte und historische Rechtsstände unterscheidet,
- notarielle Reviewpunkte ohne Mandatsdaten abbildet,
- Unsicherheit erkennt und an menschliche Prüfung verweist.

## Quellenhierarchie

Amtliche Veröffentlichungen und normalisierte Normfassungen können nach
Lizenz-, Nutzungs- und Normalisierungsprüfung Ground Truth liefern.
Wikipedia bleibt nur Begriffshilfe. NVIDIA Nemotron Pretraining Legal v1 ist
nur Baseline-/Gap-Analyse. Verlagstexte und Kommentare bleiben ausgeschlossen,
bis Lizenz-, API-, AVV-/DPA- und Review-Gates erfüllt sind.

## Nemotron-Routing

Der spätere Benchmark kann über `byob/mcq` vorbereitet und über
`eval/model_eval` ausgewertet werden. Beides bleibt blockiert, bis genehmigte
Quellen, Holdout-Manifest, Aufgabenfamilien, Review Owner, Evaluation-Task-IDs,
Zielmodell oder Endpoint, Ausführungsprofil und Ausgabepfad konkret vorliegen.

## Harte Grenzen

- Kein Benchmark-Datensatz ohne Owner-Apply.
- Kein Modelllauf ohne genehmigte Evaluation-Tasks.
- Kein Training auf Holdout-Fragen.
- Keine Mandatsdaten und keine Verlagsvolltexte.
- Kein Qualitätsversprechen nur aus automatischen Scores.
