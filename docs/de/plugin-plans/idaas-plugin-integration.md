# IDaaS Plugin Integration

## Zweck

Dieser Plan migriert `ofunk/IDaaS` in das NaC-Plugin `nac-idaas`.
Das Plugin ist ein lokaler Companion für deutsche eID-Verifikation,
datensparsame Claim-Sets, Consent-/Audit-Nachweise und IAM-Projektionsplanung.

## Day0

- Zweck der Verifikation klären.
- Tenant, Kundenanwendung, Ziel-IAM und Review-Verantwortliche bestimmen.
- Claim-Set minimieren.
- Datenschutzgrundlage, AVV/DPA-Bedarf, Retention und Audit-Anforderungen
  dokumentieren.
- Klären, ob der Kanal Public GPT Store, GPT mit Actions, Workspace-App oder
  lokales Codex-Plugin ist.

## Day1

- Plan Preview für eID-Flow und optionale IAM-Projektion erzeugen.
- AusweisApp-, Redirect-, Webhook-/Polling-, Consent- und Evidence-Annahmen
  prüfen.
- OpenAPI- und Event-Verträge trocken validieren.
- Menschliche Freigabe einholen, bevor echte personenbezogene Daten verarbeitet
  oder Zielsysteme geschrieben werden.

## Day2

- Abgelaufene Assertions, Widerrufe und fehlgeschlagene Projektionen prüfen.
- Retention-Drift und Zweckbindungsabweichungen sichtbar machen.
- Connectoren, Mapping-Profile und Reviewer-Zuständigkeiten rezertifizieren.

## Sicherheitsgrenzen

- Keine echten eID-Rohdaten, Ausweisdumps, Tokens, Zertifikate oder
  Zugangsdaten im Repository.
- Keine IAM-Schreibaktion ohne reviewed Connector und Freigabe.
- Keine Verarbeitung personenbezogener Daten ohne dokumentierte Grundlage.
- Evidence ist standardmäßig metadata-only.
