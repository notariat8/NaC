# Plugin-Plan: Juristische Recherche-Connectoren

Status: `draft`

## Zweck

Dieses Dokument führt externe Legal-Research-, MCP- und
Verlagsdatenbank-Hinweise als Kandidaten. Es ist keine Produktintegration und
keine Freigabe zur automatisierten Recherche.

NaC behandelt jede Quelle in dieser Liste als möglichen Connector-Ausgangspunkt:
Quelle aufnehmen, Nutzungs- und Lizenzlage prüfen, Datenschutz- und
AVV-Bedarf klären, Sicherheitsgrenze festlegen, AI-SBOM-Status entscheiden und
erst danach eine technische Integration planen.

## Kandidatenstand

| Kandidat | Quelle | Status | NaC-Grenze |
| --- | --- | --- | --- |
| Klotzkette Connector Reference | [CONNECTORS.md](https://github.com/Klotzkette/claude-fuer-deutsches-recht/blob/main/CONNECTORS.md) | Watchlist | Externe Referenzliste, keine direkte Übernahme. |
| German Law MCP von Ansvar Systems | [LobeHub](https://lobehub.com/mcp/ansvar-systems-german-law-mcp) | Kandidat | Metadatenprüfung für öffentliche Rechtsquellen, AI-SBOM offen. |
| German Law MCP auf ElasticFlow | [ElasticFlow](https://elasticflow.app/hub/pt-BR/mcps/german-law-mcp) | Kandidat, Doppellistung | Gleicher technischer Kandidat wie Ansvar/LobeHub, separat nachgewiesen. |
| beck-online MCP Listing | [MCP Market](https://mcpmarket.com/server/beck-online) | Lizenzprüfung nötig | Keine Nutzung ohne Vertrags-, Lizenz-, TDM-, Sicherheits- und Credential-Prüfung. |
| Deubner Recht Portal | [Deubner Recht & Praxis](https://www.deubner-recht.de/) | Lizenzprüfung nötig | Nur als Verlagsportal-Kandidat; keine automatisierte Abfrage, kein Volltextimport und keine Credential-Nutzung ohne Vertrags-, Lizenz-, AVV-/DPA-, TDM- und Sicherheitsprüfung. |

Alle URLs werden ohne Trackingparameter geführt. Die maschinenlesbare Grenze
steht im
[Legal-Research-Connector-Vertrag](../../../workflows/contracts/legal-research-connectors.contract.json).

## Freigabegrenzen

- Keine Secrets, Zugangsdaten, Session-Cookies oder privaten Schlüssel im Repo.
- Keine echten Mandatsdaten, Personenbezüge oder Dokumentvolltexte an
  externe KI- oder MCP-Dienste ohne Datenschutzprüfung.
- Keine automatisierte Abfrage geschützter Verlagsdatenbanken ohne Vertrag,
  Lizenzgrundlage, Nutzungsbedingungen und technischen Sicherheitsnachweis.
- Keine juristische Wahrheit aus KI-Antworten ableiten; verbindlich bleibt die
  menschliche fachliche Prüfung und die versionierte NaC-Freigabe.
- Keine Portal-Scraping- oder TDM-Annahme ohne ausdrückliche Rechts- und
  Anbieterprüfung.

## Kandidat Zu Connector

Ein Kandidat wird erst dann zu einem Connector-Plan, wenn diese Schritte
vollständig sind:

1. Quelle, Anbieter, Lizenzstatus und Datenklasse dokumentieren.
2. Datenschutz, AVV/DPA, TIA-Bedarf und Mandatsdatenverbot bewerten.
3. AI-SBOM-Status für KI-, API- oder MCP-Kandidaten festlegen.
4. Sicherheitsgrenze und Credential-Speicher außerhalb von Git beschreiben.
5. Dry-run- oder Metadata-only-Modus entwerfen.
6. Menschliche Review- und Vier-Augen-Pflichten festlegen.
7. Erst danach Plugin-, MCP- oder Webapp-Bedienkante planen.

## Webapp-Sicht

Eine authentifizierte NaC-Webapp darf diesen Backlog später als Status- und
Prüfansicht zeigen: Kandidat, Quelle, Lizenzstatus, Reviewstand, Blocker und
nächster Prüfschritt. Sie darf daraus keine verdeckte Produktintegration
machen und keine geheimen Zugangsdaten oder fremde Volltexte anzeigen.

## Prüfung

Der Backlog wird über die zentrale NaC-CLI geprüft:

```bash
nac contracts validate
```

Der Validator blockiert Tracking-URLs, Credentials im Repo, produktive
Integrationslevel, fehlende Lizenz-/AVV-/Review-Gates und fehlende
Nachweisfelder.
