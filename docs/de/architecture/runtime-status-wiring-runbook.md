# Runtime-Status Wiring Runbook

Status: owner-freier Contract-first-Schnitt, kein produktiver Cloud-Apply.

Dieses Runbook beschreibt, wie der aktuelle notariat8 Portal-Start für den
ersten Immobilienkaufvertrag sicher vom Demo-Status zur späteren
M365/SharePoint-Runtime und einem späteren Event-Journal geführt wird. Es ist
kein Deploy-, Datenbank- oder SharePoint-Apply-Plan.

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

## Späterer M365-/Event-Journal-Pfad

M365/SharePoint-Listen und ein späteres Event-Journal werden die
Runtime-Datenspeicher für Mandanten, Benutzerbindungen, Vorgänge,
Prozessinstanzen, Prozessereignisse und Audit-Metadaten. Die erste produktnahe
Anbindung ersetzt nicht den Vertrag, sondern nur den Adapter:

- `RuntimeStoreAdapter` bleibt die fachliche Grenze.
- `process_events` bleiben append-only.
- Die graph projection wird weiterhin aus Ereignissen abgeleitet.
- Browser-Ausgaben enthalten keine internen IDs, keine Providerdetails, keine
  Claims, keine E-Mail-Adressen und keine Sessionwerte.
- Der Vollarbeitsbereich bleibt geschlossen, bis ein eigener Owner-Gate-Schnitt
  fachlich und technisch freigegeben ist.

## M365-/JSON-Metadata-Seam

Der aktive Metadata-Seam bleibt datenbankfrei und kann für den ersten
Vorgangsstatus mit einer späteren Graph-/SharePoint-Quelle verbunden werden.
Alte ATP-Werte werden nicht mehr angebunden, sondern fail-closed als archiviert
behandelt. Der geschützte erste Vorgangsstatus kann per Umgebungsschalter
geprüft werden, ohne eine Datenbankmigration, Wallet- oder Secret-Änderung oder
ein Cloud-Apply auszulösen:

- `NAC_FIRST_MATTER_RUNTIME_SOURCE` aktiviert den Metadata-Seam für die Werte
  `json`, `metadata-json`, `sharepoint`, `m365` oder `m365-sharepoint`.
- `NAC_FIRST_MATTER_RUNTIME_OBJECT_KEY` überschreibt optional den logischen
  Runtime-Objektschlüssel. Ohne Wert gilt
  `DEMO-PROCESS-IMMOBILIENKAUF-01`.
- `NAC_FIRST_MATTER_RUNTIME_PAYLOAD_COLUMN` überschreibt optional die
  JSON-Payload-Spalte. Ohne Wert gilt `payload_json`.
- Der Reader nutzt später Graph REST oder einen MCP-Server, der Graph REST
  intern kapselt. Direkte alte SharePoint APIs, SDK-only-Zugriffe und Oracle
  ATP-Reader gehören nicht zum aktiven Pfad.
- Wenn der Reader noch nicht bereitsteht oder eine archivierte ATP-Quelle
  ausgewählt wird, liefert die Route keine Packaged-Fallback-Daten, sondern
  bleibt fail-closed geschlossen.

## Fail-closed-Regeln

Der Statuspfad muss fail-closed geschlossen bleiben, wenn eine dieser
Bedingungen eintritt:

- Runtime Store nicht erreichbar.
- Metadata-Seam aktiviert, aber kein freigegebener Reader vorhanden.
- Archivierte ATP-Quelle ausgewählt.
- Prozessinstanz oder Ereignisse fehlen.
- Graph-Projektion kann nicht aus Ereignissen gebaut werden.
- Statusmodell enthält Mandatsdaten.
- Presenter würde interne Kennungen, Providerdetails oder Zugriffswerte
  ausgeben.
- Produktive XNP/SNP-Aktion wäre nötig.

## Owner-Gates

Diese Schritte brauchen weiter eine explizite Freigabe:

- M365-/SharePoint-Listen-Provisioning.
- Graph-Berechtigungsänderungen.
- Serverless Function Configuration.
- Produktive XNP/SNP-Aktion.
- Schreiben echter Mandatsdaten.

Ohne diese Freigaben bleibt der Pfad ein sicherer Demo- und Contract-First-Pfad:
no mandate data, no productive cloud apply, no productive XNP action.
