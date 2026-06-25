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
- [workflows/contracts/runtime-status-wiring-runbook.contract.json](runtime-status-wiring-runbook.contract.json):
  Runtime-Status-Vertrag für die sichere Brücke vom aktuellen
  `InMemoryRuntimeStore`-Demo-Pfad zur späteren ATP-gestützten
  Prozessinstanz-Anzeige, ohne Mandatsdaten, Secrets oder OCI-Apply.
