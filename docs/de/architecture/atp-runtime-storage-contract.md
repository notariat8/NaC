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

Der nächste technische Track kann aus diesem Vertrag ein nicht-destruktives
ATP-Schema für die Anker ableiten. Danach kann eine schreibende Runtime-Kante
für Demo-Metadaten und später eine Graph-Projektion folgen.
