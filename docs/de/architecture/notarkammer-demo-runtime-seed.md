# Notarkammer Demo Runtime Seed

Status: owner-freier Contract-first-Slice, kein OCI-Apply.

Der Demo Runtime Seed verbindet den mandatsdatenfreien
Immobilienkaufvertrag-Fixture mit dem ATP Runtime Store Adapter. Er schreibt nur
Demo-Metadaten für Tenant, Vorgang, Prozessinstanz, Prozessereignisse und Audit.
Aus den Prozessereignissen kann die Runtime Graph Projection eine sichtbare
Graph-Sicht mit XNP/SNP-Gates, externen Grenzen, Parallelgruppen, Dauerbändern
und kritischem Pfad ableiten.

## Grenzen

- Keine Mandatsdaten.
- Keine produktive XNP/SNP-Aktion.
- Kein OCI-Apply.
- Keine Secrets.
- Keine echten Register- oder Grundbuchdaten.

Der Seed ist ein Vorführ- und Testvertrag. Eine produktive Speicherung in ATP
bleibt ein eigener Owner-Gate-Schnitt.
