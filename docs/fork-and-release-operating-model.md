# Fork-and-Release Operating Model

## Ziel

Dieses Dokument beschreibt das verbindliche Betriebsmodell fuer Unternehmen, die das zentrale `GIT OS` als Referenz nutzen:

- zentraler Upstream als Referenzstandard,
- ein Unternehmens-Fork als verbindlicher Betriebsstand,
- optionale Domaenen-Repos fuer fachlich eigenstaendige Teilprozesse.

Das Modell trennt Referenzpflege, lokale Steuerung und kontrollierte Uebernahme neuer Prozessversionen.

## Repository-Topologie

### 1) Zentrales Referenz-Repository (Upstream)

- enthaelt generische und branchenspezifische Musterprozesse,
- veroeffentlicht versionierte Releases,
- nimmt qualitaetsgesicherte Rueckfluesse aus Unternehmens-Forks auf.

### 2) Unternehmens-Fork (verbindlicher Betriebsstand)

- ist die operative Wahrheit fuer das jeweilige Unternehmen,
- fuehrt lokale Policies, Freigaben und Rollenbindung,
- uebernimmt Upstream-Aenderungen nur per kontrolliertem Sync-PR.

### 3) Optionale Domaenen-Repos

- werden nur angelegt, wenn eine Domaene eigenstaendige Release-Zyklen braucht,
- bleiben ueber Issue-Referenzen und Release-Referenzen mit dem Unternehmens-Fork gekoppelt,
- muessen dieselben Mindestkontrollen erfuellen (PR, Review, Nachweis, Versionierung).

## Verantwortungen

- `upstream_maintainer`: pflegt Referenzmodule und Release-Historie.
- `enterprise_process_owner`: entscheidet, wann Upstream-Releases in den Fork uebernommen werden.
- `enterprise_reviewer`: prueft Impact, Compliance und Rollout-Risiko.
- `enterprise_approver`: gibt die Uebernahme fuer den produktiven Einsatz frei.
- `domain_owner` (optional): verantwortet ein Domaenen-Repo inklusive lokaler Freigaberegeln.

## Verbindlicher Sync-Ablauf

1. Upstream publiziert ein freigegebenes Release (Tag + Changelog).
2. Unternehmen erstellt einen Sync-Branch im Fork, z. B. `sync/upstream-2026-03`.
3. Upstream-Aenderung wird in den Sync-Branch uebernommen.
4. Impact-Assessment und Tests werden dokumentiert.
5. Sync-PR wird reviewed und freigegeben.
6. Nach Merge wird im Unternehmens-Fork ein eigenes Release erzeugt.
7. Rollout erfolgt kontrolliert fuer neue Vorgaenge; laufende Vorgaenge bleiben unveraendert.

## Branch- und Tag-Konvention

- Keine direkten Aenderungen auf `main`.
- Sync-Branches beginnen mit `sync/upstream-`.
- Hotfix-Branches beginnen mit `hotfix/`.
- Produktive Prozessreleases nutzen `vMAJOR.MINOR.PATCH`.
- Optional zusaetzlich fachliche Abschlusstags wie `close/YYYY-MM`.

Empfehlung: Fuer Nachweise wird immer das `v*`-Release als technische Referenz genutzt, auch wenn parallel ein fachlicher Abschluss-Tag besteht.

## Wann ein Domaenen-Repo statt nur Fork?

Ein eigenes Domaenen-Repo ist sinnvoll, wenn mindestens zwei der folgenden Kriterien gelten:

- eigener Freigabeprozess mit abweichender Verantwortungsstruktur,
- deutlich hoehere Aenderungsfrequenz als im Kernmodell,
- separate Compliance-Nachweise oder externe Pruefpfade,
- eigenes Deployment/Automationsschema.

Wenn diese Kriterien nicht gelten, bleibt der Prozess im Unternehmens-Fork.

## Rueckfluss an den Upstream

Rueckfluss erfolgt optional und nur als separater PR in den Upstream:

- mit fachlicher Begruendung,
- mit Nachweis aus Pilot oder Betrieb,
- ohne unternehmensspezifische Interna oder vertrauliche Daten.

So bleibt das Referenzmodell lernfaehig, ohne lokale Steuerung zu verlieren.
