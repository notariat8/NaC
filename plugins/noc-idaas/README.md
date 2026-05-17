# NoC eID- und IAM-Begleiter

Quellrepository geprueft am 2026-05-14: `ofunk/IDaaS`

Dieses Plugin kanonisiert das fruehere IDaaS-Repository in die NoC-Plugin-
Schicht. Es ist ein lokaler regulierter Begleiter fuer deutsche
eID-Pruefungs-Bereitschaft und IAM-Projektionsplanung.

## Umfang

- deutsche eID-Bereitschaft ueber AusweisApp-orientierte Ablaeufe
- Minimierung verifizierter Claims
- Einwilligungs- und Zweckbindungsnachweise
- IAM-Projektionsplanung fuer Entra ID, Oracle IAM und SCIM-Ziele
- Trockenlauf-Pruefung von API- und Eventvertraegen

## Grenze

Dieses Plugin fuehrt standardmaessig keine produktiven eID-Transaktionen aus,
speichert keine Identitaetsdokumente, schreibt nicht in IAM-Systeme und reicht
keine Daten bei externen Diensten ein. Jeder produktive Connector muss separat
geprueft, freigegeben und bei Verarbeitung personenbezogener Daten an einen AVV
gebunden werden.

## Migrierte Quelle

Das Quellrepository enthielt:

- Produkt- und Architekturdokumentation
- OpenAPI-Skizze fuer den Verification-Vertrag
- `assertion-issued`-Eventschema
- Platzhalterordner fuer Verification-Orchestrierung und IAM-Projektion

Das kanonische NoC-Plugin-Material liegt jetzt hier:

- `.codex-plugin/plugin.json`
- `skills/noc-idaas/SKILL.md`
- `contracts/security-boundary.json`
- `contracts/verification-api.yaml`
- `contracts/assertion-issued.schema.json`
- `docs/source-summary.md`

## Veroeffentlichungskanal

Dieses Plugin ist nicht automatisch fuer den oeffentlichen GPT Store bereit. Es muss zuerst nach
[docs/de/gpt-marketplace-operating-model.md](../../docs/de/gpt-marketplace-operating-model.md)
und
[docs/en/gpt-marketplace-operating-model.md](../../docs/en/gpt-marketplace-operating-model.md)
als oeffentlicher GPT Store, GPT mit Aktionen, Arbeitsbereich-App oder lokales
Codex-Plugin klassifiziert werden.
