# Security und DSGVO Leitlinie

## Wichtigste Aussage

Es ist nie zu 100 Prozent garantiert, dass in einem Repository keine sensiblen Inhalte landen.  
Deshalb kombiniert dieses Musterrepo Regeln, Reviews und automatische Scans.

## Was verbindlich gilt

- Keine echten Passwoerter, Tokens, API-Keys oder private Schluessel.
- Keine echten personenbezogenen Daten in Beispieldateien.
- Nur synthetische Testdaten und Platzhalter.
- Nur Test-E-Mails mit Beispiel-Domains.

## Schutzmechanismen im Repo

- Policy: `policies/data-protection-policy.yaml`
- AVV-Checkliste fuer SaaS-Betrieb: `docs/avv-checkliste-eventlock-saas.md`
- PR-Checks: `.github/PULL_REQUEST_TEMPLATE.md`
- Secret-Scan in CI: `.github/workflows/privacy-and-secrets.yml`
- Privacy-Lint in CI: `.github/workflows/privacy-and-secrets.yml`

## Reaktion bei Sicherheitsvorfall

1. Secret sofort widerrufen/rotieren.
2. Betroffene Daten aus Repo entfernen und Ersatz einspielen.
3. Incident als Issue dokumentieren.
4. Freigabeprozess pruefen und verbessern.

## Hinweis fuer Forks

Forks muessen diese Regeln ebenfalls uebernehmen.  
Empfehlung: Nach Fork sofort Policies und Workflows aktiv pruefen.
