# ATP, JSON und Graph als Laufzeitmodell

Archivstatus seit 2026-07-06: Diese Zielarchitektur ist für den M365-MVP
abgelöst. Aktiver Pfad sind Teams, SharePoint-Team-Sites, Microsoft Graph
REST/MCP und optionale Graph-/Ontologie-Projektionen. Dieses Dokument bleibt
nur als Legacy-Referenz für eine spätere ausdrückliche ATP-Reaktivierung.

Status: Zielarchitektur-Entscheidung, ohne OCI-Apply und ohne produktiven
Schema-Apply.

## Entscheidung

NaC nutzt Oracle ATP als Laufzeit-Datenplattform. Das bedeutet nicht, dass das
fachliche Modell rein relational wird. Innerhalb von ATP werden drei Ebenen
getrennt:

1. **Transaktionale Anker:** Mandant, Benutzerbindung, Session, Vorgang,
   Prozessinstanz, Ereignis und Audit-Nachweis bekommen stabile technische
   Identitäten, Mandantengrenzen und Transaktionsregeln.
2. **Versionierte JSON-Payloads:** fachliche Zustandsdaten, Formularzustände,
   externe Rückläufe und Gate-Ergebnisse werden versioniert, validierbar und
   evolvierbar gespeichert.
3. **Graph- und Ontologie-Projektionen:** Beziehungen, Abhängigkeiten,
   Parallelität, kritische Pfade, XNP/SNP-Gates, Dokumentreferenzen,
   Fristen und Rollen werden als Graphmodell aus den Laufzeitereignissen
   abgeleitet.

Git bleibt Quelle für Code, IaC, Governance und freigegebene BPMN-Templates.
ATP wird System of Record für Laufzeitinstanzen und deren sichere Metadaten.

## Warum nicht SQL-only

Ein reines Tabellenmodell wäre für NaC zu starr. Notarielle Vorgänge
enthalten fachliche Beziehungen, externe Rückläufe, Nachweise, Abhängigkeiten
und parallele Pfade, die sich besser als Graph/Ontologie ausdrücken lassen:

- ein Immobilienkaufvertrag blockiert am kritischen Pfad oft auf externe
  Rückläufe;
- XNP/SNP, Grundbuch, Register, Kartenleser und Signatur erzeugen Gates statt
  nur Formularfelder;
- ein Schritt kann mehrere Nachweise verbrauchen und mehrere Folgepfade
  freigeben;
- fachliche Begriffe müssen auf Quellen, Rollen, Dokumentarten und
  Prozessschritte verweisbar bleiben.

Deshalb ist `schema` in NaC kein Synonym für ein vollständig relationales
Fachmodell. Gemeint ist ein stabiler Laufzeitvertrag für Speicherung,
Validierung, Zugriff, Audit und Projektionen.

## Warum nicht Graph-only

Ein reines Graphmodell wäre für die erste SaaS-Laufzeitgrenze ebenfalls
falsch. Authentifizierung, Session-Widerruf, Mandantentrennung, Idempotenz,
Transaktionen, Sperren, Audit und Statusabfragen brauchen stabile
transaktionale Anker. Diese Anker dürfen nicht aus einem frei wachsenden Graphen
erraten werden.

Der Graph ist daher keine zweite Wahrheit neben ATP, sondern eine Projektion auf
Basis von append-only Laufzeitereignissen und freigegebenen Templates.

## Laufzeitfluss

1. Ein BPMN-Template wird in Git reviewt und freigegeben.
2. Ein Mandant aktiviert eine konkrete Template-Version.
3. Ein Vorgang erzeugt in ATP Mandant-, Benutzer-, Vorgangs- und
   Prozessinstanz-Anker.
4. Jede relevante Aktion schreibt ein append-only `process_event`.
5. JSON-Payloads halten versionierte fachliche Metadaten und Gate-Ergebnisse.
6. Graph-Projektionen leiten daraus Beziehungen, Parallelpfade, Blocker,
   kritische Pfade und Nachweisbeziehungen ab.
7. Die UI liest zunächst nur redigierte Status- und Demo-Metadaten, keine
   Rohmandatsdaten.

## Ontologie-Kandidaten

Erste Knotentypen:

- `Tenant`
- `UserBinding`
- `Matter`
- `ProcessTemplate`
- `ProcessInstance`
- `ProcessStep`
- `Gate`
- `ExternalSystem`
- `DocumentReference`
- `Deadline`
- `FeeEvent`
- `AuditEvent`

Erste Kantenarten:

- `belongs_to`
- `acts_as`
- `requires`
- `blocks`
- `produces`
- `consumes`
- `sent_to`
- `received_from`
- `signed_by`
- `depends_on`
- `parallel_with`
- `critical_path_of`
- `fee_basis_for`
- `audited_by`

Diese Begriffe sind keine produktive Schemafreigabe. Sie sind der
Entscheidungsrahmen für die nächsten Vertrags- und Implementierungs-PRs.

## Oracle Graph Einordnung

Oracle beschreibt Graph Studio als Teil von Oracle Autonomous AI Database
Serverless. Es unterstützt Property Graphs für Abfragen und Analysen sowie
RDF/SPARQL/OWL für Knowledge-Graph- und Ontologie-Szenarien. Graph Studio nutzt
die Autonomous Database als Persistenzschicht.

Für NaC bedeutet das:

- Property Graph eignet sich für Prozessabhängigkeiten, Parallelität,
  kritische Pfade und Statusvisualisierung.
- RDF/OWL eignet sich später für Rechtsquellen-, Ontologie- und
  Begriffssysteme.
- Graph Studio ist ein Analyse- und Modellierungswerkzeug, nicht automatisch
  die produktive Runtime-UI.
- Aktivierung, Rollen wie `GRAPH_DEVELOPER` und etwaige ECPU-Auswirkungen
  brauchen einen separaten Apply- und Kosten-Gate.

Quelle: <https://www.oracle.com/de/database/integrated-graph-database/graph-faq/>

## Mandantenmodell

NaC trifft hier keine Entscheidung für eine PDB pro Mandant. Für den SaaS-Start
ist eine gemeinsame ATP mit expliziter Mandantengrenze, serverseitiger
Autorisierung, Tenant-Bindung, Audit und späteren DB-Policies der pragmatische
Startpunkt. Dedizierte Datenbanken, Schemas oder weitere Isolationsmodelle
bleiben spätere Optionen für regulatorische, vertragliche oder
Skalierungsanforderungen.

## Nicht-Ziele

- Kein OCI-Apply.
- Kein produktiver ATP-Schema-Apply.
- Keine Aktivierung von Graph Studio.
- Keine produktive XNP/SNP-Aktion.
- Keine Speicherung von Rohmandatsdaten.
- Keine Ablage produktiver Mandatsdaten in Git.

## Nächste Tracks

1. Laufzeitvertrag für relationale Anker, JSON-Payloads und Graph-Projektion
   definieren.
2. Immobilienkaufvertrag als synthetische ATP-Prozessinstanz mit XNP/SNP-,
   Grundbuch-, Register-, Kartenleser- und Vollzugs-Gates modellieren.
3. Kritischer Pfad, Parallelität und Dauerbänder aus der Graph-Projektion
   ableiten.
4. Editor-Grenze klären: BPMN-Template-Editor über Git/PR, Laufzeitstatus und
   Ereignisse über ATP.
