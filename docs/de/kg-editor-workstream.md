# KG-Editor-Workstream

Status: MVP umgesetzt am 2026-05-15

Der KG-Editor ist die fachliche Bearbeitungsschicht über den usecase-lokalen
statischen Knowledge Graphs. Die Dateien
[usecases/*/knowledge-graph.graph.json](../../usecases) bleiben die
maschinenlesbare Repräsentation. Fachpersonal soll diese JSON-Dateien nicht
direkt bearbeiten.

## Produktentscheidung

Für notarielle Vorgangsarten führt der Editor keine echten Mandatsdaten in Git
ein. `value`-Felder bleiben leer und sind in der Editor-Ansicht gesperrt. Der
Editor zeigt stattdessen Status, Rollen, offene Angaben, Dokumente,
Entscheidungen, Gates und Evidence-Metadaten.

Der kleinste sinnvolle Endnutzer-Flow ist:

1. ChatGPT oder ein anderes LLM nimmt die natürliche Anweisung entgegen.
2. Die Runtime liest den passenden KG über [src/notary_kg/editor.py](../../src/notary_kg/editor.py).
3. Fachpersonal sieht vier Tabs: Offene Angaben, Dokumente, Entscheidungen und
   Gates/Evidence.
4. Änderungen entstehen als strukturierter Patch nach
   [schemas/kg-editor-patch.schema.json](../../schemas/kg-editor-patch.schema.json).
5. Der Patch wird validiert, auf Datenschutz geprüft, als Diff angezeigt und
   erst nach Bestätigung per Pull Request umgesetzt.

## Ausführbare Oberfläche

Die aktuelle CLI erzeugt eine sichere Editor-View für jeden Usecase-Slug:

```bash
python scripts/nac.py kg editor-view immobilienkaufvertrag
python scripts/nac.py kg --format json editor-view immobilienkaufvertrag
```

Die Ausgabe ist kein finaler Web-Editor, aber sie ist ein implementierter
Vertrag für einen GitHub-backed Sidecar-Editor oder eine spätere ChatGPT App.
Der Workflow-Vertrag steht in
[workflows/contracts/kg-editor.contract.json](../../workflows/contracts/kg-editor.contract.json).
Warum die sichtbare Bedienung einen prüfbaren technischen Kern braucht,
beschreibt
[ausfuehrungsmodell.md](ausfuehrungsmodell.md).

## Tabs

| Tab | Quelle im KG | Bedienmodell |
| --- | --- | --- |
| Offene Angaben | `required_information` | Checkliste mit Status, Rolle und Pflichtkontext |
| Dokumente | `documents` | Dokumentenstatus mit Quelle und Datenschutzmarkierung |
| Entscheidungen | `decisions` | Dropdown-/Optionsmodell mit Status |
| Gates/Evidence | `gates`, `evidence` | Review-Liste für Freigaben und Nachweise |

## Guardrails

- Keine direkte JSON-Bearbeitung durch Fachpersonal.
- Keine echten Personen-, Grundstücks-, Gesundheits-, Familien-, Nachlass-,
  Firmen- oder Secret-Daten im Repo.
- Keine Änderung von `value`-Feldern über den Editor.
- Keine blinden Überschreibungen; Änderungen laufen über Patch, Validierung,
  Diff, Bestätigung und Pull Request.
- Graph-Visualisierung ist nachrangig; operativ wichtiger sind offene Punkte,
  Blocker, Verantwortlichkeiten und Review-Gates.

## Integrationspfad

MVP 1 ist der GitHub-backed KG-Editor. MVP 2 ist eine ChatGPT-App mit
eingebettetem Sidecar-Editor. MVP 3 ist eine Low-Code-Konfiguration, damit neue
Usecases ohne neue UI-Programmierung als Formulare, Checklisten und Review-Gates
gerendert werden können.

Für spätere OpenAI-Integration sind die offiziellen Pfade
[Apps SDK](https://developers.openai.com/apps-sdk/) und
[GPT Actions](https://platform.openai.com/docs/actions) als technische
Integrationsziele vorgemerkt. Die fachliche Wahrheit bleibt trotzdem Git plus
Review plus Freigabe.
