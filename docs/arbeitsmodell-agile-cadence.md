# Arbeitsmodell im Unternehmen: Agile und Kanban Cadence

## Ziel

Dieses Dokument legt waehbare Arbeitsmodi fuer den operativen Betrieb im Unternehmens-Fork fest.
Es enthaelt zwei freigegebene Methoden mit standardisierten Taktoptionen.

## Arbeitsmethoden

- `agile` ist der Startstandard fuer Einfuehrung und kontinuierliche Verbesserung.
- `kanban` ist als kontinuierlicher Flussmodus zulaessig.
- Die konkrete Auspraegung kann je Team variieren, muss aber im Repo dokumentiert sein.

## Agile: Sprintdauer (Auswahl)

Zulaessige Sprintdauern:

- `1w` (1 Woche)
- `2w` (2 Wochen)
- `4w` (4 Wochen)

## Agile: Daily-Dauer (Auswahl)

Zulaessige Daily-Dauern:

- `5m` (5 Minuten)
- `10m` (10 Minuten)
- `20m` (20 Minuten)

## Entscheidungshilfe

- `1w + 5m`: hohe Dynamik, kleine Teams, schneller Feedbackzyklus.
- `2w + 10m`: Standard fuer gemischte Fach-/Ops-Teams.
- `4w + 20m`: hohe regulatorische Pruefanteile, laengere Planungsfenster.

## Kanban: Review-Cadence (Auswahl)

Zulaessige Review-Cadences:

- `1w` (woechentlich)
- `2w` (zweiwoechentlich)
- `4w` (monatlicher Review-Zyklus)

## Kanban: Sync-Dauer (Auswahl)

Zulaessige Sync-Dauern:

- `5m`
- `10m`
- `20m`

Empfehlung:

- taeglicher Kurzsync in `5m|10m|20m`,
- Kanban-Review im Takt `1w|2w|4w`,
- Replenishment zusammen mit dem Review oder als eigener kurzer Termin.

## Verbindliche Dokumentation pro Team

Jedes Team dokumentiert im Unternehmens-Fork:

- gewaehlte Arbeitsmethode (`agile` oder `kanban`),
- bei `agile`: Sprintdauer und Daily-Dauer,
- bei `kanban`: Review-Cadence und Sync-Dauer,
- Startdatum der Cadence,
- verantwortliche Rolle fuer Anpassungen.

## Anpassungsregel

- Wechsel der Cadence erfolgt nur ueber Change Request.
- Wirkung wird nach 1-2 Zyklen bewertet.
- Nach Freigabe wird die neue Cadence versioniert uebernommen.
