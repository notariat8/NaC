# ATP Runtime Graph Projection

Status: owner-freier Contract-first-Slice, kein OCI-Apply.

Dieser Vertrag ergänzt den ATP Runtime Store um eine testbare Graph-Projektion aus
`process_events`. Die Projektion erzeugt eine mandatsdatenfreie Metadatensicht für
Demo, Review und spätere Oracle-Graph-Aktivierung.

## Zweck

Die Runtime-Events bleiben die Append-only-Quelle. Daraus wird eine Graph-Sicht
abgeleitet:

- Knoten für Prozessinstanz, Gates und externe Systeme.
- Kanten für Event-Gates, externe Berührungspunkte und Abhängigkeiten.
- Parallelgruppen für fachlich gleichzeitig mögliche Schritte.
- Dauerbänder für Stunden, Tage, Wochen oder Monate.
- kritischer Pfad für Schritte, die den Vollzug voraussichtlich bestimmen.

## Guardrails

- Kein Live-OCI.
- Kein Schema-Apply.
- Keine Secrets.
- Keine Mandatsdaten.
- Keine produktive XNP/SNP-Aktion.
- Keine rohen Browser-Identifier als fachlicher Output.

## Oracle-Graph-Studio-Grenze

Die erste Umsetzung ist bewusst eine Python-Projektion aus freigegebenen
Runtime-Metadaten. Oracle Graph Studio, Property Graph, PGQL und RDF/OWL sind
hier nur Ziel- und Analysebegriffe. Graph Studio ist keine Abhängigkeit der
Runtime-UI und keine produktive Aktivierung.

Eine spätere Oracle-Graph- oder PGQL-Nutzung braucht ein eigenes Owner-Apply-
und Kosten-Gate, inklusive Rollenfreigabe wie `GRAPH_DEVELOPER`.

## Runtime-Vokabular v0.1

Die Python-Projektion nutzt bewusst ein kleines Runtime-Vokabular und mappt es
auf die kanonischen Architekturbegriffe:

| Runtime-Typ | Kanonischer Begriff |
| --- | --- |
| `process_instance` | `ProcessInstance` |
| `gate` | `Gate` |
| `external_system` | `ExternalSystem` |
| `has_event_gate` | `has_step` |
| `touches_gate` | `external_gate_touchpoint` |
| `depends_on` | `depends_on` |

Neue Knoten- oder Kantentypen brauchen eine Contract-Änderung und Validator-
Nachweis, bevor sie in der Runtime-Projektion auftauchen.
