# Parallelbetrieb mit Version-Binding

## Ziel

Dieses Dokument regelt den Mischbetrieb, wenn alte und neue Prozessversionen gleichzeitig rechts- und revisionssicher betrieben werden muessen.

Kernprinzip: **Die beim Vorgangsstart gueltige Prozessversion bleibt fuer diesen Vorgang verbindlich.**

## Verbindliche Regeln

1. Jeder neue Vorgang bekommt beim Start eine Prozessversions-Referenz (`process_version`).
2. `process_version` verweist auf ein freigegebenes Release-Tag im Unternehmens-Fork.
3. Laufende Vorgaenge wechseln nicht automatisch auf spaetere Releases.
4. Neue Releases gelten nur fuer Vorgaenge, die nach Freigabe neu gestartet werden.
5. Ausnahmen (manueller Umzug eines Vorgangs auf neue Version) brauchen dokumentierte Einzelentscheidung.

## Mindestmetadaten je Vorgang

- `request_id`
- `process_domain` (z. B. `notary`, `invoice`, `tax`)
- `process_version` (z. B. `v1.6.2`)
- `version_bound_at` (Zeitpunkt der Bindung)
- `bound_by_role` (Rolle/Person, die den Vorgang gestartet hat)
- `compliance_basis` (optional, z. B. interne Richtlinie oder externer Bezug)

## Audit-Nachweis

Fuer jeden Vorgang muss reproduzierbar sein:

- welche Prozessversion galt,
- wann und warum diese Version gebunden wurde,
- welche Freigaben fuer diese Version vorlagen,
- ob und warum es eine dokumentierte Ausnahme gab.

## Ablauf bei neuem zentralen Update waehrend laufender Faelle

1. Upstream-Update wird im Unternehmens-Fork ueber Sync-PR bewertet.
2. Neues Unternehmens-Release wird freigegeben.
3. Bereits laufende Vorgaenge behalten alte `process_version`.
4. Neue Vorgaenge nutzen das neue Release.
5. Reporting/Audit fuehrt Alt- und Neu-Faelle getrennt aus.

## Beispiel: Notar legt Akte fuer Mandant an

- 10:15 Uhr: Akte `NOT-2026-0042` startet mit `process_version=v1.4.0`.
- 12:30 Uhr: Release `v1.5.0` wird freigegeben.
- 13:00 Uhr: Neue Akte `NOT-2026-0043` startet mit `process_version=v1.5.0`.
- Ergebnis:
  - `NOT-2026-0042` laeuft regelkonform auf `v1.4.0` zu Ende.
  - `NOT-2026-0043` folgt dem neuen Ablauf auf `v1.5.0`.

Damit bleiben laufende Verfahren stabil und neue Verfahren nutzen den aktualisierten Standard.

## Umzugsregel fuer Sonderfaelle

Ein Umzug eines laufenden Vorgangs auf eine neue Version ist nur zulaessig, wenn:

- fachliche und regulatorische Auswirkungen geprueft wurden,
- die Entscheidung durch freigabeberechtigte Rolle dokumentiert ist,
- der Umzug selbst als nachvollziehbarer Nachweisschritt archiviert wird.
