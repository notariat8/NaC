# GitHub Identitaet und Rollenreferenz

## Ist eine Rollen-Definition direkt im GitHub-Profil moeglich?

Kurz: nicht als verlaessliche, workflow-taugliche Standardquelle fuer fachliche Berechtigungen.

GitHub-Profile sind fuer Darstellung gedacht, nicht als verbindliches Berechtigungsregister fuer Fachrollen.

## Verbindlicher Ansatz in diesem Repo

1. Technische Rollenquelle im Repository:
   - `policies/github-identity-registry.json`
2. Rollen- und Qualifikationsregeln:
   - `policies/role-model-policy.yaml`
3. Onboarding-Fragen und Berechtigungen:
   - `policies/onboarding-flow.json`

Damit ist klar und auditierbar:

- welcher GitHub-Login welche technische Rolle hat,
- welche Fragen von welcher Rolle beantwortet werden duerfen,
- welche Qualifikationen fuer kritische Schritte erforderlich sind.

## Empfohlene Zusatzabsicherung

- GitHub Teams fuer technische Zugriffssteuerung (Repo-Ebene)
- optional IdP/SSO-Gruppen als externe Governance-Quelle
- regelmaessige Synchronpruefung zwischen Team-Struktur und Registry-Datei
