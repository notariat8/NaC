# KG-Editor-Workstream

Status: MVP umgesetzt am 2026-05-15

Der KG-Editor ist die fachliche Bearbeitungsschicht ueber den usecase-lokalen
statischen Knowledge Graphs. Die Dateien
[usecases/*/knowledge-graph.graph.json](../../usecases) bleiben die
maschinenlesbare Repraesentation. Fachpersonal soll diese JSON-Dateien nicht
direkt bearbeiten.

## Produktentscheidung

Fuer notarielle Vorgangsarten fuehrt der Editor keine echten Mandatsdaten in Git
ein. `value`-Felder bleiben leer und sind in der Editor-Ansicht gesperrt. Der
Editor zeigt stattdessen Status, Rollen, offene Angaben, Dokumente,
Entscheidungen, Gates und Evidence-Metadaten.

Der kleinste sinnvolle Endnutzer-Flow ist:

1. ChatGPT oder ein anderes LLM nimmt die natuerliche Anweisung entgegen.
2. Die Runtime liest den passenden KG ueber [src/notary_kg/editor.py](../../src/notary_kg/editor.py).
3. Fachpersonal sieht vier Tabs: Offene Angaben, Dokumente, Entscheidungen und
   Gates/Evidence.
4. Aenderungen entstehen als strukturierter Patch nach
   [schemas/kg-editor-patch.schema.json](../../schemas/kg-editor-patch.schema.json).
5. Der Patch wird validiert, auf Datenschutz geprueft, als Diff angezeigt und
   erst nach Bestaetigung per Pull Request umgesetzt.

## Ausfuehrbare Oberflaeche

Die aktuelle CLI erzeugt eine sichere Editor-View fuer jeden Usecase-Slug:

```bash
python scripts/notary_kg.py --repo-root . editor-view immobilienkaufvertrag
python scripts/notary_kg.py --repo-root . --format json editor-view immobilienkaufvertrag
```

Die Ausgabe ist kein finaler Web-Editor, aber sie ist ein implementierter
Vertrag fuer einen GitHub-backed Sidecar-Editor oder eine spaetere ChatGPT App.
Der Workflow-Vertrag steht in
[workflows/contracts/kg-editor.contract.json](../../workflows/contracts/kg-editor.contract.json).

## Tabs

| Tab | Quelle im KG | Bedienmodell |
| --- | --- | --- |
| Offene Angaben | `required_information` | Checkliste mit Status, Rolle und Pflichtkontext |
| Dokumente | `documents` | Dokumentenstatus mit Quelle und Datenschutzmarkierung |
| Entscheidungen | `decisions` | Dropdown-/Optionsmodell mit Status |
| Gates/Evidence | `gates`, `evidence` | Review-Liste fuer Freigaben und Nachweise |

## Guardrails

- Keine direkte JSON-Bearbeitung durch Fachpersonal.
- Keine echten Personen-, Grundstuecks-, Gesundheits-, Familien-, Nachlass-,
  Firmen- oder Secret-Daten im Repo.
- Keine Aenderung von `value`-Feldern ueber den Editor.
- Keine blinden Ueberschreibungen; Aenderungen laufen ueber Patch, Validierung,
  Diff, Bestaetigung und Pull Request.
- Graph-Visualisierung ist nachrangig; operativ wichtiger sind offene Punkte,
  Blocker, Verantwortlichkeiten und Review-Gates.

## Integrationspfad

MVP 1 ist der GitHub-backed KG-Editor. MVP 2 ist eine ChatGPT-App mit
eingebettetem Sidecar-Editor. MVP 3 ist eine Low-Code-Konfiguration, damit neue
Usecases ohne neue UI-Programmierung als Formulare, Checklisten und Review-Gates
gerendert werden koennen.

Fuer spaetere OpenAI-Integration sind die offiziellen Pfade
[Apps SDK](https://developers.openai.com/apps-sdk/) und
[GPT Actions](https://platform.openai.com/docs/actions) als technische
Integrationsziele vorgemerkt. Die fachliche Wahrheit bleibt trotzdem Git plus
Review plus Freigabe.
