# Parallelbetrieb mit Version-Binding

## Ziel

Dieses Dokument regelt den Mischbetrieb, wenn alte und neue Prozessversionen gleichzeitig rechts- und revisionssicher betrieben werden müssen.

Kernprinzip: **Die beim Vorgangsstart gültige Prozessversion bleibt für diesen Vorgang verbindlich.**

## Verbindliche Regeln

1. Jeder neue Vorgang bekommt beim Start eine Prozessversions-Referenz (`process_version`).
2. `process_version` verweist auf ein freigegebenes Release-Tag im Unternehmens-Fork.
3. Laufende Vorgänge wechseln nicht automatisch auf spätere Releases.
4. Neue Releases gelten nur für Vorgänge, die nach Freigabe neu gestartet werden.
5. Ausnahmen (manueller Umzug eines Vorgangs auf neue Version) brauchen dokumentierte Einzelentscheidung.

## Mindestmetadaten je Vorgang

- `request_id`
- `process_domain` (z. B. `notary`, `invoice`, `tax`)
- `process_version` (z. B. `v1.6.2`)
- `version_bound_at` (Zeitpunkt der Bindung)
- `bound_by_role` (Rolle/Person, die den Vorgang gestartet hat)
- `compliance_basis` (optional, z. B. interne Richtlinie oder externer Bezug)

## Audit-Nachweis

Für jeden Vorgang muss reproduzierbar sein:

- welche Prozessversion galt,
- wann und warum diese Version gebunden wurde,
- welche Freigaben für diese Version vorlagen,
- ob und warum es eine dokumentierte Ausnahme gab.

## Ablauf bei neuem zentralen Update während laufender Fälle

1. Upstream-Update wird im Unternehmens-Fork über Sync-PR bewertet.
2. Neues Unternehmens-Release wird freigegeben.
3. Bereits laufende Vorgänge behalten alte `process_version`.
4. Neue Vorgänge nutzen das neue Release.
5. Reporting/Audit führt Alt- und Neu-Fälle getrennt aus.

## Beispiel: Notar legt Akte für Mandant an

- 10:15 Uhr: Akte `NOT-2026-0042` startet mit `process_version=v1.4.0`.
- 12:30 Uhr: Release `v1.5.0` wird freigegeben.
- 13:00 Uhr: Neue Akte `NOT-2026-0043` startet mit `process_version=v1.5.0`.
- Ergebnis:
  - `NOT-2026-0042` läuft regelkonform auf `v1.4.0` zu Ende.
  - `NOT-2026-0043` folgt dem neuen Ablauf auf `v1.5.0`.

Damit bleiben laufende Verfahren stabil und neue Verfahren nutzen den aktualisierten Standard.

## Umzugsregel für Sonderfälle

Ein Umzug eines laufenden Vorgangs auf eine neue Version ist nur zulässig, wenn:

- fachliche und regulatorische Auswirkungen geprüft wurden,
- die Entscheidung durch freigabeberechtigte Rolle dokumentiert ist,
- der Umzug selbst als nachvollziehbarer Nachweisschritt archiviert wird.
