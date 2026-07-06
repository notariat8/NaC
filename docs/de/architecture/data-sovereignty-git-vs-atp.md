# Datenhoheit: Git-Templates und ATP-Laufzeitdaten

Archivstatus seit 2026-07-06: Diese Datenhoheitsentscheidung ist für den
M365-MVP abgelöst. Aktive Datenhaltung startet über Teams,
SharePoint-Team-Sites und Microsoft Graph REST/MCP; ATP bleibt nur
Legacy-Referenz.

Status: entschieden für Zielarchitektur, noch ohne produktiven Schema-Apply.

Ergänzende Modellentscheidung:
[atp-graph-runtime-model.md](atp-graph-runtime-model.md) klärt, dass ATP die
Laufzeit-Datenplattform ist, aber nicht als reines SQL-Fachmodell verstanden
wird. NaC trennt relationale Sicherheitsanker, versionierte JSON-Payloads und
Graph-/Ontologie-Projektionen.

## Entscheidung

NaC trennt Git als Steuerungsebene von ATP als Laufzeit-Datenebene.

Git bleibt die verbindliche Quelle für:

- Produktcode, Tests und Release-Artefakte
- Infrastructure as Code und Betriebsrunbooks
- Governance-Regeln, Policies, Quality Gates und Review-Nachweise
- kanonische BPMN-Prozessdefinitionen und Template-Versionen
- synthetische Demo- und Testdaten

ATP wird die verbindliche Laufzeitdatenbank für:

- Mandanten, Benutzer- und Rollenbindungen
- serverseitige Sessions und Widerrufsinformationen
- Vorgangs- und Akten-Metadaten
- aktivierte Prozessversionen je Mandant
- Agent-Registrierungen, Sandbox-Bindungen und aktive Leases für die
  On-Prem-Agent-Runtime
- Prozessinstanzen, Prozessereignisse, Status und Fristen
- XNP/SNP-, Register-, Grundbuch- und Signatur-Gates als redaktionell sichere Metadaten
- Audit-Metadaten ohne Tokens, Claims, Secrets oder Rohmandatsdaten in Browserausgaben

Produktive Mandatsdaten werden nicht in Git gespeichert. Git darf weiterhin
synthetische Demo-Daten und fachliche Templates enthalten. Die alte
Tenant-Git-Repo-Logik ist damit Demo-/Legacy-Pfad, nicht Zielbild für den
produktiven SaaS-Betrieb.

## Begründung

Git ist stark für Nachvollziehbarkeit, Review und Versionierung von
Produktlogik. Git ist schwach für laufende SaaS-Daten:

- Klone, Forks und lokale Arbeitskopien vervielfältigen Daten.
- Mandanten-, Rollen- und Feldzugriff lassen sich nicht sauber pro Datensatz
  durchsetzen.
- Löschen, Korrigieren, Sperren und Aufbewahren sind mit Git-Historie schwer
  kontrollierbar.
- Gleichzeitige Laufzeitschreibvorgänge führen zu Merge- und
  Konsistenzproblemen.
- Abfragen über Akten, Fristen, Status, Ereignisse und Mandanten sind in Git
  keine tragfähige Datenbankoperation.

ATP ist für NaC die bessere Laufzeitgrenze, weil es Transaktionen,
strukturierte Abfragen, JSON-Flexibilität, Zugriffskontrolle, Backups und
serverseitige Persistenz verbindet. Das ist keine SQL-only-Entscheidung:
relationale Schlüssel bleiben die führende Sicherheits- und
Integritätsgrenze, JSON-Payloads tragen versionierte fachliche Zustände, und
Graph-/Ontologie-Projektionen bilden Beziehungen, Abhängigkeiten,
Parallelität und kritische Pfade ab. Die Basisdatenhaltung verschiebt sich
damit nicht zurück nach Git.

## Datenklassifizierung

| Datenart | Zielort | Regel |
| --- | --- | --- |
| Code, Tests, IaC, Policies | Git | Protected PR, Review und Quality Gate |
| BPMN-Prozessdefinition | Git | versioniertes Template, kein konkreter Mandatsinhalt |
| Aktivierte Prozessversion | ATP | Mandant verweist auf freigegebene Template-Version |
| Prozessinstanz | ATP | konkreter Vorgang, Status, Fristen, Ereignisse |
| Mandanten und Benutzerbindungen | ATP / IdP | ATP speichert NaC-Bindung, IdP authentifiziert |
| Agent- und Sandbox-Bindungen | ATP | User-/Tenant-/Agent-/Sandbox-Lease, kein lokaler NemoClaw-Alleinbesitz |
| Sessions | ATP | nur gehashte/abgeleitete Sessiondaten, keine Tokens oder Claims |
| Dokument-Metadaten | ATP | Dateiname, Typ, Status, Nachweisreferenz ohne Rohinhalt |
| Dokument-Binärdaten | später Object Storage | verschlüsselt, mit Retention und Audit nach [private-payload-target-design.md](private-payload-target-design.md) |
| Demo-Daten | Git erlaubt | nur synthetisch und ausdrücklich markiert |

## Erstes Laufzeitvertrags-Konzept

Das Zielmodell wird inkrementell aufgebaut. `Schema` meint hier keinen rein
relationalen Fachentwurf, sondern einen Laufzeitvertrag für transaktionale
Anker, JSON-Payloads, Audit und Graph-Projektionen. Für den nächsten Ausbau
reichen folgende logische Tabellen oder gleichwertige Store-Grenzen:

- `tenants`: Mandant, Status, Domainbindung, aktivierte Prozessversionen.
- `users`: NaC-Benutzerbindung, Rollenklasse, Mandantenzuordnung, IdP-Subjekt-Hash.
- `agent_registry`: Agent-Typen, Zielsystemklasse, freigegebene Fähigkeiten und
  Verweis auf Git-versionierte Verträge.
- `sandbox_bindings`: Bindung zwischen Tenant, Benutzer, Rolle, Vorgang,
  Agent und lokaler Sandbox-Referenz.
- `sandbox_leases`: aktive Lease, Ablauf, Revocation-Status und
  Wiederverwendungsgrenze für die On-Prem-Agent-Runtime.
- `matters`: Vorgangs-/Akten-Metadaten, Mandant, Usecase, Status, keine Rohdokumente.
- `process_templates`: aktivierbare Template-Referenz auf Git-Version, BPMN-ID, Hash.
- `process_instances`: konkrete Prozessinstanz je Vorgang, Template-Version, Laufzeitstatus.
- `process_events`: append-only Ereignisse, Gate-Ergebnisse, Fristen, XNP/SNP-Statusklassen.
- `document_metadata`: optionale Dokumentreferenzen, Klassifikation und Speicherverweis.

Die Tabellen dürfen keine Tokens, IdP-Claims, PINs, Kartenrohdaten,
Zugangsdaten oder unredigierte Mandatsinhalte speichern, solange die jeweilige
Datenschutz-, Aufbewahrungs- und Notariatsfreigabe nicht explizit definiert ist.

## Prozessregel

Ein Prozess hat zwei getrennte Lebenszyklen:

1. **Template-Lebenszyklus in Git:** Fachmodell, BPMN, Review, Freigabe, Version.
2. **Instanz-Lebenszyklus in ATP:** konkreter Vorgang, Status, Ereignisse,
   externe Rückläufe, Fristen, Audit-Metadaten.

Ein Merge in Git ändert keine laufende Akte automatisch. Ein Mandant muss eine
Template-Version aktivieren; Prozessinstanzen referenzieren danach die konkrete
Version. Dadurch bleiben Demo, Governance und produktive Laufzeitdaten getrennt.

## Nicht-Ziele

- Kein OCI-Apply durch diese Entscheidung.
- Kein produktiver ATP-Schema-Apply durch diese Entscheidung.
- Keine Migration echter Mandatsdaten.
- Keine Ablage von Rohdokumenten in ATP oder Git.
- Keine Aussage, dass XNP/SNP produktiv angebunden ist.

## Nächste Tracks

1. Laufzeitvertragsplan für Anker, JSON-Payloads und Graph-Projektionen rund um
   `tenants`, `matters`, `process_templates`, `process_instances` und
   `process_events`.
2. Migrationspfad für synthetische Demo-Git-Daten in einen ATP-basierten
   Demo-Read-Model-Store.
3. `/workspace`-Status aus ATP-Metadaten lesen, ohne Rohmandatsdaten zu laden.
4. Immobilienkaufvertrag als erste Prozessinstanz mit XNP/SNP-, Grundbuch-,
   Register- und Vollzugs-Gates abbilden.
