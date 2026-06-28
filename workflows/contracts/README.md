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
  Kandidateninventar für juristische Recherche-, MCP- und Verlagsdatenbank-
  Connectoren ohne Produktintegration, Credentials oder Mandatsdaten, mit
  Lizenz-, AVV-, AI-SBOM- und Review-Gates.
- [workflows/contracts/legal-graph.contract.json](legal-graph.contract.json):
  Vertrag für den mandatsdatenfreien NaC-Rechtsgraphen mit Primärquellen,
  Erbrechts-, Familienrechts- und Gesellschaftsrechts-MVPs, Review-Patches und
  No-Auto-Merge-Regel.
- [workflows/contracts/legal-model-customization-readiness.contract.json](legal-model-customization-readiness.contract.json):
  Readiness-Vertrag für spätere Legal-Nemotron-Modellanpassung mit
  Quellenhierarchie, Lizenz-/TDM-, Benchmark-, Evaluation-, Model-Card-,
  AI-SBOM- und Owner-Apply-Gates, ohne Trainingsstart.
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
- [workflows/contracts/oci-tenant-identity.contract.json](oci-tenant-identity.contract.json):
  Vertrag für tenant-aware NaC-SaaS-Onboarding mit Oracle OCI Identity Domains,
  Domain-Readiness, Admin-Provisioning-Dry-run und Owner-Apply-Gate vor jedem
  produktiven Identity-Write.
- [workflows/contracts/customer-tenant-onboarding.contract.json](customer-tenant-onboarding.contract.json):
  Vertrag für die sichtbare Neukundenreise von `www-n8` nach NaC mit
  Domain-Readiness, DNS-TXT-Challenge, SaaS-Admin-Review, Owner-Apply-Gate,
  OCI-IAM-Domain-/Compartment-Zielbild und gemeinsamer ATP-Tenant-Mapping-
  Logik ohne Mandatsdaten oder Credential-Material im Produktrepo.
- [workflows/contracts/codex-parallel-review.contract.json](codex-parallel-review.contract.json):
  Vertrag für explizite, parallele Codex-Reviews mit read-only Agentprofilen,
  Scope-Mapping, KG-/BPMN-/Policy-/Doku-/Validierungsprüfung, Guardrails und
  frischem Nachweis vor Abnahme.
- [workflows/contracts/nac-onprem-agent-runtime.contract.json](nac-onprem-agent-runtime.contract.json):
  Vertrag für die NaC-On-Prem-Agent-Runtime auf `notoclaw01` mit
  NemoClaw/OpenClaw-Zielsystemgrenze, Target-Control-Pfaden, Connector-Stubs,
  Handoff-Regeln, Owner-Gates und Quality-Gate-Validator.
- [workflows/contracts/notarial-onprem-connector-boundaries.contract.json](notarial-onprem-connector-boundaries.contract.json):
  Vertrag für XNP/SNP, XNotar, cyberJack/Kartenarbeitsplatz sowie Register-
  und Grundbuchpfade als lokale Readiness- und redigierte Evidence-Grenzen
  ohne Credentials, Mandatsdaten oder Live-Apply.
- [workflows/contracts/matter-data-classification-redaction.contract.json](matter-data-classification-redaction.contract.json):
  Vertrag für Mandatsdaten-Klassifikation, Redaktionsnachweise und
  Speichergrenzen zwischen GitHub, `notoclaw01`, Webapp-Status, ATP-Metadaten
  und späterem privaten Betriebsrahmen.
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
  `InMemoryRuntimeStore`-Demo-Pfad zur späteren ATP-gestützten
  Prozessinstanz-Anzeige, ohne Mandatsdaten, Secrets oder OCI-Apply.
