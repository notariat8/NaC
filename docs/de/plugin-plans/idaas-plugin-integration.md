# IDaaS Plugin Integration

## Zweck

Dieser Plan migriert `ofunk/IDaaS` in das NoC-Plugin `noc-idaas`.
Das Plugin ist ein lokaler Companion fuer deutsche eID-Verifikation,
datensparsame Claim-Sets, Consent-/Audit-Nachweise und IAM-Projektionsplanung.

## Day0

- Zweck der Verifikation klaeren.
- Tenant, Kundenanwendung, Ziel-IAM und Review-Verantwortliche bestimmen.
- Claim-Set minimieren.
- Datenschutzgrundlage, AVV/DPA-Bedarf, Retention und Audit-Anforderungen
  dokumentieren.
- Klaeren, ob der Kanal Public GPT Store, GPT mit Actions, Workspace-App oder
  lokales Codex-Plugin ist.

## Day1

- Plan Preview fuer eID-Flow und optionale IAM-Projektion erzeugen.
- AusweisApp-, Redirect-, Webhook-/Polling-, Consent- und Evidence-Annahmen
  pruefen.
- OpenAPI- und Event-Vertraege trocken validieren.
- Menschliche Freigabe einholen, bevor echte personenbezogene Daten verarbeitet
  oder Zielsysteme geschrieben werden.

## Day2

- Abgelaufene Assertions, Widerrufe und fehlgeschlagene Projektionen pruefen.
- Retention-Drift und Zweckbindungsabweichungen sichtbar machen.
- Connectoren, Mapping-Profile und Reviewer-Zustaendigkeiten rezertifizieren.

## Sicherheitsgrenzen

- Keine echten eID-Rohdaten, Ausweisdumps, Tokens, Zertifikate oder
  Zugangsdaten im Repository.
- Keine IAM-Schreibaktion ohne reviewed Connector und Freigabe.
- Keine Verarbeitung personenbezogener Daten ohne dokumentierte Grundlage.
- Evidence ist standardmaessig metadata-only.
