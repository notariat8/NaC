# ATP Runtime Store Adapter

Status: owner-freier Contract-First-Schnitt, testbar ohne Live-OCI und ohne
Schema-Apply.

`RuntimeStoreAdapter` beschreibt die schmale Runtime-Grenze für Mandanten,
Benutzerbindungen, Vorgangsanker, Prozessinstanzen, Prozessereignisse und
Audit-Ereignisse. Die erste Implementierung ist `InMemoryRuntimeStore`; sie ist
ein deterministischer Testadapter und keine produktive ATP-Anbindung.

## Vertragsform

- Alle fachlichen Zustandsdaten liegen als versionierte JSON-Payloads vor.
- Prozessereignisse und Audit-Ereignisse sind append-only.
- Der Adapter speichert keine Secrets, keine Rohmandatsdaten und keine
  produktiven Mandatsdaten.
- Kein Live-OCI. Kein Schema-Apply. Keine produktive Graph-Aktivierung.
- Die spätere Graph-Projektion wird aus `process_events` abgeleitet und ist
  hier nur als deferred graph projection markiert.

Dieser Slice ist absichtlich disjunkt zu ATP-Schema- oder Deploy-PRs. Ein
späterer ATP-Adapter kann denselben Vertrag implementieren, ohne dass dieser
PR Datenbankobjekte anlegt oder Mandatsdaten berührt.
