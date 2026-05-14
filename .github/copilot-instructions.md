# GitHub Copilot Instructions

Dieses Repository ist ein Muster fuer `Notariat as Code` mit `NoC` als konkreter Betriebsauspraegung.

## Verbindliche Prioritaet

1. Compliance und rechtliche Pflichten
2. Prozessgovernance (Review, Freigaben, Nachvollziehbarkeit)
3. Branchenmodule
4. Kultur- und Sprachvorgaben

## Arbeitsweise

- Behandle das LLM als Assistent fuer Eingaben, nicht als finale fachliche Autoritaet.
- Rahmen: `Notariat as Code` + `Enterprise GitOps`; `NoC` ist die konkrete Umsetzung.
- Schlage keine direkten Aenderungen an `main` vor.
- Erzwinge Vorschlaege ueber Branch + Pull Request + Review.
- Sensible Prozessschritte (z. B. Steuer, Zahlungsfreigaben) brauchen Vier-Augen-Prinzip.
- Jede Prozessaenderung muss begruendet und versioniert sein.
- Ein Update gilt erst als abgeschlossen, wenn die Aenderung validiert, committed, zu GitHub gepusht und in den Zielbranch gemerged wurde.
- Jeder Push muss `roadmap/GANTT.md` aktualisieren; Aenderungen unter `plugins/`, `workflows/` oder `usecases/` muessen zusaetzlich das jeweilige Themen-Gantt aktualisieren.
- Trenne installierbare Plugin-Artefakte (`plugins/`), ausfuehrbare Notariats-Workflows (`workflows/`) und konkrete notarielle Usecases (`usecases/`).
- Konzept- und Regelupdates muessen plattformuebergreifend synchronisiert werden (Cursor und VS Code + Copilot).
- Onboarding-Updates muessen fuer alle unterstuetzten Plattformen parallel gepflegt werden.
- Access- und Rollenregeln sind nur unter `policies/` zu aendern; AI-Regelflaechen sind Spiegel dieser Policy.
- Mehrsprachigkeit ist verbindlich nach `policies/language-policy.yaml`.
- Sprachabhaengige Inhalte liegen in ISO-639-Ordnern; `de` und `en` sind immer zu pflegen.
- Die Sprache des Prompts begrenzt die Aenderung nicht: bei lokalisierten Inhalten immer alle Standardsprachen aktualisieren.
- Standard-MVP-Module im Referenzrepo sind synchron: `software_company`, `notary`, `wealth_management`.
- Zusaetzlicher MVP-Use-Case: `property_management`.
- Plugin- und Connector-Plaene liegen unter `docs/plugin-plans/`.
- NoC-Ausfuehrung und Plugin-Regeneration erfolgen lokal in WSL im Workspace `~/NoC`, nicht ueber Omnistation.

## Pflichtquellen im Repository

- `docs/de/START_HERE.md`
- `docs/en/START_HERE.md`
- `docs/de/fachanwender-guide.md`
- `docs/en/fachanwender-guide.md`
- `policies/culture-policy.yaml`
- `policies/process-policy.yaml`
- `policies/technology-policy.yaml`
- `policies/data-protection-policy.yaml`
- `policies/language-policy.yaml`
- `docs/de/avv-checkliste-eventlock-saas.md`
- `policies/sbom-policy.yaml`
- `policies/role-model-policy.yaml`
- `policies/access-control-policy.yaml`
- `policies/revisionssicherheit-eventstream-policy.yaml`
- `policies/tenant-ownership-policy.yaml`
- `policies/provider-open-services-policy.yaml`
- `policies/github-identity-registry.json`
- `docs/de/governance.md`
- `docs/de/eventstream-implementation-templates.md`
- `docs/de/eventstream-runbook-aws.md`
- `docs/de/eventstream-runbook-azure.md`
- `docs/de/eventstream-runbook-gcp.md`
- `docs/de/eventstream-runbook-oci.md`
- `docs/de/tenant-ownership-and-eventlock-service.md`
- `docs/de/function8-service-catalog.md`
- `docs/de/third-party-operations-and-exit.md`
- `docs/de/organization-as-code-positioning.md`
- `docs/de/fork-and-release-operating-model.md`
- `docs/de/release-sync-playbook.md`
- `docs/de/parallelbetrieb-version-binding.md`
- `docs/de/issue-taxonomie-pro-repo.md`
- `docs/de/einfuehrung-greenfield-brownfield.md`
- `docs/de/service-business-core-vertical-blueprint.md`
- `docs/de/vertical-starter-prozesskatalog.md`
- `docs/de/repo-refactor-plan-single-repo-modules.md`
- `docs/de/plugin-plans/README.md`
- `docs/de/arbeitsmodell-agile-cadence.md`
- `docs/de/access-and-issue-operations.md`

## Sprache und Kultur

- Folge immer `policies/culture-policy.yaml`.
- Folge immer `policies/language-policy.yaml`.
- Lokal gepflegte Inhalte muessen immer in `de` und `en` aktualisiert werden.
- Bei Genderfragen gilt die konfigurierte Policy.
- Wenn keine Policy gesetzt ist, nutze neutrale Sprache und bitte einmal um Entscheidung.

## Datenschutz und Sicherheit

- Keine echten Zugangsdaten, Keys oder Tokens in Vorschlaegen speichern.
- Keine echten personenbezogenen Daten in Prozessbeispielen speichern.
- Fuer Beispieldaten nur Testdomains und Platzhalter verwenden.

## Technikvorgaben

- Folge `policies/technology-policy.yaml` als verbindlichem Stack.
- Markdown ist die einzige manuell gepflegte Doku-Quelle.
- BPMN-2.0 ist die fachliche Quellnotation fuer Prozesse.
- Mermaid darf nur als Uebersicht eingesetzt werden.

## Erststart fuer VS Code + Copilot

1. Lies `docs/de/vscode-copilot-start.md` oder `docs/en/vscode-copilot-start.md`.
2. Fuehre `python scripts/startup_check.py --ide vscode --run-tests` aus.
3. Waehle das passende Branchen-Onboarding unter `prompts/de/onboarding/` oder `prompts/en/onboarding/`.
   Bevorzugte Defaults: `software-company-first-setup.md`, `notary-first-setup.md`, `wealth-management-first-setup.md`.
   Zusaetzlicher MVP-Pfad: `property-management-first-setup.md`.
4. Beginne mit einem Pilotprozess statt Vollausrollung.
5. Nutze fuer Fork-Betrieb, Sync und Mischbetrieb die neuen Betriebsdokumente in `docs/de/` und `docs/en/`.
