# Implementierungsplan: Team-Mitgliedschaft als Aktenleserecht

Issue: [#620](https://github.com/notariat8/NaC/issues/620).
Spec: [Team-Leserecht](../specs/2026-10-03-team-member-matter-read-design.md).
Status: Spec vom Owner freigegeben; lokale Umsetzung, kein Deployment.

1. Plan → Review → Fix: Vertrauenswürdige feste MVP-Team-/Sitebindung und
   vollständigen direkten Mitgliedschaftsnachweis prüfen. Keine Clientrollen.
2. Test-first: Neutrale Zugangsart `team_member` und Rolle `team_reader`;
   Positivtest ohne Personenmapping/Einzelzuordnung. Nichtmitglied, anderes
   Team, falscher Tenant, ungültige IDs, Paging und unvollständige Antworten
   sperren. Kein Rückfall auf Einzelzuordnung für Nichtmitglieder.
3. GET-Kante: gebundene Gruppenmetadaten, Group-Sitebindung und Mitglieder
   der exakt konfigurierten MVP-Gruppe. Nur abgeschlossene begrenzte Antworten
   akzeptieren; paginierte Antworten zunächst gesperrt statt teilweise positiv.
   Keine Rechteausweitung oder Token-/Provideraktion im lokalen Test.
   Konkrete Kanten: `GET /groups/{boundTeamId}?$select=id,groupTypes,resourceProvisioningOptions`,
   `GET /groups/{boundTeamId}/sites/root?$select=id,webUrl` und
   `GET /groups/{boundTeamId}/members?$select=id&$top=100`.
   Kein OData-Typcast: Dieser verlangt einen eventuell verzögerten Index und
   zusätzliche Advanced-Query-Parameter. Siehe die
   [offizielle Mitglieder-API](https://learn.microsoft.com/en-us/graph/api/group-list-members?view=graph-rest-1.0).
   `{boundTeamId}` ist die feste provisionierte MVP-Team-ID, keine Request-ID.
   Mitgliedschaft liest die Runtime über Application `GroupMember.Read.All`
   oder nachgewiesene bestehende stärkere Leserechte; Site-Lesen erfordert
   bestehendes `Sites.Selected` mit passendem Site-Grant oder belegte stärkere
   Rechte. Fehlende Rechte bleiben ein separates Live-Gate, kein Auto-Consent.
4. Mitgliedschaftsadapter, RawGraph-Transport und Composition synchronisieren.
   Teamleserecht braucht kein SharePoint-Personenmapping. Bestehende Personen-
   und Vertretungslogik bleibt für fachliche Aktionen getrennt.
5. AccessDecision, Endpoint, Projektion, DTO und SPFx führen `team_member` /
   `team_reader` ohne Freigabe-/Schreibfähigkeiten. Lease maximal 300 Sekunden;
   keine neue requestübergreifende Mitgliedschaftscache.
6. Policies, Agentenspiegel, Startdokumente, Contracts, CLI-Dokumentation,
   AI-SBOM und betroffene Validatoren synchronisieren. AC-620-05 ist künftig
   der Nichtmitglieder-Negativtest; Teammitglieder sind Positivfälle.
7. Implement → Review → Fix: unabhängige Sicherheits- und Validierungsreview,
   fokussierte Python-/SPFx-Tests, Parität/Traceability/Governance, Graft und
   vollständiger Strict-Doctor. Lokale Commits; Veröffentlichung und Live-
   Deployment nicht als durch die Spec bereits erledigt oder geprüft darstellen.

Die MVP-Allowlist bleibt erhalten; keine allgemeine Mehrakten-/Mehrmandanten-
Runtime. Vor Live-Reparatur Runtime-GET-Berechtigungen und Releasebindung
prüfen, dann kontrollierter positiver Mitgliedertest und Nichtmitgliedertest.
