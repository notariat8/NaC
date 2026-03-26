# GitHub Copilot Instructions

Dieses Repository ist ein Muster fuer `Organization as Code` mit `OaC8` als konkreter Betriebsauspraegung.

## Verbindliche Prioritaet

1. Compliance und rechtliche Pflichten
2. Prozessgovernance (Review, Freigaben, Nachvollziehbarkeit)
3. Branchenmodule
4. Kultur- und Sprachvorgaben

## Arbeitsweise

- Behandle das LLM als Assistent fuer Eingaben, nicht als finale fachliche Autoritaet.
- Rahmen: `Organization as Code` + `Enterprise GitOps`; `OaC8` ist die konkrete Umsetzung.
- Schlage keine direkten Aenderungen an `main` vor.
- Erzwinge Vorschlaege ueber Branch + Pull Request + Review.
- Sensible Prozessschritte (z. B. Steuer, Zahlungsfreigaben) brauchen Vier-Augen-Prinzip.
- Jede Prozessaenderung muss begruendet und versioniert sein.
- Konzept- und Regelupdates muessen plattformuebergreifend synchronisiert werden (Cursor und VS Code + Copilot).
- Onboarding-Updates muessen fuer alle unterstuetzten Plattformen parallel gepflegt werden.
- Access- und Rollenregeln sind nur unter `policies/` zu aendern; AI-Regelflaechen sind Spiegel dieser Policy.
- Standard-MVP-Module im Referenzrepo sind synchron: `software_company`, `notary`, `wealth_management`.
- Zusaetzlicher MVP-Use-Case: `property_management`.

## Pflichtquellen im Repository

- `docs/START_HERE.md`
- `docs/fachanwender-guide.md`
- `policies/culture-policy.yaml`
- `policies/process-policy.yaml`
- `policies/technology-policy.yaml`
- `policies/data-protection-policy.yaml`
- `docs/avv-checkliste-eventlock-saas.md`
- `policies/sbom-policy.yaml`
- `policies/role-model-policy.yaml`
- `policies/access-control-policy.yaml`
- `policies/revisionssicherheit-eventstream-policy.yaml`
- `policies/tenant-ownership-policy.yaml`
- `policies/provider-open-services-policy.yaml`
- `policies/github-identity-registry.json`
- `docs/governance.md`
- `docs/eventstream-implementation-templates.md`
- `docs/eventstream-runbook-aws.md`
- `docs/eventstream-runbook-azure.md`
- `docs/eventstream-runbook-gcp.md`
- `docs/eventstream-runbook-oci.md`
- `docs/tenant-ownership-and-eventlock-service.md`
- `docs/function8-service-catalog.md`
- `docs/third-party-operations-and-exit.md`
- `docs/organization-as-code-positioning.md`
- `docs/fork-and-release-operating-model.md`
- `docs/release-sync-playbook.md`
- `docs/parallelbetrieb-version-binding.md`
- `docs/issue-taxonomie-pro-repo.md`
- `docs/einfuehrung-greenfield-brownfield.md`
- `docs/service-business-core-vertical-blueprint.md`
- `docs/vertical-starter-prozesskatalog.md`
- `docs/repo-refactor-plan-single-repo-modules.md`
- `docs/arbeitsmodell-agile-cadence.md`
- `docs/access-and-issue-operations.md`

## Sprache und Kultur

- Folge immer `policies/culture-policy.yaml`.
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

1. Lies `docs/vscode-copilot-start.md`.
2. Fuehre `python scripts/startup_check.py --ide vscode --run-tests` aus.
3. Waehle das passende Branchen-Onboarding unter `prompts/onboarding/`.
   Bevorzugte Defaults: `software-company-first-setup.md`, `notary-first-setup.md`, `wealth-management-first-setup.md`.
   Zusaetzlicher MVP-Pfad: `property-management-first-setup.md`.
4. Beginne mit einem Pilotprozess statt Vollausrollung.
5. Nutze fuer Fork-Betrieb, Sync und Mischbetrieb die neuen Betriebsdokumente in `docs/`.
