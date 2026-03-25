# Zugriff und Issue-Betrieb im Unternehmen

## Ziel

Dieses Dokument beschreibt ein umsetzbares Modell fuer:

- gemeinsame Task-Uebersicht ueber mehrere Repos,
- strikte Sichtbarkeit je Akte/Repo,
- Rollen- und Rechtepflege fuer Mitarbeitende, Mandanten und Auditoren.

## Grundregel

In GitHub werden Rechte auf **Repository-Ebene** vergeben, nicht auf Issue-Ebene.

Folge:

- Wer ein Repo nicht sehen darf, sieht auch dessen Issues nicht.
- Eine gemeinsame Uebersicht ueber viele Repos erfolgt ueber ein Organization-Project.

Ergaenzung fuer Compliance:

- Issues sind die **operative Ebene**.
- Revisionssichere Ablage erfolgt ueber ein separates, unveraenderbares Event-Journal.
- Details: `docs/revisionssicherheit-eventstreaming.md`

## Repo-Typen im Unternehmen

1. `core-repo`
   - zentrale Regeln, Standards, gemeinsame Workflows
2. `domain-repo`
   - fachlicher Domaenenkontext (z. B. Notariat)
3. `case-repo`
   - einzelne Akte/Verfahren, z. B. `case-notary-2026-0042`

## Rollen und technische Zuordnung

Fachliche Rollen werden in `policies/role-model-policy.yaml` gepflegt.  
GitHub-Logins werden in `policies/github-identity-registry.json` den technischen Rollen zugeordnet.
Repo-/Issue-Sichtbarkeit und Gastzugriffe sind in `policies/access-control-policy.yaml` verbindlich festgelegt.

Technische Teams in der GitHub-Organisation:

- `team-notaries-all`: alle Notare mit Vollsicht auf alle Notariats-Akten
- `team-notary-ops`: operative Mitarbeitende Notariat
- `team-tax`, `team-law`, `team-software`, `team-carpentry` (je Vertical)
- `team-audit-readonly`: interne Audit-Sicht, read-only

Externe:

- Mandant als Gastnutzer (`outside collaborator`) nur auf seinem `case-repo`
- Auditor extern als Gastnutzer, read-only nur auf freigegebene `case-repo` oder Audit-Repo

## Rechtematrix (empfohlen)

| Rolle/Gruppe | core-repo | domain-repo | case-repo (eigene Akte) | case-repo (fremde Akte) |
| --- | --- | --- | --- | --- |
| notar_fachlich | write/maintain | write/maintain | maintain | no access |
| sachbearbeitung_notary | read/triage | write | write | no access |
| prozessverantwortung | maintain | maintain | maintain | read (optional) |
| revision_audit intern | read | read | read | read (nur freigegebene) |
| mandant_gast | no access | no access | read oder triage | no access |
| auditor_gast extern | no access | no access | read (freigegebene) | no access |

Hinweis:

- Notare mit Gesamtverantwortung erhalten Teamzugriff auf alle Notariats-`case-repo`.
- Mitarbeitende ohne Repo-Aufgabe erhalten keinen Zugriff auf dieses Repo und sehen dessen Issues nicht.

## Gemeinsame Issue-Uebersicht ueber Repos

Nutzen Sie ein GitHub Organization Project als zentrale Aufgabenansicht.

Empfohlene Felder:

- `case_id`
- `domain`
- `repo_type` (`core`, `domain`, `case`)
- `impact_level`
- `decision_type`
- `due_date`

Empfohlene Views:

- `my_tasks`: `assignee = @me`
- `notary_all_cases`: `domain = notary`
- `audit_view`: `impact_level in (medium, high)` und `decision_type = requires_approval`
- `client_case_view`: nur Issues des jeweiligen `case-repo`

Wichtig:

- Das Project zeigt nur Issues aus Repos, auf die der Nutzer bereits Zugriff hat.
- So entsteht eine zentrale Uebersicht ohne Rechtebruch.

## Standardablauf: Neue Akte anlegen

1. `case-repo` nach Namensstandard anlegen (z. B. `case-notary-2026-0042`).
2. Repo-Template fuer Akten nutzen (Issue-Templates, Labels, Schutzregeln).
3. Teamrechte setzen:
   - `team-notaries-all` mindestens `maintain`
   - zustaendige Sachbearbeitung `write`
4. Mandant als Gastnutzer hinzufuegen (`read` oder `triage` je Policy).
5. Auditor (falls erforderlich) als Gastnutzer mit `read` zuweisen.
6. Start-Issues aus Vorlage erstellen:
   - `intake`
   - `identity_check`
   - `document_preparation`
   - `approval_gate`
   - `execution_tracking`
7. Issues dem Organization-Project zuordnen und Pflichtfelder befuellen.
8. `process_version` fuer den Vorgang dokumentieren (Version-Binding).

## Pflegeprozess fuer Rollen und Rechte

Pflegeorte:

- fachliche Entscheidung: `policies/role-model-policy.yaml`
- technische Login-Zuordnung: `policies/github-identity-registry.json`
- Zugriffsmodell und Gastregeln: `policies/access-control-policy.yaml`
- Betriebsablauf und Rechteverfahren: dieses Dokument

Pflegezyklus:

1. Monatsweise Rollenreview mit Prozessverantwortung.
2. Quartalsweise Rezertifizierung fuer Gastzugriffe.
3. Sofortige Anpassung bei Rollenwechsel, Offboarding oder Incident.

## Mindestkontrollen

- keine direkten Aenderungen auf `main`
- PR + Review fuer alle Prozessaenderungen
- CODEOWNERS pro Domain/Case
- Environment-Gates bei approval-pflichtigen Schritten
- Audit-Log regelmaessig pruefen (Gastzugriffe, Repo-Berechtigungen, Freigaben)
