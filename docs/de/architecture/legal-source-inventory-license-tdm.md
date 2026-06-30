# Legal-Source-Inventar und Lizenz-/TDM-Gate

Status: Quelleninventar-Readiness ohne Ingestion
Letzte inhaltliche Anpassung: 2026-06-30

## Zweck

Diese Seite beschreibt das Quelleninventar, Lizenz- und TDM-Gate für spätere
Legal-Nemotron- oder Rechtsgraph-Arbeit. Sie lädt keine Quellentexte, erzeugt
keinen Benchmark-Datensatz, ruft kein Modell auf und startet kein Training.

Der maschinenlesbare Vertrag steht in
[workflows/contracts/legal-source-inventory-license-tdm.contract.json](../../../workflows/contracts/legal-source-inventory-license-tdm.contract.json)
und wird durch
[scripts/validate_legal_source_inventory_license_tdm.py](../../../scripts/validate_legal_source_inventory_license_tdm.py)
geprüft.
Der aktuelle Gate-Stand ist zusätzlich über
`nac legal-graph source-inventory --format json` abrufbar. Der Befehl liest nur
das Inventar-Metadatenmodell und bleibt ohne Quellentext-Ingestion,
Benchmark-Erzeugung, Modelllauf oder Training.

## Inventarregel

Jede Quelle braucht vor einer produktiven Nutzung mindestens:

- stabile Quell-ID und kanonische URL,
- Quellenklasse und Jurisdiktionsbezug,
- Lizenz- und Nutzungsstatus,
- TDM- und Bulk-Access-Entscheidung,
- Attributionsplan,
- Storage-Grenze,
- menschlichen Review Owner.

Zusätzlich führt das Inventar eine Prüftiefe je Quelle. Sie trennt, ob die
Seed-Metadaten vollständig sind, ob Lizenzbedingungen, TDM/Bulk-Access,
Attribution und Storage-Grenze bereits fachlich geprüft wurden und welcher
nächste Review zwingend ist. Diese Prüftiefe ist weiterhin nur Metadaten:
Sie lädt keine Quellentexte und ersetzt keine Owner-Apply-Freigabe.

## Aktuelle Startquellen

- NVIDIA Nemotron Pretraining Legal v1 bleibt ein englischer
  Baseline-Datensatzkandidat, nicht eine deutsche Rechtsquelle.
- `recht.bund.de` bleibt ein offizieller Veröffentlichungskandidat für spätere
  Ingestionsplanung, aber ohne Bulk-Crawl oder Volltexttraining vor Review.
- Wikipedia `Rechtsquelle` bleibt nur Begriffshilfe für Quellenhierarchie und
  Kollisionsregeln.

## Harte Grenzen

- Kein Volltextdownload ohne Owner-Apply.
- Kein Bulk-Crawl ohne Nutzungs- und TDM-Review.
- Kein Benchmark-Datensatz ohne freigegebene Quellen.
- Kein Training oder Modelllauf aus diesem Vertrag.
- Keine Mandatsdaten und keine Verlagsvolltexte im Produktrepo.
