# Implementierungsplan: technischer Team-Owner

Issue: [#766](https://github.com/notariat8/NaC/issues/766).
Spec: [Technischer Team-Owner](../specs/2026-10-02-technical-team-owner-design.md).
Status: lokale Korrektur beauftragt; kein Tenant-Apply.

1. **Plan → Review → Fix:** Owner-Klarstellung in Policy verankern; aktive
   Erstellungspläne, Gruppen-/Teams-Owner-Prüfung und historische Evidence
   getrennt mappen. Unabhängiges Review prüft Scope und Sicherheitsgrenzen.
2. **Test-first:** Positivtest für ausschließlich technischen Owner;
   Negativtests für fehlenden, falschen, zusätzlichen, malformed Owner sowie
   abweichende Gruppen-/Teams-Rollen. Jeder Fehler beweist null Writes.
3. **Implement → Review → Fix:** Expliziter Owner im Offline-Team-Plan;
   Vorabprüfung aller Zielteams vor der ersten Mutation; keine automatische
   Migration. Historische Evidence bleibt unverändert und nicht operativ.
4. Policy, Verträge, Validatoren, DE/EN-Architektur, Einstieg und relevante
   Codex-/pi-Profile synchronisieren. Lizenz-, Principal- und Akten-Gates
   weder entfernen noch durch Team-Ownership ersetzen.
5. Fokussierte Tests, Privacy-Lint, Contract-/Governance-/Sprach-/Traceability-
   Validatoren und frisch gebauten Graft-Graph prüfen; vollständige
   `main...HEAD`-Diff unabhängig reviewen.
   Danach lokale Commits und normaler Push in Draft-PR. Vollständiger lokaler
   Strict-Doctor und Remote-CI dürfen parallel laufen; ein laufendes oder
   fehlgeschlagenes Gate wird nicht als bestanden dargestellt.
6. Vollständigen Strict-Doctor und Remote-CI erfolgreich abschließen und
   vollständig auswerten. Vor Merge und jeder realen
   Team-Owner-Änderung stoppen; keinen aktuellen Tenant-Sollzustand behaupten.

AC-OWNER-01 bis AC-OWNER-05 werden durch die in der Spec genannten Tests und
Validatoren belegt. Die vorhandene `nac m365 teams-sharepoint plan`-/
`privileged-plan`-/`application-owner-readiness`-Bedienkante wird genutzt;
kein neuer Live-Executor entsteht.

## Windows-Prüflauf

Der vollständige Lauf übernimmt die native Windows-Kodierung. Ein pauschaler
UTF-8-Modus ist kein Ersatz für passende Unterprozess-Kodierungen: Python,
Node und Windows-Systemprogramme können unterschiedliche Ausgabeformate
verwenden. Auf dem geprüften Arbeitsplatz werden `PYTHONUTF8=0` und
`PYTHONIOENCODING=cp1252` ausschließlich prozesslokal genutzt; System- und
Benutzereinstellungen bleiben unverändert. Bei einem Fehler zunächst genau
die betroffenen Tests reproduzieren und erst nach deren Erfolg den finalen
vollständigen Strict-Doctor starten. Keine Prüfung wird ausgelassen.
