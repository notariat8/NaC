# Arbeitsmodell im Unternehmen: Agile und Kanban Cadence

## Ziel

Dieses Dokument legt waehbare Arbeitsmodi für den operativen Betrieb im Unternehmens-Fork fest.
Es enthält zwei freigegebene Methoden mit standardisierten Taktoptionen.

## Arbeitsmethoden

- `agile` ist der Startstandard für Einführung und kontinuierliche Verbesserung.
- `kanban` ist als kontinuierlicher Flussmodus zulässig.
- Die konkrete Ausprägung kann je Team variieren, muss aber im Repo dokumentiert sein.

## Agile: Sprintdauer (Auswahl)

Zulässige Sprintdauern:

- `1w` (1 Woche)
- `2w` (2 Wochen)
- `4w` (4 Wochen)

## Agile: Daily-Dauer (Auswahl)

Zulässige Daily-Dauern:

- `5m` (5 Minuten)
- `10m` (10 Minuten)
- `20m` (20 Minuten)

## Entscheidungshilfe

- `1w + 5m`: hohe Dynamik, kleine Teams, schneller Feedbackzyklus.
- `2w + 10m`: Standard für gemischte Fach-/Ops-Teams.
- `4w + 20m`: hohe regulatorische Prüfanteile, längere Planungsfenster.

## Kanban: Review-Cadence (Auswahl)

Zulässige Review-Cadences:

- `1w` (woechentlich)
- `2w` (zweiwoechentlich)
- `4w` (monatlicher Review-Zyklus)

## Kanban: Sync-Dauer (Auswahl)

Zulässige Sync-Dauern:

- `5m`
- `10m`
- `20m`

Empfehlung:

- täglicher Kurzsync in `5m|10m|20m`,
- Kanban-Review im Takt `1w|2w|4w`,
- Replenishment zusammen mit dem Review oder als eigener kurzer Termin.

## Verbindliche Dokumentation pro Team

Jedes Team dokumentiert im Unternehmens-Fork:

- gewählte Arbeitsmethode (`agile` oder `kanban`),
- bei `agile`: Sprintdauer und Daily-Dauer,
- bei `kanban`: Review-Cadence und Sync-Dauer,
- Startdatum der Cadence,
- verantwortliche Rolle für Anpassungen.

## Anpassungsregel

- Wechsel der Cadence erfolgt nur über Change Request.
- Wirkung wird nach 1-2 Zyklen bewertet.
- Nach Freigabe wird die neue Cadence versioniert übernommen.
