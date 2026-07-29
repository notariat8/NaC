# Workflow-Verträge

Dieser Ordner ist für Workflow-Verträge reserviert. Ein Vertrag beschreibt
die Grenze zwischen einem notariellen Usecase, einem oder mehreren Plugins und
deterministischer Workflow-Ausführung.

Jeder Vertrag soll definieren:

- Eingabeschema
- Ausgabeschema
- erforderliche Rollen
- erforderliche Freigaben
- erforderliche Plugin-Gates
- Datenklasse
- Form des Nachweisdatensatzes

Ergänzend können wiederkehrende agentische Definition-of-Done-Fragen als
Verification Contracts unter [../verification-contracts/](../verification-contracts)
modelliert werden. Diese Verträge beschreiben `applies_when`, benötigten
Kontext, Checks, Invarianten, Thresholds, Evidence, Pass-Bedingung und
Fehlerverhalten. Sie ersetzen die fachlichen Domain-Contracts nicht, sondern
machen die Abnahmeharness agentisch lesbar.

## Implementierte Verträge

- [workflows/contracts/kg-editor.contract.json](kg-editor.contract.json):
  KG-Editor-Vertrag zum Rendern usecase-lokaler
  [knowledge-graph.graph.json](../../usecases/immobilienkaufvertrag/knowledge-graph.graph.json)
  Dateien als sichere Formulare, Checklisten und Patch-Vorschläge, ohne
  `value`-Felder für Fachpersonal offenzulegen.
- [workflows/contracts/bpmn-js-editor.contract.json](bpmn-js-editor.contract.json):
  BPMN-js-Editor-Vertrag für visuell bearbeitbare BPMN-2.0-Prozessmodelle mit
  NaC-Properties, Python-Validierung und Pull-Request-Freigabe.
- [workflows/contracts/notarkammer-process-editor.contract.json](notarkammer-process-editor.contract.json):
  Notarkammer-Prozess-Editor-Vertrag für demo-sichere BPMN-Bearbeitung und
  BPMN-Ansicht mit XNP/SNP-Gates, Dauerbändern, Parallelgruppen und kritischem
  Pfad ohne Mandatsdaten oder produktiven Fachsystemzugriff.
- [workflows/contracts/local-web-preview.contract.json](local-web-preview.contract.json):
  lokaler Webserver-Vertrag für grafische BPMN- und KG-Ausgaben ohne Cloud-
  oder Mandatsdatenpflicht.
- [workflows/contracts/gnotkg-cost-review.contract.json](gnotkg-cost-review.contract.json):
  GNotKG-Kostenvertrag für zentrale Wertgebührenlogik, Kostenprüfgates in
  allen notariellen Usecases und eine spätere `xyflow`-Ansicht als reine
  Review- und Erklärungsschicht.
- [workflows/contracts/secure-document-link.contract.json](secure-document-link.contract.json):
  Vertrag für mobile Mandanten-/Beteiligten-Apps und sichere Upload- oder
  Leselinks auf Object Store, Datenbank-Blob oder OneDrive mit Zweckbindung,
  Ablauf, Aktenbindung, Widerruf und Auditnachweis.
- [workflows/contracts/legal-research-connectors.contract.json](legal-research-connectors.contract.json):
  Kandidateninventar für juristische Recherche-, MCP-, Verlagsdatenbank- und
  externe Legal-Produkt-Referenzen ohne Produktintegration, Credentials oder
  Mandatsdaten, mit Lizenz-, AVV-, AI-SBOM- und Review-Gates.
- [workflows/contracts/legal-source-inventory-license-tdm.contract.json](legal-source-inventory-license-tdm.contract.json):
  Quelleninventar-, Lizenz- und TDM-Gate für spätere Legal-Nemotron- oder
  Rechtsgraph-Arbeit ohne Quellentext-Ingestion, Benchmark-Datensatz,
  Modelllauf oder Training.
- [workflows/contracts/legal-graph.contract.json](legal-graph.contract.json):
  Vertrag für den mandatsdatenfreien NaC-Rechtsgraphen mit Primärquellen,
  Erbrechts-, Familienrechts- und Gesellschaftsrechts-MVPs, Review-Patches und
  No-Auto-Merge-Regel.
- [workflows/contracts/legal-model-customization-readiness.contract.json](legal-model-customization-readiness.contract.json):
  Readiness-Vertrag für spätere Legal-Nemotron-Modellanpassung mit
  Quellenhierarchie, Lizenz-/TDM-, Benchmark-, Evaluation-, Model-Card-,
  AI-SBOM- und Owner-Apply-Gates, ohne Trainingsstart.
- [workflows/contracts/legal-model-card-ai-sbom-delta.contract.json](legal-model-card-ai-sbom-delta.contract.json):
  Delta-Vertrag für spätere Legal-Nemotron-Model-Card- und AI-SBOM-
  Aktualisierungen ohne Training, Checkpoint-Veröffentlichung,
  Quellentextspeicherung oder Qualitätsbehauptung.
- [workflows/contracts/legal-model-evaluation-benchmark.contract.json](legal-model-evaluation-benchmark.contract.json):
  Benchmark-Blueprint für spätere Legal-Nemotron-Evaluationen mit
  Quellenhierarchie, Holdout-Regeln, Aufgabenfamilien, BYOB/MCQ- und
  `eval/model_eval`-Routing, ohne Benchmark-Datensatz, Modelllauf oder
  Qualitätsbehauptung.
- [workflows/contracts/legal-commentary-connectors.contract.json](legal-commentary-connectors.contract.json):
  Vertrag für lizenzierte Kommentar- und Verlagsquellen über MCP/API ohne
  Credentials, Mandatsdaten oder Kommentar-Volltexte im Produktrepo, mit
  Provider-Matrix für Lizenzbasis, AVV-/DPA-Status, Berufsgeheimnis,
  AI-SBOM, Sicherheitsgrenze, Credential-Betrieb, Evidence-Felder und
  Aktivierungsgates.
- [workflows/contracts/customer-tenant-onboarding.contract.json](customer-tenant-onboarding.contract.json):
  Vertrag für die sichtbare Neukundenreise von `www-n8` nach NaC mit
  Domain-Readiness, DNS-TXT-Challenge, SaaS-Admin-Review, Teams,
  SharePoint-Team-Site, Microsoft Graph REST und Owner-Apply-Gate ohne
  Mandatsdaten oder Credential-Material im Produktrepo.
- [workflows/contracts/codex-parallel-review.contract.json](codex-parallel-review.contract.json):
  Vertrag für explizite, parallele Codex-Reviews mit read-only Agentprofilen,
  Scope-Mapping, KG-/BPMN-/Policy-/Doku-/Validierungsprüfung, Guardrails und
  frischem Nachweis vor Abnahme.
- [workflows/contracts/nac-onprem-agent-runtime.contract.json](nac-onprem-agent-runtime.contract.json):
  archivierter Legacy-Vertrag für die OCI-gebundene NaC-On-Prem-Agent-Runtime;
  nicht Teil der aktiven M365-MVP-Spur.
- [workflows/contracts/teams-sharepoint-graph-data-plane.contract.json](teams-sharepoint-graph-data-plane.contract.json):
  Vertrag für die MVP-Datenhaltung über Teams Team, Microsoft-365-Gruppe,
  SharePoint-Team-Site, Microsoft Graph REST only, declaratives Schema,
  Provisioner-Skeleton, MCP-Grenze und Owner-Gates ohne Live-Apply.
- [workflows/contracts/microsoft-first-onprem-target-architecture.contract.json](microsoft-first-onprem-target-architecture.contract.json):
  Entscheidungsvertrag für Teams, SPFx, SharePoint, Entra und Graph REST v1.0
  als Microsoft-Kante sowie Python/FastAPI, deterministische Workflows, NVIDIA
  NeMo Agent Toolkit, PostgreSQL, Outbox/Broker und Evidence-Publisher als
  On-Prem-Kern sowie Azure Blob Immutable Storage als autoritative, getrennte
  WORM-Evidence-Kopie; Temporal bleibt ein zeitbegrenzter Spike-Kandidat.
- [workflows/contracts/m365-azure-bff-activation-plan.contract.json](m365-azure-bff-activation-plan.contract.json):
  Hashgebundener Offline-One-Shot-Plan für die feste Azure-Subscription,
  Entra-API, Managed-Identity-Sites.Selected-Bindung, exakten Site-Read-Grant,
  Azure-Functions-Deployment, SPFx-AadHttpClient-Cutover, synthetischen Seed,
  Zugriffstests, Idempotenz und redigierte Evidence; Live-Aktionen bleiben bis
  zum einzigen konsolidierten Owner-Gate ausgesetzt.
- [workflows/contracts/m365-sharepoint-bpmn-viewer-adapter.contract.json](m365-sharepoint-bpmn-viewer-adapter.contract.json):
  Vertrag für einen späteren read-only SPFx-BPMN-Viewer in SharePoint mit
  `bpmn-js`, Microsoft Graph REST only, freigegebenen BPMN-Modellkopien oder
  Pointern, optionalem Provisioning-Plan für `BPMN Models` und
  `Prozessregister`, source-only Skeleton unter `spfx/nac-bpmn-viewer`,
  `bpmn-viewer-runtime-readiness` für SPFx-Paketierungs-, App-Catalog- und
  `.bpmn`-Graph-Content-Read-Gates, Prozessregister-Metadaten und ohne
  Modeler, Workflow-Ausführung, Mandatsdaten, alte SharePoint-APIs, SDKs,
  App-Catalog-Deploy oder Live-Tenant-Apply.
- [workflows/contracts/teams-sharepoint-data-mcp.contract.json](teams-sharepoint-data-mcp.contract.json):
  Vertrag für den ersten `teams-sharepoint-data-mcp`-Runtime-Skeleton mit
  Tool-Manifest, MCP-stdio-Adapter, Rollen-/Akten-/Zweckgate,
  Graph-REST-Request-Planung, owner-gated Live-Reads für `case_get` und
  `document_list`, optionalen BPMN-Viewer-Request-Plan-Tools,
  metadata-only Werkzeugen für das notarielle Schnittstelleninventar,
  redigierten `mcp-inventory-smoke` und `mcp-live-read-smoke` sowie ohne
  Live-Writes, Secrets, Dateiinhalt oder Mandatsdaten im Produktrepo.
- [workflows/contracts/m365-matter-access-delegation.contract.json](m365-matter-access-delegation.contract.json):
  Vertrag für M365-Aktensichtbarkeit und zeitlich begrenzte
  Vertretungsfreigaben über `Akten`, `Vertretungsfreigaben`,
  `AuditJournalLite` und `teams-sharepoint-data-mcp`; `matter-access-plan`
  rendert nur Graph-REST-Requestpläne ohne Live-Tenant-Aktion,
  `matter-access-apply-readiness` prüft die spätere owner-gated Apply-Grenze
  und `matter-access-apply-request-plan` schreibt einen redigierten Auftrag
  für `grant_request` plus `audit_append` ohne Live-Apply; ergänzend spielt
  `matter-access-decision-replay` synthetische SharePoint-Listensnapshots für
  Zugriffentscheidungen lokal nach, ohne Dateiinhalt, Secrets,
  Graph-Requests oder Mandats-Rohdaten.
- [workflows/contracts/notarial-ontology-sizing-storage.contract.json](notarial-ontology-sizing-storage.contract.json):
  Vertrag für Ontologie-Sizing und Storage-Grenzen aus dem
  Geschäftsvorfall-Inventar; SharePoint bleibt operative M365-MVP-Datenhaltung,
  die Ontologie bleibt versionierter Projektionsvertrag über usecase-lokalen
  KGs, Microsoft Graph REST v1.0 bleibt einzige M365-Datenebene und globale
  Runtime-Reasoning-, Dokumentvolltext-, Mandatswert- oder zentrale KG-Ablage
  bleiben blockiert.
- [workflows/contracts/notarial-process-ontology.contract.json](notarial-process-ontology.contract.json):
  Vertrag für das fachliche Prozess-/Ontologie-Produktmodell über alle
  Geschäftsvorfälle; definiert Geschäftsvorfalltypen, Prozessphasen, Rollen,
  Aufgaben, Dokumentzeiger, Evidence, Audit, Vertretungsfreigaben,
  BPMN-Zeiger und SharePoint-MVP-Projektionen, ohne Live-Apply, Mandatswerte,
  Dokumentvolltexte, Runtime-Reasoning oder zentrale KG-Ablage.
- [workflows/contracts/agent-runtime-registry.contract.json](agent-runtime-registry.contract.json):
  archivierter Legacy-Vertrag für die ATP-gestützte Agent-Registry; nicht
  aktive MVP-Datenhaltung.
- [workflows/contracts/agent-control-api.contract.json](agent-control-api.contract.json):
  archivierter Legacy-Vertrag für die OCI/BFF-API-Grenze von
  `agent.notariat8.de`; nicht aktiver MVP-Pfad.
- [workflows/contracts/notarial-onprem-connector-boundaries.contract.json](notarial-onprem-connector-boundaries.contract.json):
  Vertrag für XNP/SNP, XNotar, cyberJack/Kartenarbeitsplatz sowie Register-
  und Grundbuchpfade als lokale Readiness- und redigierte Evidence-Grenzen
  ohne Credentials, Mandatsdaten oder Live-Apply.
- [workflows/contracts/notarial-application-interface-inventory.contract.json](notarial-application-interface-inventory.contract.json):
  Metadaten-Inventar für owner-provided BNotK-Anwendungsschnittstellen, beN
  und XJustiz 3.3.1 mit read-only MCP-Zielgrenze, ohne Volltext-Ingestion,
  XSD-Rohkopie, Credentials, Mandatsdaten oder Live-Apply.
- [workflows/contracts/xnotar-xjustiz-package-boundary.contract.json](xnotar-xjustiz-package-boundary.contract.json):
  Offline-Paketgrenze für XNotar/XJustiz-Exchange-Folder-Readiness mit
  `attachments/`, erwartetem `xjustiz_nachricht.xml`-Pointer,
  referenzierten Anlagen, relativen Pfaden, Counts, Hash-/Pointer-Status und
  redigierter Evidence, ohne XNotar-Import, beN-Versand, XSD-/WSDL-Kopie,
  XML-Payloads, echte Pakete, Urkunden-, Register- oder Grundbuchdaten.
- [workflows/contracts/matter-data-classification-redaction.contract.json](matter-data-classification-redaction.contract.json):
  Vertrag für Mandatsdaten-Klassifikation, Redaktionsnachweise und
  Speichergrenzen zwischen GitHub, Webapp-Status, M365/SharePoint-Metadaten,
  redigierter Evidence und späterem privaten Betriebsrahmen.
- [workflows/contracts/private-operating-frame-gate.contract.json](private-operating-frame-gate.contract.json):
  Gate-Vertrag für den späteren privaten Betriebsrahmen mit Datenschutz-,
  Rollen-, Speicher-, Verschlüsselungs-, Retention-, Audit- und Owner-Gates,
  ohne produktiven Apply.
- [workflows/contracts/private-payload-target-design.contract.json](private-payload-target-design.contract.json):
  logisches Envelope-/Pointer-Zielbild für spätere private Payloads mit
  Zugriffsgates, Hashes, Retention, Audit und Speicherzielgrenzen, ohne DDL-
  Artefakt, Apply oder private Beispieldaten.
- [workflows/contracts/private-payload-access-policy.contract.json](private-payload-access-policy.contract.json):
  Rollen-, Zweck- und Zugriffsmatrix für spätere private Payloads mit Step-up,
  Human Review, Audit, globalen Ablehnungen und ohne Live-Zugriff oder private
  Beispieldaten.
- [workflows/contracts/runtime-status-wiring-runbook.contract.json](runtime-status-wiring-runbook.contract.json):
  Runtime-Status-Vertrag für die sichere Brücke vom aktuellen
  `InMemoryRuntimeStore`-Demo-Pfad zur späteren M365/SharePoint- und
  Event-Journal-gestützten Prozessinstanz-Anzeige, ohne Mandatsdaten, Secrets
  oder produktiven Cloud-Apply.

- [business-case-type-runtime.contract.json](business-case-type-runtime.contract.json): Offline-S3-Vertrag für die sechs Akzeptanzkriterien aus Issue #612: exakte BusinessCaseTypeId- und Aliasauflösung, Registry-Kardinalität/Version/Status, Cache-TTL/Invalidierung, Viewer-Isolation, ETag/Datenminimierung sowie CLI- und Strict-Gate-Nachweis ohne Graph-, HTTP- oder Credential-Zugriff.

- [business-case-type-graph-read-edge.contract.json](business-case-type-graph-read-edge.contract.json): In PR #617 offline implementierter S4-Read-Edge-Vertrag für Issue #616 mit exakt `Sites.Selected` plus Site-Grant `read`, Graph REST v1.0 GET, Same-Filter-Paging, lokaler Row-ETag-Auswertung, Redaction und Viewer-Isolation.
- [business-case-type-graph-write-edge-s4b.contract.json](business-case-type-graph-write-edge-s4b.contract.json): Offline implementierter S4b-Write-Edge-Vertrag für Issue #694 mit den fünf exakt begrenzten Operationen `case_create`, `case_status_update`, `task_create`, `task_update` und `business_case_type_backfill`, separater `Sites.Selected`-/`write`-Identität, ETag-/S5-Hashbindung, dokumentiertem Dedupe-Query, frischem konkretem Item-Readback auch nach HTTP 409, Dual-Schema- und Textlängenprüfung, zielgebundener persistenter Reconciliation mit neuer Authorization-Run-Identity für Retryable-Läufe und dem ausschließlich synthetischen, redigierten Dry-Run `nac m365 teams-sharepoint business-case-type-write-dry-run`; Live-Graph-Aufrufe und Tenant-Writes bleiben null, produktive Komposition und Live-Write bleiben owner-gated.
- [business-case-type-graph-write-composition-s4c.contract.json](business-case-type-graph-write-composition-s4c.contract.json): Offline implementierte S4c-Komposition für Issue #698 mit lokalem SQLite-CAS-/Evidence-State, injiziertem Graph-REST-v1.0-Transport, exakt zwei gebundenen Collections, null Auto-Retries und einem synthetischen Fünf-Operationen-Smoke; Netzwerk, externe Credential-Reads, Live-Graph und Tenant-Writes bleiben null, zentrale Durability und Live-Factory bleiben außerhalb des Scopes.
- [business-case-type-live-write-boundary-s4d.contract.json](business-case-type-live-write-boundary-s4d.contract.json): Owner-gated S4d-Produktionsgrenze aus S4c, getrennter `Sites.Selected/write`-Identität, S6-v0.2-Evidence und S6b-Azure-WORM-Port. Der Fünf-Operationen-Smoke bleibt strikt offline; produktive Identity-/Outbox-/Broker-/Signatur-/Reconciliation-Adapter und jeder Tenant-Write bleiben geblockt.
- [business-case-type-migration-s5.contract.json](business-case-type-migration-s5.contract.json): Deterministischer S5-Offline-Migrationsvertrag für Issue #618 mit AC-S5-01 bis AC-S5-07, sieben Inventarklassen, exaktem Vier-Werte-Mapping, idempotentem Backfill-Plan, persistenter lokaler Quarantäne, unabhängig erfassten stabilen Endscans, leerem Quarantäne-Gate und N-/N-1-Profil-Evaluation; Live-Aufrufe und Tenant-Writes bleiben null.
- [business-case-type-immutable-evidence-s6.contract.json](business-case-type-immutable-evidence-s6.contract.json): S6a-Offline-Foundation für Issue #687 mit kanonischen Intent-, Outcome-, Readback- und Reconciliation-Ereignissen, HMAC-pseudonymer ActorRef, Hashkette, Retention- und Legal-Hold-Metadaten sowie expliziten PostgreSQL-, Broker-, Anchor-, WORM- und Reconciliation-Ports; Live-Mutationen bleiben bis S7 blockiert und es wird keine Produktions-WORM-Wirkung behauptet.
- [business-case-type-azure-blob-worm-s6b.contract.json](business-case-type-azure-blob-worm-s6b.contract.json): Offline-S6b-Vertrag für Issue #693 mit create-only, versionsgebundenem Azure-Blob-WORM-Adapter, tenantgebundener CMK-/Policy-Prüfung, delete-freier Writer-Rolle und autoritativer Azure-Evidence-Kopie eines on-prem Publishers; Deployment und Lock bleiben blockiert.
- [azure-blob-worm-irreversible-lock-s6b.contract.json](azure-blob-worm-irreversible-lock-s6b.contract.json): Separater, nicht ausführbarer Lock-Plan für Target-/Tenant-/Policy-, ETag-, Request-Hash- und Dual-Control-Bindung; S6b enthält keine Live-Lock-Kante.
- [m365-azure-bff-offline-readiness.contract.json](m365-azure-bff-offline-readiness.contract.json): Offline-Readiness-Vertrag für Issue #620 mit deterministischem Azure-Functions-Paket, manifest- und importgeprüfter Python-3.12-Quelle, vollständig gehashter 24-Pakete-Abhängigkeitsauflösung einschließlich `azure-identity`, UAMI-gebundenem `ManagedIdentityCredential` und hashgebundenem Bicep-Compile-Nachweis ohne Environment-, Secret-, Netzwerk-, Azure- oder Graph-Zugriff.
- [m365-azure-bff-offline-readiness.verification.json](../verification-contracts/m365-azure-bff-offline-readiness.verification.json): Verification Contract und redigierter Evidence-Deskriptor für AC-620-01 bis AC-620-07; `READY` erfordert byteidentische In-Memory-Builds, exakte Lock-Integrität, UAMI-Adapter und frische, in CI mit Bicep 0.45.6 reproduzierte `az bicep build`-/`build-params`-Artefakte sowie einen verpflichtenden Flex-OneDeploy-Remote-Build.
- [m365-azure-bff-live-activation.contract.json](m365-azure-bff-live-activation.contract.json): Owner-gated Live-Aktivierungsvertrag für Issue #632 mit exakten Azure-/M365-Zielbindungen, zwölf geordneten Schritten, hashgebundenen Prepared Inputs, deaktiviertem MVP-Resume und strikt redigierter Evidence. [validate_m365_azure_bff_live_activation.py](../../scripts/validate_m365_azure_bff_live_activation.py) prüft Domain- und Verification-Contract strukturell gegen Runner-Konstanten, Implementierungsmarker und Negativtests und ist Bestandteil des strikten Quality Gates. Der Offline-Safety-Rework aus Issue #664 ergänzt den kanonischen `bff-azure-activation-owner-gate`: exakter kompakter Kommentar ohne abschließende Newline, gemeinsamer Binding-Hash mit dem Verifier, doppelte Clean-Tree-Prüfung und atomisches `NOT_READY` ohne partielle Approval-Payload. Issue #666 ergänzt den Pre-Write-Provisioner-Bootstrap mit expliziten State-/Zertifikat-/Private-Key-Pfaden, redigierter Readiness, Metadaten- und Tenant-/App-Bindungsprüfung sowie einer nur an die Live-Factory übergebenen Env-Kopie ohne Mutation der globalen Prozessumgebung. Das Security-Rework bindet zusätzlich den atomar und größenbegrenzt gelesenen Provisioning-State sowie gehashte State-, Zertifikat- und Private-Key-Pfade über `provisioner_bootstrap_binding_sha256` exakt an Owner-Payload, generierte Live-Argumentmap, Live-Aufruf und Recovery; Abweichungen stoppen vor Providerzugriff und Write. Issue #671 bindet die owner-gated Provisioning-App an eine exakte Sechser-Allowlist einschließlich `Sites.FullControl.All` und trennt sie strikt von Runtime-App und BFF-UAMI mit `Sites.Selected`/`read`; ein verpflichtendes read-only Rollen-Inventar und der Capability-Probe auf `GET /sites/{siteId}/permissions` stoppen vor dem ersten Provider-Write bei fehlenden, doppelten, breiteren oder nicht wirksamen Rechten.
- [business-case-type-production-adapters-s4f.contract.json](business-case-type-production-adapters-s4f.contract.json): Partieller Offline-S4f-Vertrag für Issue #704 mit exakt gebundenem Owner-Kommentar-Verifier, zertifikatsbasierter Writer-Factory, redirect-freiem Graph-v1.0-HTTP-Port und lokaler SQLite-Evidence-Staging-Outbox ohne Abschlussrecht; PostgreSQL-Promotion/Ack/Retention/lokales Cleanup, Broker, Signatur, provider-seitiger Identity-Readback, WORM-Transport/Lock und jede Runtime-/Live-Aktivierung bleiben explizite Blocker.
