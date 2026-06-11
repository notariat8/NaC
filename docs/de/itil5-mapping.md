# ITIL-5-Mapping für NaC

## Zweck

Dieses Dokument ordnet `NaC` gegen ITIL 5 ein. Es ist kein Zertifizierungs-
oder Reifegradversprechen. Es dient als Brücke für Gespräche mit IT-Leitung,
Revision, Datenschutz, Betriebsverantwortlichen und Notariaten, die
IT-Service-Management-Sprache erwarten.

NaC bleibt führend durch:

- notarielle Verantwortung,
- Datenschutz und AVV/DPA-Gates,
- QMS-/ISO-9001-Nachweise,
- `Notariat as Code` und `Enterprise GitOps`,
- versionierte Policies, Pull Requests, Reviews, Releases und Event-Journal.

ITIL 5 ist für NaC damit eine Anschluss- und Prüfsprache, kein zusätzlicher
Steuerungsrahmen.

## Quellenstand

Geprüft am 2026-06-11:

- PeopleCert ITIL Framework:
  [peoplecert.org/Frameworks-Professionals/ITIL-framework](https://www.peoplecert.org/Frameworks-Professionals/ITIL-framework)
- PeopleCert ITIL Certifications:
  [peoplecert.org/browse-certifications/it-governance-and-service-management/ITIL-1](https://www.peoplecert.org/browse-certifications/it-governance-and-service-management/ITIL-1)

PeopleCert beschreibt ITIL als Framework für Digital Product and Service
Management, AI-native Governance, integrierte Lebenszyklen, Experience,
Governance, messbaren Wert und kontinuierliche Verbesserung. Genau diese
Begriffe sind für NaC nützlich, weil das Projekt bereits Service-, Produkt-,
Governance-, Nachweis- und Betriebsflächen für notarielle Arbeit verbindet.

## Kurzfazit

ITIL 5 spielt für NaC eine Rolle, aber nicht als neuer Pflichtprozess.

| Wirkung | Einordnung für NaC |
| --- | --- |
| Notariats- und IT-Leitungssprache | Hilft, NaC als betreibbaren digitalen Service statt nur als Repo zu erklären. |
| Betrieb und Drittbetrieb | Wichtig für Servicekatalog, Incident, SLA/SLO, Change, Nachweisführung und Exit. |
| AI-Governance | Passt zu AI-SBOM, Human Review, Datenschutzgrenzen und auditierbarer Control Plane. |
| Auditfähigkeit | Ergänzt QMS-/ISO-9001-Nachweise, ersetzt sie aber nicht. |
| Zertifizierung | Keine Organisationszertifizierung behaupten; ITIL-Zertifikate beziehen sich auf Personen und Rollen. |

## Mapping

| ITIL-5-Begriff | NaC-Artefakte | Stand | Nächste sinnvolle Ergänzung |
| --- | --- | --- | --- |
| Digital Product and Service Management | [docs/de/README.md](README.md), [docs/de/service-model/README.md](service-model/README.md), [docs/de/architecture.md](architecture.md) | NaC beschreibt Produktkern, Servicegrenzen und Control Plane bereits zusammen. | In Notariatsgesprächen NaC als digitalen Produkt- und Servicebetrieb erklären, nicht nur als Automatisierungsrepo. |
| Servicekatalog | [docs/de/service-model/function8-service-catalog.md](service-model/function8-service-catalog.md) | Betriebsleistungen, AVV-Relevanz, Runbooks und Portabilität sind benannt. | Je Service `service_owner`, Supportpfad, SLO-Klasse und Eskalationsweg ergänzen. |
| Service Ownership und Tenant-Grenze | [docs/de/service-model/tenant-ownership-and-eventlock-service.md](service-model/tenant-ownership-and-eventlock-service.md), [policies/tenant-ownership-policy.yaml](../../policies/tenant-ownership-policy.yaml) | Betriebs- und Notariatsverantwortung sind getrennt. | Für produktive Notariats-Subinstanzen eine kompakte RACI je Service aufnehmen. |
| Change Enablement | [docs/de/governance.md](governance.md), [policies/process-policy.yaml](../../policies/process-policy.yaml), [docs/de/operations/release-sync-playbook.md](operations/release-sync-playbook.md) | Change Requests, PRs, Reviews, Risk Gates und Release-Syncs sind etabliert. | ITIL-Begriff `Change Enablement` als Alias in Notariats-/Auditunterlagen nutzen. |
| Release Management | [docs/de/operations/release-checklist.md](operations/release-checklist.md), [docs/de/operations/parallelbetrieb-version-binding.md](operations/parallelbetrieb-version-binding.md), [docs/de/operations/oci-runtime.md](operations/oci-runtime.md) | Release, Tag, Rollout, Rückfallstand und Version-Binding sind dokumentiert. | Produktive Release Notes konsequent mit Servicewirkung, Risiken und Rollback verknüpfen. |
| Incident Management | [docs/de/issues/taxonomy.md](issues/taxonomy.md), [docs/de/security-and-dsgvo.md](security-and-dsgvo.md), [policies/data-protection-policy.yaml](../../policies/data-protection-policy.yaml) | Incident-Issues, Datenschutzvorfälle und Security-Pfade sind angelegt. | Ein kurzes Incident-Playbook mit Schweregrad, Erstreaktion, Eskalation und Abschlusskriterien ergänzen. |
| Problem Management | [qms/nonconformities.schema.json](../../qms/nonconformities.schema.json), [qms/audit-program.md](../../qms/audit-program.md), [qms/management-review.md](../../qms/management-review.md) | Abweichungen, Korrekturmaßnahmen und Wirksamkeitsprüfung sind QMS-seitig vorhanden. | Wiederkehrende Incidents explizit als Problem/Korrekturmaßnahme in der QMS-Schicht spiegeln. |
| Monitoring und Event Evidence | [docs/de/eventstream/revisionssicherheit.md](eventstream/revisionssicherheit.md), [docs/de/eventstream/implementation-templates.md](eventstream/implementation-templates.md), [policies/revisionssicherheit-eventstream-policy.yaml](../../policies/revisionssicherheit-eventstream-policy.yaml) | Append-only Journal, Hash Chain, WORM-Store, Anchoring und Evidence Index sind Zielbild. | Betriebsmetriken für Ingest-Lag, Anchor-Fehler, DLQ und Restore-Test je Service dokumentieren. |
| Service Level Management | [docs/de/service-model/tenant-ownership-and-eventlock-service.md](service-model/tenant-ownership-and-eventlock-service.md), [docs/de/avv-checkliste-eventlock-saas.md](avv-checkliste-eventlock-saas.md) | SLA/SLO werden erwähnt, aber noch nicht als standardisierte Tabelle geführt. | Service-Level-Klassen für Pilot, produktiven Betrieb und revisionssichere Nachweisleistung definieren. |
| Supplier und Third-Party Management | [docs/de/service-model/third-party-operations-and-exit.md](service-model/third-party-operations-and-exit.md), [policies/provider-open-services-policy.yaml](../../policies/provider-open-services-policy.yaml) | Drittbetrieb, Exit und Ersetzbarkeit sind explizit dokumentiert. | Prüfpunkte je externer Plattform oder Subprozessor in AVV-/Drittbetriebsunterlagen spiegeln. |
| AI Governance | [docs/de/sbom-for-ai.md](sbom-for-ai.md), [docs/de/datenschutz-avv-dpa.md](datenschutz-avv-dpa.md), [docs/de/codex-parallel-review-workflow.md](codex-parallel-review-workflow.md) | AI-Touchpoints, Modell-/Daten-/Infrastrukturtransparenz, Human Review und Datenschutzgates sind vorbereitet. | Für produktive AI-Flächen Review-Metriken, Modellwechselpfad und Drift-/Fehlerraten als Release-Evidence führen. |
| Continual Improvement | [qms/quality-objectives.json](../../qms/quality-objectives.json), [qms/audit-program.md](../../qms/audit-program.md), [qms/management-review.md](../../qms/management-review.md), [roadmap/GANTT.md](../../roadmap/GANTT.md) | Qualitätsziele, interne Audits, Managementbewertung und Roadmap bilden den Verbesserungszyklus. | Verbesserungsmaßnahmen aus Incidents, Audits und Kundenfeedback einheitlich als Issues klassifizieren. |

## Konsequenz für revisionssicheren NaC-Betrieb

Für den revisionssicheren Ereignisnachweis im NaC-Betrieb ist ITIL 5 am
konkretesten relevant. Vor produktiver Nutzung mit personenbezogenen Daten
sollte der Servicekatalog mindestens diese ITIL-kompatiblen Betriebsfelder
sichtbar machen:

- `service_owner`
- `notary_office_owner`
- `support_channel`
- `incident_severity_model`
- `initial_response_target`
- `service_level_class`
- `change_window`
- `rollback_or_fallback_path`
- `evidence_and_audit_path`
- `exit_path`

Diese Felder ändern nicht die NaC-Architektur. Sie machen aber klar, wer bei
Störung, Änderung, Audit, Drittbetriebswechsel und Notariatsfreigabe handelt.

## Was wir nicht tun

- Keine Behauptung, NaC oder notariat8 sei ITIL-zertifiziert.
- Keine Ersetzung von ISO 9001, Datenschutz, Berufsrecht oder notarieller
  Verantwortung durch ITIL.
- Keine zusätzliche Prozessbürokratie für kleine Doku- oder Referenzrepo-
  Änderungen.
- Keine Ablage echter Mandatsdaten, Secrets oder vertraulicher Incident-Details
  im öffentlichen Repo.

## Empfohlene nächste Schritte

| Priorität | Aufgabe | Ergebnis |
| --- | --- | --- |
| P0 | Dieses Mapping in Notariats-, Prüfungs- und Servicegesprächen als Orientierung nutzen. | Gemeinsame Sprache ohne Framework-Overhead. |
| P1 | Servicekatalog um die ITIL-kompatiblen Betriebsfelder für revisionssicheren NaC-Betrieb erweitern. | Betrieb ist besser prüfbar. |
| P1 | Incident-Playbook für NaC-Betrieb und Notariatsumgebungen ergänzen. | Schweregrad, Meldeweg und Abschluss sind eindeutig. |
| P2 | SLO-Klassen für Pilot, Produktivbetrieb und revisionssichere Nachweisleistung definieren. | SLA-/AVV-Gespräche werden konkreter. |
| P2 | Wiederkehrende Incidents und Notariatsfeedback in QMS-Abweichungen und Managementbewertung spiegeln. | Continual Improvement wird nachweisbar geschlossen. |
