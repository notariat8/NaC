# ISO-9001-Mapping

Diese Matrix ordnet typische ISO-9001-Themen den NaC-Artefakten zu. Sie ersetzt
kein externes Audit und keine Normauslegung, macht aber sichtbar, wo ein
Notariat seine Nachweise führen kann.

| ISO-9001-Thema | NaC-Nachweis | Stand |
| --- | --- | --- |
| Kontext der Organisation | [docs/de/notar-start.md](../docs/de/notar-start.md), [docs/de/reifegrad.md](../docs/de/reifegrad.md), [qms/process-map.md](process-map.md) | Muster vorhanden |
| Interessierte Parteien | Zielgruppenpfade im README, Rollen in [qms/roles-raci.json](roles-raci.json) | Muster vorhanden |
| QMS-Anwendungsbereich | [qms/README.md](README.md), [qms/quality-policy.md](quality-policy.md) | zu freigeben |
| Führung und Verantwortung | [qms/quality-policy.md](quality-policy.md), [qms/roles-raci.json](roles-raci.json) | Muster vorhanden |
| Risiken und Chancen | Usecase-Gates, Datenschutzgrenzen, Plugin-Readiness, Quality Gate | teilweise vorhanden |
| Qualitätsziele | [qms/quality-objectives.json](quality-objectives.json) | Muster vorhanden |
| Ressourcen und Kompetenz | [docs/de/minimum-requirements.md](../docs/de/minimum-requirements.md), Plugin-Readiness | vorhanden |
| Dokumentierte Information | Git, Pull Requests, QMS-Ordner, Datenrepo, Akten-IDs | vorhanden |
| Betrieb und Leistungserbringung | BPMN-Modelle, KG-Modelle, Operator-Webapp, `nac tenant` | vorhanden |
| Steuerung externer Anbieter | Service-Modell, Plugin-Pläne, Provider-Regeln | teilweise vorhanden |
| Überwachung und Messung | `nac doctor --profile strict`, Qualitätsziele, Datenrepo-Indizes | vorhanden |
| Interne Audits | [qms/audit-program.md](audit-program.md) | Muster vorhanden |
| Managementbewertung | [qms/management-review.md](management-review.md) | Muster vorhanden |
| Nichtkonformität und Korrekturmaßnahme | [qms/nonconformities.schema.json](nonconformities.schema.json) | Schema vorhanden |
| Kontinuierliche Verbesserung | Git-Änderungen, Auditmaßnahmen, CAPA, Roadmap | teilweise vorhanden |

## Lesart Für Auditoren

NaC ist kein einzelnes Formular, sondern ein versioniertes System. Ein Auditor
kann prüfen:

1. Ob der QMS-Scope freigegeben ist.
2. Ob Prozesse in BPMN und KG nachvollziehbar beschrieben sind.
3. Ob Akten, Personen, Dokumente und Ereignisse im Datenrepo referenzierbar
   sind.
4. Ob Quality Gates und Reviews regelmäßig laufen.
5. Ob Abweichungen und Verbesserungen nachverfolgt werden.

## Offene Punkte Vor Zertifizierung

- QMS-Scope durch das konkrete Notariat freigeben.
- Qualitätsziele mit echten Zielwerten und Verantwortlichen bestätigen.
- Auditprogramm terminieren und Auditoren benennen.
- CAPA-Register produktiv führen.
- Managementbewertung mindestens einmal durchführen.
- Produktive Datenhaltung, Rechte und Aufbewahrung final festlegen.
