# Governance mit Git und GitHub

## Repository-Regeln

Empfohlenes Zielbild fuer `main`:

- Pushes direkt auf `main` verbieten
- Pull Requests verpflichtend machen
- Status-Checks aus `Validate Business Processes` verlangen
- Review durch mindestens eine fachlich verantwortliche Person verlangen
- Signierte Tags fuer Abschluesse wie `close/2026-03` verwenden

## Environment-Mapping

- `business-operations`: sensible manuelle Ausfuehrung einzelner Prozesse
- `month-close`: Monatsabschluss und periodische Aggregation
- optional `tax-submission`: letzte Freigabestufe vor externer Steuerabgabe

## Fachliches Mapping

| Git/GitHub-Mechanismus | Fachliche Bedeutung |
| --- | --- |
| Branch | in Arbeit befindlicher Geschaeftsvorgang |
| Pull Request | formaler Antrag mit Freigabebedarf |
| Review | fachliche Freigabe |
| Action Run | dokumentierte maschinelle Ausfuehrung |
| Artifact | exportierter Nachweis oder Bericht |
| Tag | Abschlussstand |
| Release | publizierter, versionierter Nachweis |

## Praktische Regeln pro Domäne

### Gruendung

- Schritte koennen in einem Sammelvorgang oder als einzelne Prozessdateien gefuehrt werden.
- Status `needs_review` sollte mit manuellem Review gekoppelt werden.

### Rechnungsstellung

- `draft -> approved` nur ueber Pull Request.
- `approved -> issued` nur in einer gesicherten Runtime oder nach dokumentierter Freigabe.

### Buchfuehrung

- Buchungssaetze muessen ausgeglichen sein.
- Idempotenzschluessel und Belegreferenzen verhindern Doppelbuchungen.

### Steuer

- `prepared -> approved` immer mit Vier-Augen-Prinzip.
- `submitted` sollte nur nach manueller Freigabe und moeglichem externen Filing gesetzt werden.
