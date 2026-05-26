# Idee: BPMN-2.0-Workflows als kontrollierter GitHub-Projects-Layer

## Idee

GitHub Issues und Projects koennten als kontrollierte Ausfuehrungsebene fuer modellierte BPMN-2.0-Workflows genutzt werden.

Der Kern waere eine Trennung zwischen:

- **BPMN 2.0 als Prozessmodell und Visualisierung**
- **GitHub Issues/Projects als operativer Ist-Zustand**
- **einer API/GitHub-App als einzige schreibende Instanz**

Damit koennten Nutzer Workflows, Swimlanes, Assignments und Abhaengigkeiten sehen, aber operative Veraenderungen wie Verschieben, Statuswechsel oder Loeschen wuerden nicht manuell im Board passieren, sondern kontrolliert ueber die API.

## Grobes Mapping

- BPMN Pool/Lane -> Organisation, Rolle, Team oder System
- BPMN Task -> Issue, Arbeitsschritt oder Checkpoint
- BPMN Gateway -> Entscheidung, Freigabe oder Bedingung
- BPMN Sequence Flow -> Prozessreihenfolge
- BPMN Message Flow -> Uebergabe zwischen Rollen/Systemen
- GitHub Assignees -> verantwortliche Person(en)
- GitHub Labels/Project Fields -> Status, Phase, Prioritaet, Lane, SLA, Kategorie
- GitHub Issue Dependencies -> `blocked by` / `blocking`
- GitHub Project Views -> Board, Tabelle, Roadmap, Charts

## Governance-Modell

User und Teams erhalten nur Lesezugriff auf Projects und die noetigen Repository-Rechte, damit sie alles sehen koennen.

Schreibzugriffe laufen ueber eine GitHub App oder API-Automation mit gezielten Rechten, z. B.:

- Issues erstellen oder aktualisieren
- Project-Felder setzen
- Assignees zuweisen
- Dependencies pflegen
- Statusuebergaenge anhand des BPMN-Modells validieren

So koennten Menschen das System beobachten und diskutieren, ohne aus Versehen Items im Board zu verschieben oder Workflow-Zustaende zu veraendern.

## Moeglicher MVP

1. BPMN-XML oder eine vereinfachte Prozessdefinition einlesen.
2. Lanes, Tasks und Kanten extrahieren.
3. GitHub Issues fuer Tasks erzeugen oder synchronisieren.
4. Project-Felder wie `Lane`, `Status`, `Phase`, `Owner Role` und `Blocked By` setzen.
5. Einen BPMN-Viewer bauen, der den Soll-Prozess zeigt und Live-Status aus GitHub einblendet.
6. Optional: Statuswechsel nur erlauben, wenn vorgelagerte Dependencies erledigt sind.

## Nutzen

- Swimlanes und Prozesslogik bleiben visuell nachvollziehbar.
- GitHub bleibt das operative System fuer Issues, PRs und Projektstatus.
- Assignments und Dependencies werden maschinenlesbar.
- Read-only Boards reduzieren versehentliche manuelle Aenderungen.
- Die Automation kann als Audit- und Governance-Layer dienen.

## Offene Fragen

- Soll BPMN die fuehrende Quelle sein, oder sollen GitHub Issues die fuehrende Quelle bleiben?
- Brauchen wir vollstaendige BPMN-2.0-Semantik oder reicht ein pragmatischer Subset?
- Welche Felder sollen im Project standardisiert werden?
- Wie streng sollen Statusuebergaenge validiert werden?
- Soll der BPMN-Viewer nur lesen oder auch geplante Aenderungen als Vorschlag erzeugen?
