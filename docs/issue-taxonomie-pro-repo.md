# Issue-Taxonomie pro Repository

## Ziel

Dieses Dokument definiert, welche Themen in welches Repository gehoeren und wie Issues zwischen Repos verlinkt werden.

## Repo-Typen

### Upstream-Repo (zentrales OaC8)

Zustaendig fuer:

- generische Referenzprozesse,
- branchenspezifische Musterbausteine,
- uebergreifende Governance-Standards,
- oeffentlich nutzbare Verbesserungen aus Rueckfluss.

Nicht zustaendig fuer:

- unternehmensinterne Sonderfaelle,
- lokale Betriebsentscheidungen ohne Referenzrelevanz.

### Unternehmens-Fork

Zustaendig fuer:

- lokale Prozessanpassungen,
- Release-Uebernahmen aus Upstream,
- Compliance- und Rollout-Entscheidungen im Unternehmen,
- verbindlichen Betriebsstand und Audit-Nachweise.

### Optionale Domaenen-Repos

Zustaendig fuer:

- dichte Fachlogik einzelner Domaenen (z. B. Notariat-Akte),
- dichte operative Aenderungen mit eigener Release-Taktung,
- domaenenspezifische Integrationen und Fachnachweise.

## Issue-Klassen (Mindeststandard)

- `process-change`: fachliche Prozessaenderung.
- `compliance-change`: regulatorische oder governance-relevante Aenderung.
- `sync-upstream`: Uebernahme eines Upstream-Releases in den Fork.
- `incident`: Stoerung, Abweichung oder Regelverletzung im Betrieb.
- `documentation`: Klarstellung oder Nachweisanpassung ohne Prozesslogik-Aenderung.

## Fuehrungsregel pro Thema

- Ein Thema hat genau ein fuehrendes Issue in genau einem Repo.
- Verwandte Issues in anderen Repos werden als abgeleitete Issues verlinkt.
- Der Status des fuehrenden Issues steuert den Gesamtfortschritt.

## Verlinkungsstandard

Jedes abhaengige Issue enthaelt:

- Referenz auf das fuehrende Issue (`upstream`, `fork` oder `domain`),
- kurze Einordnung der lokalen Auswirkung,
- benoetigten Entscheidungszeitpunkt.

Empfehlung fuer Titelpraefixe:

- `[UPSTREAM]`
- `[FORK]`
- `[DOMAIN-NOTARY]`

## Beispielverteilung

Fall: Neuer Notariatsablauf wird im zentralen Standard angepasst.

1. Upstream-Issue beschreibt Referenzaenderung.
2. Fork-Issue `sync-upstream` plant lokale Uebernahme.
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

Alle Repos nutzen dieselben Statuswerte, damit uebergreifendes Reporting konsistent bleibt.
