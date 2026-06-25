# Runtime-Status Wiring Runbook

Status: owner-freier Contract-first-Schnitt, kein OCI Apply.

Dieses Runbook beschreibt, wie der aktuelle notariat8 Portal-Start für den
ersten Immobilienkaufvertrag sicher vom Demo-Status zur späteren
ATP-Runtime-Speicherung geführt wird. Es ist kein Deploy- oder
Datenbank-Migrationsplan.

## Aktueller sicherer Pfad

Der aktuelle Pfad bleibt vollständig mandatsdatenfrei:

1. `notarkammer-first-immobilienkaufvertrag.metadata.json` liefert die
   Demo-Metadaten.
2. `InMemoryRuntimeStore` speichert diese Daten nur als Test- und
   Demo-Adapter.
3. Der Demo Runtime Seed erzeugt Tenant-, Vorgangs-, Prozess- und
   Audit-Metadaten.
4. `process_events` bleiben append-only.
5. Die runtime graph projection wird aus den Prozessereignissen abgeleitet.
6. Das Runtime-Status-Read-Model verdichtet die Prozesssicht.
7. Der Presenter erzeugt browser-sichere Texte.
8. `/workspace` und `/workspace/immobilienkaufvertrag` zeigen nur den
   Startstatus.

Die sichtbare Demo erklärt BPMN, XNP/SNP, Vollzug, Dauerband und kritischen
Pfad, ohne echte Beteiligte, Akteninhalte, Registerdaten oder Grundbuchdaten zu
laden.

## Späterer ATP-Pfad

ATP wird der Runtime-Datenspeicher für Mandanten, Benutzerbindungen,
Vorgänge, Prozessinstanzen, Prozessereignisse und Audit-Metadaten. Die erste
produktnahe Anbindung ersetzt nicht den Vertrag, sondern nur den Adapter:

- `RuntimeStoreAdapter` bleibt die fachliche Grenze.
- `process_events` bleiben append-only.
- Die graph projection wird weiterhin aus Ereignissen abgeleitet.
- Browser-Ausgaben enthalten keine internen IDs, keine Providerdetails, keine
  Claims, keine E-Mail-Adressen und keine Sessionwerte.
- Der Vollarbeitsbereich bleibt geschlossen, bis ein eigener Owner-Gate-Schnitt
  fachlich und technisch freigegeben ist.

## Fail-closed-Regeln

Der Statuspfad muss fail-closed geschlossen bleiben, wenn eine dieser
Bedingungen eintritt:

- Runtime Store nicht erreichbar.
- Prozessinstanz oder Ereignisse fehlen.
- Graph-Projektion kann nicht aus Ereignissen gebaut werden.
- Statusmodell enthält Mandatsdaten.
- Presenter würde interne Kennungen, Providerdetails oder Zugriffswerte
  ausgeben.
- Produktive XNP/SNP-Aktion wäre nötig.

## Owner-Gates

Diese Schritte brauchen weiter eine explizite Freigabe:

- ATP-Schema-Migration.
- ATP-Wallet-, Credential- oder Secret-Änderung.
- OCI Function Configuration oder Resource Manager Apply.
- Produktive XNP/SNP-Aktion.
- Schreiben echter Mandatsdaten.

Ohne diese Freigaben bleibt der Pfad ein sicherer Demo- und Contract-First-Pfad:
no mandate data, no OCI Apply, no productive XNP action.
