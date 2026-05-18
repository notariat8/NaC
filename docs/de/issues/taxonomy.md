# Issue-Taxonomie pro Repository

## Ziel

Dieses Dokument definiert, welche Themen in welches Repository gehören und wie Issues zwischen Repos verlinkt werden.

## Repo-Typen

### Upstream-Repo (zentrales NaC)

Zuständig für:

- generische Referenzprozesse,
- branchenspezifische Musterbausteine,
- übergreifende Governance-Standards,
- öffentlich nutzbare Verbesserungen aus Rückfluss.

Nicht zuständig für:

- unternehmensinterne Sonderfälle,
- lokale Betriebsentscheidungen ohne Referenzrelevanz.

### Unternehmens-Fork

Zuständig für:

- lokale Prozessanpassungen,
- Release-Übernahmen aus Upstream,
- Compliance- und Rollout-Entscheidungen im Unternehmen,
- verbindlichen Betriebsstand und Audit-Nachweise.

### Optionale Domänen-Repos

Zuständig für:

- dichte Fachlogik einzelner Domänen (z. B. Notariat-Akte),
- dichte operative Änderungen mit eigener Release-Taktung,
- domänenspezifische Integrationen und Fachnachweise.

## Issue-Klassen (Mindeststandard)

- `process-change`: fachliche Prozessänderung.
- `compliance-change`: regulatorische oder governance-relevante Änderung.
- `sync-upstream`: Übernahme eines Upstream-Releases in den Fork.
- `incident`: Störung, Abweichung oder Regelverletzung im Betrieb.
- `documentation`: Klarstellung oder Nachweisanpassung ohne Prozesslogik-Änderung.

## Führungsregel pro Thema

- Ein Thema hat genau ein führendes Issue in genau einem Repo.
- Verwandte Issues in anderen Repos werden als abgeleitete Issues verlinkt.
- Der Status des führenden Issues steuert den Gesamtfortschritt.

## Verlinkungsstandard

Jedes abhängige Issue enthält:

- Referenz auf das führende Issue (`upstream`, `fork` oder `domain`),
- kurze Einordnung der lokalen Auswirkung,
- benötigten Entscheidungszeitpunkt.

Empfehlung für Titelpraefixe:

- `[UPSTREAM]`
- `[FORK]`
- `[DOMAIN-NOTARY]`

## Beispielverteilung

Fall: Neuer Notariatsablauf wird im zentralen Standard angepasst.

1. Upstream-Issue beschreibt Referenzänderung.
2. Fork-Issue `sync-upstream` plant lokale Übernahme.
3. Domain-Issue bewertet Notariat-spezifische Auswirkungen.
4. Nach Freigabe verweist das Fork-Issue auf den produktiven Release-Tag.

## Statusmodell (einfach)

- `backlog`
- `in_assessment`
- `in_implementation`
- `in_review`
- `approved`
- `released`
- `closed`

Alle Repos nutzen dieselben Statuswerte, damit übergreifendes Reporting konsistent bleibt.
