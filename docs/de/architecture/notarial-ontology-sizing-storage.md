# Notarielles Ontologie-Sizing und Storage-Grenze

Diese Decision Note fixiert die Grenze zwischen Geschäftsvorfall-Inventar,
Ontologie-Projektion und operativer Microsoft-365-Datenhaltung.

## Entscheidung

NaC nutzt für den M365-MVP SharePoint als operative Datenhaltung. Die
Ontologie ist kein Laufzeit-Store und keine zentrale Wissensgraph-Ablage,
sondern ein versionierter Projektions- und Prüfvertrag über den
usecase-lokalen Knowledge Graphs.

Der maschinenlesbare Vertrag steht unter
[workflows/contracts/notarial-ontology-sizing-storage.contract.json](../../../workflows/contracts/notarial-ontology-sizing-storage.contract.json)
und wird mit `nac kg ontology-storage-contract --format json` gegen das
aktuelle Geschäftsvorfall-Inventar geprüft.

## Warum kein zentraler Knowledge Graph

Die fachliche Quelle bleibt je Usecase:

- [usecases/](../../../usecases) enthält die notariellen Vorgangsarten.
- Jede Vorgangsart führt ihre eigene `knowledge-graph.graph.json`.
- Ein zentraler `knowledge-graph/` Ordner ist nicht zulässig.

Das Geschäftsvorfall-Inventar zählt und klassifiziert alle vorhandenen
Vorgänge für Sizing und Routing. Es ersetzt aber nicht die usecase-lokalen
Graphen.

## Storage-Rollen

| Ebene | Rolle |
| --- | --- |
| SharePoint | operative MVP-Datenhaltung für Aktenmetadaten, Aufgaben, Dokument-Pointer, Vertretungsfreigaben und redigierte Auditereignisse |
| Ontologie | versionierter Katalog und Projektionsvertrag für Typen, Feldabbildungen, zulässige Beziehungen und Sizing |
| BPMN | Prozessmodell und Review-Oberfläche, nicht Workflow-Engine |
| MCP/Graph | Laufzeit-Zugriffsschicht über Microsoft Graph REST v1.0 |

Die Ontologie speichert keine Matter-Instanzwerte, keine Dokumentvolltexte,
keine rohen SharePoint-Items, keine Graph-Rohantworten und keine Secrets.

## Performance-Grenzen

Alle Geschäftsvorfälle werden für das Sizing gezählt. Tiefe Prozessmodellierung
bleibt selektiv, weil große Ontologien sonst zur Laufzeit unkontrolliert
wachsen können.

Der Contract setzt daher harte Grenzen:

- keine globale OWL-/Graph-Reasoning-Pflicht im Nutzer-Request-Pfad
- keine Massenspiegelung von Office-/SharePoint-Inhalten in Agent Memory
- keine Dokumentvolltexte in Ontologie oder Git
- keine Matter-Instanzwerte in der Repo-Ontologie
- Microsoft Graph REST v1.0 only, keine alten SharePoint-APIs, kein SDK-Zwang
- Architektur-Review, wenn Business-Case-Anzahl oder Complexity-Score die
  gesetzten Schwellwerte überschreiten

## Validierung

Der Validator
[scripts/validate_notarial_ontology_storage_contract.py](../../../scripts/validate_notarial_ontology_storage_contract.py)
prüft:

- Contract-Struktur und Schema-Version
- SharePoint als operativen MVP-Store
- Ontologie als versionierten Projektionsvertrag
- Graph-REST-only-Grenze
- Sizing gegen das aktuelle Geschäftsvorfall-Inventar
- Verbot zentraler KG-Ablage und sensibler Payloads

Der Check ist im strikten Quality Gate als
`notarial_ontology_storage_contract` verankert.
