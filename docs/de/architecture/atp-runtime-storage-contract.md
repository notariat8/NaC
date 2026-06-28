# ATP Runtime-Storage-Vertrag

Dieser Vertrag schneidet aus dem ATP-Graph-Zielbild den ersten
Implementierungs-Track heraus. Er aktiviert noch kein produktives Schema und
keine Graph-Funktion. Er legt fest, welche Laufzeitobjekte NaC in ATP halten
darf und wie diese später in eine Graph- oder Ontologie-Sicht projiziert
werden können.

Der maschinenlesbare Vertrag liegt in
`workflows/contracts/atp-runtime-storage.contract.json`.

## Entscheidung

Git bleibt die Quelle der Wahrheit für Code, IaC, Governance,
BPMN-Templates und synthetische Demo-Daten. ATP wird die Laufzeit-Datenebene
für Mandanten, Benutzerbindungen, Sessions, Vorgänge, Prozessinstanzen,
Prozessereignisse und Audit-Metadaten.

Das ist keine rein relationale Fachentscheidung. Das Modell trennt drei
Ebenen:

1. Transaktionale Anker für stabile IDs, Status und Tenant-Grenzen.
2. Versionierte JSON-Payloads für fachliche Zustands- und Gate-Metadaten.
3. Graph-Projektionen für Abhängigkeiten, Parallelität, kritische Pfade,
   XNP/SNP-Gates, Dokumentreferenzen, Fristen, Rollen und Audit-Beziehungen.

## Datenmodell-Slice v0.1

Der erste verbindliche Datenmodell-Slice ist `runtime_graph_metadata_v0`.
Er gilt nur für sichere Runtime-Metadaten im ersten
`immobilienkaufvertrag`-Pfad. Die Quelle bleibt ATP:

- transaktionale Anker für Mandant, Vorgang, Prozessinstanz,
  append-only Prozessereignisse und Audit-Metadaten;
- versionierte JSON-Payloads für Status, Gates, Dauerbänder, externe
  Systemgrenzen und redigierte Audit-Referenzen;
- daraus abgeleitete Graph-/Ontologie-Kandidaten für Abhängigkeiten,
  Parallelgruppen, kritischen Pfad und externe Gate-Berührungen.

Oracle Graph Studio ist in diesem Slice kein Runtime-Bestandteil. Es bleibt ein
späteres Analyse- und Modellierungswerkzeug nach separatem Owner-, Apply- und
Kosten-Gate.

## Erste Anker

- `tenants`
- `user_bindings`
- `sessions`
- `matters`
- `process_templates`
- `process_instances`
- `process_events`
- `audit_events`

Diese Anker dürfen im ersten Schritt nur sichere Metadaten aufnehmen. Rohdaten
aus Mandaten, Urkunden, Ausweisen, Vollmachten, Registerabrufen oder
Grundbuchdaten brauchen einen eigenen Design-, Schutz- und Apply-Gate.

## Umsetzungsgrenze v0.1

Der `runtime_graph_metadata_v0`-Slice setzt nicht alle Zielanker über dieselbe
Adapterfläche um:

- `tenants`, `user_bindings`, `matters`, `process_instances`,
  `process_events` und `audit_events` sind die erste
  `RuntimeStoreAdapter`-Grenze für Graph-Status und Tests.
- `process_templates` ist im Schema-Artefakt ein Anker, wird im v0.1-Adapter
  aber nur als freigegebene Template-Referenz im `process_instances`-Payload
  getragen. Eine eigene Template-Adaptermethode bleibt deferred.
- `sessions` gehören zum ATP-Runtime-Zielmodell, sind aber in diesem
  Graph-Slice externalisiert: der Portal-Session-Pfad läuft über
  `nac_identity.session_store.AtpSessionStore` und
  [atp-onboarding-request-store.sql](../../../deploy/database/atp-onboarding-request-store.sql).

Damit bleibt die Prozessgraph-Projektion klar auf `process_events` begrenzt und
vermischt keine Auth-/Session-Widerrufslogik mit Vorgangsstatus.

## Schema-Artefakt

Der erste technische Schema-Zuschnitt liegt als nicht-destruktives Artefakt in
`deploy/database/atp-runtime-anchor-schema.sql`. Das Artefakt ist noch kein
Apply-Auftrag. Es beschreibt idempotente Runtime-Anker für:

- `nac_tenants`
- `nac_user_bindings`
- `nac_matters`
- `nac_process_templates`
- `nac_process_instances`
- `nac_process_events`
- `nac_audit_events`

Jede mandantenbezogene Runtime-Tabelle traegt eine Tenant-Grenze. Fachliche
Zustandsdetails werden als validierte JSON-Payloads gehalten, damit später
eine Graph- oder Ontologie-Projektion daraus entstehen kann. Prozessereignisse
sind append-orientiert; sie ersetzen keine Audit-Freigabe und enthalten keine
Rohdaten aus Mandaten.

## JSON-Payload-Regeln

Jeder Runtime-Payload braucht mindestens:

- eine Schema-Version,
- einen Payload-Typ,
- eine Redaktionsklasse,
- eine Referenz auf die freigegebene Template-Version, wenn der Payload zu
  einem Vorgang gehoert.

Erlaubte Starttypen sind Status-, Gate-, Dauer-, externe Gate- und
Audit-Metadaten. Produktive Mandatsinhalte sind nicht Bestandteil dieses
Vertrags.

## Graph-Projektion

Die Graph-Projektion ist zunaechst nur ein Vertrag. Sie beschreibt, welche
Knoten und Kanten aus den transaktionalen Ankern und JSON-Payloads entstehen
dürfen. Sie aktiviert weder Graph Studio noch eine produktive Graph-Pipeline.

Wichtige Knoten:

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

Wichtige Kanten:

- `depends_on`
- `parallel_with`
- `critical_path_of`
- `sent_to`
- `received_from`
- `requires`
- `blocks`
- `fee_basis_for`
- `audited_by`

## Guardrails

- Kein produktiver Schema-Apply durch diesen PR.
- Keine produktive Graph-Aktivierung durch diesen PR.
- Keine Mandatsdaten in Git.
- Keine Secret-Werte in Git oder Chat.
- Keine OCI-Schreibaktion ohne separates Owner-Apply-Gate.

## Naechster Track

Der nächste technische Track bleibt metadata-only, bis der
[private-operating-frame-gate.md](private-operating-frame-gate.md) erfüllt ist.
Erst danach darf ein separates ATP-Private-Payload-Schema entworfen werden.
Bis dahin kann NaC nur nicht-destruktive Anker, Demo-Metadaten und
Graph-Projektionen ohne Rohmandatsdaten ausbauen.
