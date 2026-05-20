# Fork-and-Release Operating Model

## Ziel

Dieses Dokument beschreibt das verbindliche Betriebsmodell für Unternehmen, die das zentrale `NaC` als Referenz nutzen:

- zentraler Upstream als Referenzstandard,
- ein Unternehmens-Fork als verbindlicher Betriebsstand,
- optionale Domänen-Repos für fachlich eigenständige Teilprozesse.

Das Modell trennt Referenzpflege, lokale Steuerung und kontrollierte Übernahme neuer Prozessversionen.

## Repository-Topologie

### 1) Zentrales Referenz-Repository (Upstream)

- enthält generische und branchenspezifische Musterprozesse,
- veröffentlicht versionierte Releases,
- nimmt qualitätsgesicherte Rückfluesse aus Unternehmens-Forks auf.

### 2) Unternehmens-Fork (verbindlicher Betriebsstand)

- ist die operative Wahrheit für das jeweilige Unternehmen,
- führt lokale Policies, Freigaben und Rollenbindung,
- übernimmt Upstream-Änderungen nur per kontrolliertem Sync-PR.

### 3) Optionale Domänen-Repos

- werden nur angelegt, wenn eine Domäne eigenständige Release-Zyklen braucht,
- bleiben über Issue-Referenzen und Release-Referenzen mit dem Unternehmens-Fork gekoppelt,
- müssen dieselben Mindestkontrollen erfüllen (PR, Review, Nachweis, Versionierung).

## Verantwortungen

- `upstream_maintainer`: pflegt Referenzmodule und Release-Historie.
- `enterprise_process_owner`: entscheidet, wann Upstream-Releases in den Fork übernommen werden.
- `enterprise_reviewer`: prüft Impact, Compliance und Rollout-Risiko.
- `enterprise_approver`: gibt die Übernahme für den produktiven Einsatz frei.
- `domain_owner` (optional): verantwortet ein Domänen-Repo inklusive lokaler Freigaberegeln.

## Verbindlicher Sync-Ablauf

1. Upstream publiziert ein freigegebenes Release (Tag + Changelog).
2. Unternehmen erstellt einen Sync-Branch im Fork, z. B. `sync/upstream-2026-03`.
3. Upstream-Änderung wird in den Sync-Branch übernommen.
4. Impact-Assessment und Tests werden dokumentiert.
5. Sync-PR wird reviewed und freigegeben.
6. Nach Merge wird im Unternehmens-Fork ein eigenes Release erzeugt.
7. Rollout erfolgt kontrolliert für neue Vorgänge; laufende Vorgänge bleiben unverändert.

## Branch- und Tag-Konvention

- Keine direkten Änderungen auf `main`.
- Sync-Branches beginnen mit `sync/upstream-`.
- Hotfix-Branches beginnen mit `hotfix/`.
- Produktive Prozessreleases nutzen `vMAJOR.MINOR.PATCH`.
- Optional zusätzlich fachliche Abschlusstags wie `close/YYYY-MM`.

Empfehlung: Für Nachweise wird immer das `v*`-Release als technische Referenz genutzt, auch wenn parallel ein fachlicher Abschluss-Tag besteht.

## Wann ein Domänen-Repo statt nur Fork?

Ein eigenes Domänen-Repo ist sinnvoll, wenn mindestens zwei der folgenden Kriterien gelten:

- eigener Freigabeprozess mit abweichender Verantwortungsstruktur,
- deutlich höhere Änderungsfrequenz als im Kernmodell,
- separate Compliance-Nachweise oder externe Prüfpfade,
- eigenes Deployment/Automationsschema.

Wenn diese Kriterien nicht gelten, bleibt der Prozess im Unternehmens-Fork.

## Rückfluss an den Upstream

Rückfluss erfolgt optional und nur als separater PR in den Upstream:

- mit fachlicher Begründung,
- mit Nachweis aus Pilot oder Betrieb,
- ohne unternehmensspezifische Interna oder vertrauliche Daten.

So bleibt das Referenzmodell lernfähig, ohne lokale Steuerung zu verlieren.
