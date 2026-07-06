# Omnigraph Als Optionale Ontologie-Projektion

Status: Architektur-Decision-Note
Letzte inhaltliche Anpassung: 2026-07-06

## Entscheidung

[ModernRelay/omnigraph](https://github.com/ModernRelay/omnigraph) wird für
NaC als optionaler Kandidat für eine spätere Ontologie- und
Agent-Kontext-Projektion geführt. Es ist nicht Teil des M365-MVP, keine
führende Datenhaltung, keine BPMN-Engine und kein Ersatz für Microsoft Graph
REST, SharePoint, Teams oder NeMo Agent Toolkit / AI-Q.

Die aktive MVP-Entscheidung bleibt:

- BPMN 2.0 ist die fachliche Prozessquelle.
- Usecase-lokale Knowledge Graphs bleiben die kanonische Ontologie-Baseline.
- Teams, Microsoft-365-Gruppe und SharePoint-Team-Site sind die erste
  Datenhaltung.
- Microsoft Graph REST oder MCP-Server auf Graph-REST-Basis sind die
  Integrationsgrenze.
- NeMo Agent Toolkit / AI-Q bleibt die führende agentische Runtime.

## Einordnung

Omnigraph passt konzeptionell zu NaC, weil es Graph-Kontext,
Agenten-Branches, Policy-Grenzen und Retrieval über strukturierte Graphdaten
adressiert. Für langlaufende notarielle Workflows kann das später helfen,
wenn Agenten Fragen über Prozessstatus, offene Angaben, Evidence, Rollen,
Dokument-Pointer und kritische BPMN-Gates beantworten sollen.

Der richtige Platz ist aber eine abgeleitete Projektion:

```text
BPMN + usecase-lokaler KG + SharePoint-Metadaten + Audit-Ereignisse
  -> nac-ontology-graph-mcp
    -> optionale Omnigraph-Projektion
      -> NeMo/AI-Q-Agenten lesen Kontext
```

Omnigraph darf dabei keine Rohmandatsdaten, keine Dokumentinhalte, keine
Ausweisdaten, keine Register- oder Grundbuchrohdaten und keine Secrets halten.
Zugriff, Vertretung, Zweckbindung und Schreibfreigaben bleiben im
NaC-Rollen-, Akten-, Zweck- und Vertretungsgate.

## Relevanz Für BPMN

Omnigraph ist für BPMN nur indirekt relevant. Es kann BPMN-Modelle in
abfragbare Knoten und Kanten projizieren, zum Beispiel:

- `ProcessTemplate`
- `BpmnTask`
- `Gate`
- `Role`
- `DataClass`
- `EvidenceRequirement`
- `DocumentPointer`
- `Matter`
- `ProcessInstance`
- `AccessGrant`
- `AuditEvent`

Das unterstützt Fragen wie:

- Welche BPMN-Gates blockieren den Vollzug?
- Welche Evidence fehlt für den nächsten Schritt?
- Welche Rolle darf eine Aufgabe fachlich freigeben?
- Welche Dokument-Pointer gehören zu welchem Gate?

Omnigraph ersetzt dabei nicht BPMN-Token-Semantik, bpmn-js, NaC-Validatoren,
Pull-Request-Review oder menschliche Freigaben.

## Grenzen Für Den MVP

Nicht zulässig für den MVP:

- Omnigraph als führende Datenhaltung,
- Omnigraph als SharePoint-Ersatz,
- Omnigraph als BPMN-Engine,
- Omnigraph als alleinige Berechtigungsentscheidung,
- Bulk-Kopie von Outlook, Teams, OneDrive oder SharePoint in eine
  Agenten-Memory,
- produktive Rohdaten-Projektion ohne Private-Payload-Gate.

## Evaluationspfad

Eine spätere Evaluation ist sinnvoll, wenn die M365-Datenebene stabil ist und
ein erster NeMo/AI-Q-Workflow über `nac-workflow-mcp`,
`nac-access-grant-mcp` und `nac-audit-evidence-mcp` läuft.

Die Evaluation muss read-only starten:

1. Export eines synthetischen Usecase-KG und eines BPMN-Modells in ein
   Omnigraph-kompatibles Schema.
2. Import nur mit Demo- oder Template-Daten.
3. Abfragen zu offenen Angaben, Evidence, kritischem Pfad und Rollenbindung.
4. Vergleich gegen bestehende NaC-Validatoren.
5. Entscheidung, ob `nac-ontology-graph-mcp` eine Omnigraph-Backend-Option
   bekommt.

Ein produktiver Einsatz braucht danach einen eigenen Contract, Validator,
Sicherheitsreview und Owner-Gate.
