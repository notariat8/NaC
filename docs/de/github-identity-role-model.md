# GitHub Identität und Rollenreferenz

## Ist eine Rollen-Definition direkt im GitHub-Profil möglich?

Kurz: nicht als verlaessliche, workflow-taugliche Standardquelle für fachliche Berechtigungen.

GitHub-Profile sind für Darstellung gedacht, nicht als verbindliches Berechtigungsregister für Fachrollen.

## Verbindlicher Ansatz in diesem Repo

1. Technische Rollenquelle im Repository:
   - `policies/github-identity-registry.json`
2. Rollen- und Qualifikationsregeln:
   - `policies/role-model-policy.yaml`
3. Zugriffs- und Sichtbarkeitsregeln:
   - `policies/access-control-policy.yaml`
4. Onboarding-Fragen und Berechtigungen:
   - `policies/onboarding-flow.json`

Damit ist klar und auditierbar:

- welcher GitHub-Login welche technische Rolle hat,
- welche Fragen von welcher Rolle beantwortet werden dürfen,
- welche Qualifikationen für kritische Schritte erforderlich sind.
- welche Repo-/Issue-Sichtbarkeitsregeln für Mitarbeitende und Gaeste gelten.

## Empfohlene Zusatzabsicherung

- GitHub Teams für technische Zugriffssteuerung (Repo-Ebene)
- optional IdP/SSO-Gruppen als externe Governance-Quelle
- regelmäßige Synchronprüfung zwischen Team-Struktur und Registry-Datei
