# eID-Prüfung

Quellrepository geprüft am 2026-05-14: `ofunk/IDaaS`

Dieses Plugin kanonisiert das fruehere IDaaS-Repository in die NaC-Plugin-
Schicht. Es ist ein lokaler regulierter Begleiter für deutsche
eID-Prüfungs-Bereitschaft und IAM-Projektionsplanung.

## Umfang

- deutsche eID-Bereitschaft über AusweisApp-orientierte Abläufe
- Minimierung verifizierter Claims
- Einwilligungs- und Zweckbindungsnachweise
- IAM-Projektionsplanung für Entra ID, Oracle IAM und SCIM-Ziele
- Trockenlauf-Prüfung von API- und Eventverträgen

## Grenze

Dieses Plugin führt standardmäßig keine produktiven eID-Transaktionen aus,
speichert keine Identitätsdokumente, schreibt nicht in IAM-Systeme und reicht
keine Daten bei externen Diensten ein. Jeder produktive Connector muss separat
geprüft, freigegeben und bei Verarbeitung personenbezogener Daten an einen AVV
gebunden werden.

## Migrierte Quelle

Das Quellrepository enthielt:

- Produkt- und Architekturdokumentation
- OpenAPI-Skizze für den Verification-Vertrag
- `assertion-issued`-Eventschema
- Platzhalterordner für Verification-Orchestrierung und IAM-Projektion

Das kanonische NaC-Plugin-Material liegt jetzt hier:

- `.codex-plugin/plugin.json`
- `skills/nac-idaas/SKILL.md`
- `contracts/security-boundary.json`
- `contracts/verification-api.yaml`
- `contracts/assertion-issued.schema.json`
- `docs/source-summary.md`

## Veröffentlichungskanal

Dieses Plugin ist nicht automatisch für den öffentlichen GPT Store bereit. Es muss zuerst nach
[docs/de/gpt-marketplace-operating-model.md](../../docs/de/gpt-marketplace-operating-model.md)
und
[docs/en/gpt-marketplace-operating-model.md](../../docs/en/gpt-marketplace-operating-model.md)
als öffentlicher GPT Store, GPT mit Aktionen, Arbeitsbereich-App oder lokales
Codex-Plugin klassifiziert werden.
