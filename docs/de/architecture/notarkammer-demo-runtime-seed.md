# Notarkammer Demo Runtime Seed

Status: owner-freier Contract-first-Slice, kein produktiver Cloud-Apply.

Der Demo Runtime Seed verbindet den mandatsdatenfreien
Immobilienkaufvertrag-Fixture mit dem `RuntimeStoreAdapter`. Er schreibt nur
Demo-Metadaten für Tenant, Vorgang, Prozessinstanz, Prozessereignisse und
Audit. Aus den Prozessereignissen kann die Runtime Graph Projection eine
sichtbare Graph-Sicht mit XNP/SNP-Gates, externen Grenzen, Parallelgruppen,
Dauerbändern und kritischem Pfad ableiten.

Der Seed ist der erste konkrete Fixture für `runtime_graph_metadata_v0`. Die
Fixture enthält ein strukturiertes `runtime_event_profile`; daraus schreibt der
Seed append-only `process_events` mit Abhängigkeiten, Dauerbändern,
Parallelgruppen, externen Boundary-Labels und kritischem Pfad.

## Grenzen

- Keine Mandatsdaten.
- Keine produktive XNP/SNP-Aktion.
- Kein M365-/SharePoint-/Cloud-Apply.
- Keine Secrets.
- Keine echten Register- oder Grundbuchdaten.

Der Seed ist ein Vorführ- und Testvertrag. Eine produktive Speicherung in der
M365/SharePoint-Runtime oder einem späteren Event-Journal bleibt ein eigener
Owner-Gate-Schnitt.
