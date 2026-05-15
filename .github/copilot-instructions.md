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
- Wenn nach `fertig` gefragt wird, ist nur ein in `main` gemergter, gepruefter und lokal sauberer Stand fertig.
- Jeder Push muss [roadmap/GANTT.md](../roadmap/GANTT.md) aktualisieren; Aenderungen unter [plugins/](../plugins), [workflows/](../workflows) oder [usecases/](../usecases) muessen zusaetzlich das jeweilige Themen-Gantt aktualisieren.
- Trenne installierbare Plugin-Artefakte ([plugins/](../plugins)), ausfuehrbare Notariats-Workflows ([workflows/](../workflows)) und konkrete notarielle Usecases ([usecases/](../usecases)).
- Knowledge-Graph-Artefakte liegen usecase-lokal als `knowledge-graph.graph.json` und `knowledge-graph.md`; ein zentraler `knowledge-graph/` Ordner ist nicht zulaessig.
- Konzept- und Regelupdates muessen plattformuebergreifend synchronisiert werden (Cursor und VS Code + Copilot).
- Onboarding-Updates muessen fuer alle unterstuetzten Plattformen parallel gepflegt werden.
- README-, START_HERE-, Index- und Agentenregel-Dateien muessen interne Repo-Verweise als klickbare Markdown-Links fuehren; Code-Formatierung ist fuer Befehle, Konfigurationsschluessel, Dateimuster und Code-Identifier reserviert.
- Access- und Rollenregeln sind nur unter [policies/](../policies) zu aendern; AI-Regelflaechen sind Spiegel dieser Policy.
- Mehrsprachigkeit ist repo-weit verbindlich nach [policies/language-policy.yaml](../policies/language-policy.yaml); die Policy gilt fuer alle menschlich lesbaren Inhalte, inklusive GitHub-Root-[README.md](../README.md).
- Sprachabhaengige Inhalte liegen in ISO-639-Ordnern; `de` und `en` sind immer zu pflegen.
- Die Sprache des Prompts begrenzt die Aenderung nicht: bei lokalisierten Inhalten immer alle Standardsprachen aktualisieren.
- Fuer deutsches Recht und notarielle Usecases ist Deutsch die fuehrende und rechtlich bindende Sprache; Englisch ist nur Uebersetzung oder Orientierung. Usecase-Indizes und fachliche Usecase-Inhalte werden deutsch gefuehrt.
- Standard-MVP-Module im Referenzrepo sind synchron: `software_company`, `notary`, `wealth_management`.
- Zusaetzlicher MVP-Use-Case: `property_management`.
- Plugin- und Connector-Plaene liegen unter [docs/de/plugin-plans/](../docs/de/plugin-plans) und
  [docs/en/plugin-plans/](../docs/en/plugin-plans).
- Mindestvoraussetzungen fuer Base-Workspace, Plugin-Entwicklung und lokalen Notariatsarbeitsplatz stehen in [docs/de/minimum-requirements.md](../docs/de/minimum-requirements.md) und [docs/en/minimum-requirements.md](../docs/en/minimum-requirements.md).
- NoC-Ausfuehrung und Plugin-Regeneration erfolgen lokal im genehmigten Workspace, nicht ueber Omnistation.

## Pflichtquellen im Repository

- [docs/de/START_HERE.md](../docs/de/START_HERE.md)
- [docs/en/START_HERE.md](../docs/en/START_HERE.md)
- [docs/de/fachanwender-guide.md](../docs/de/fachanwender-guide.md)
- [docs/en/fachanwender-guide.md](../docs/en/fachanwender-guide.md)
- [policies/culture-policy.yaml](../policies/culture-policy.yaml)
- [policies/process-policy.yaml](../policies/process-policy.yaml)
- [policies/technology-policy.yaml](../policies/technology-policy.yaml)
- [policies/data-protection-policy.yaml](../policies/data-protection-policy.yaml)
- [policies/language-policy.yaml](../policies/language-policy.yaml)
- [docs/de/avv-checkliste-eventlock-saas.md](../docs/de/avv-checkliste-eventlock-saas.md)
- [policies/sbom-policy.yaml](../policies/sbom-policy.yaml)
- [docs/de/sbom-for-ai.md](../docs/de/sbom-for-ai.md)
- [docs/en/sbom-for-ai.md](../docs/en/sbom-for-ai.md)
- [docs/de/minimum-requirements.md](../docs/de/minimum-requirements.md)
- [docs/en/minimum-requirements.md](../docs/en/minimum-requirements.md)
- [policies/role-model-policy.yaml](../policies/role-model-policy.yaml)
- [policies/access-control-policy.yaml](../policies/access-control-policy.yaml)
- [policies/revisionssicherheit-eventstream-policy.yaml](../policies/revisionssicherheit-eventstream-policy.yaml)
- [policies/tenant-ownership-policy.yaml](../policies/tenant-ownership-policy.yaml)
- [policies/provider-open-services-policy.yaml](../policies/provider-open-services-policy.yaml)
- [policies/github-identity-registry.json](../policies/github-identity-registry.json)
- [docs/de/governance.md](../docs/de/governance.md)
- [docs/de/eventstream/implementation-templates.md](../docs/de/eventstream/implementation-templates.md)
- [docs/de/eventstream/runbook-aws.md](../docs/de/eventstream/runbook-aws.md)
- [docs/de/eventstream/runbook-azure.md](../docs/de/eventstream/runbook-azure.md)
- [docs/de/eventstream/runbook-gcp.md](../docs/de/eventstream/runbook-gcp.md)
- [docs/de/eventstream/runbook-oci.md](../docs/de/eventstream/runbook-oci.md)
- [docs/de/service-model/tenant-ownership-and-eventlock-service.md](../docs/de/service-model/tenant-ownership-and-eventlock-service.md)
- [docs/de/service-model/function8-service-catalog.md](../docs/de/service-model/function8-service-catalog.md)
- [docs/de/service-model/third-party-operations-and-exit.md](../docs/de/service-model/third-party-operations-and-exit.md)
- [docs/de/organization-as-code-positioning.md](../docs/de/organization-as-code-positioning.md)
- [docs/de/operations/fork-and-release-operating-model.md](../docs/de/operations/fork-and-release-operating-model.md)
- [docs/de/operations/release-sync-playbook.md](../docs/de/operations/release-sync-playbook.md)
- [docs/de/operations/parallelbetrieb-version-binding.md](../docs/de/operations/parallelbetrieb-version-binding.md)
- [docs/de/issues/taxonomy.md](../docs/de/issues/taxonomy.md)
- [docs/de/einfuehrung-greenfield-brownfield.md](../docs/de/einfuehrung-greenfield-brownfield.md)
- [docs/de/service-model/core-vertical-blueprint.md](../docs/de/service-model/core-vertical-blueprint.md)
- [docs/de/service-model/vertical-starter-process-catalog.md](../docs/de/service-model/vertical-starter-process-catalog.md)
- [docs/de/operations/single-repo-refactor-plan.md](../docs/de/operations/single-repo-refactor-plan.md)
- [docs/de/plugin-plans/README.md](../docs/de/plugin-plans/README.md)
- [docs/de/operations/agile-cadence.md](../docs/de/operations/agile-cadence.md)
- [docs/de/issues/operations.md](../docs/de/issues/operations.md)

## Sprache und Kultur

- Folge immer [policies/culture-policy.yaml](../policies/culture-policy.yaml).
- Folge immer [policies/language-policy.yaml](../policies/language-policy.yaml).
- Lokal gepflegte Inhalte muessen immer in `de` und `en` aktualisiert werden.
- Bei Genderfragen gilt die konfigurierte Policy.
- Wenn keine Policy gesetzt ist, nutze neutrale Sprache und bitte einmal um Entscheidung.

## Datenschutz und Sicherheit

- Keine echten Zugangsdaten, Keys oder Tokens in Vorschlaegen speichern.
- Keine echten personenbezogenen Daten in Prozessbeispielen speichern.
- Fuer Beispieldaten nur Testdomains und Platzhalter verwenden.
- AI-SBOM gilt repo-weit fuer AI-faehige Plugins, Workflows, Usecases, Prompts und externe Modellaufrufe; lokale Runtime-, Hardware- und Middleware-Mindestvoraussetzungen muessen in der AI-SBOM gefuehrt werden; keine Mandatsinhalte, Secrets oder personenbezogenen Daten in AI-SBOM-Artefakten speichern.

## Technikvorgaben

- Folge [policies/technology-policy.yaml](../policies/technology-policy.yaml) als verbindlichem Stack.
- Markdown ist die einzige manuell gepflegte Doku-Quelle.
- BPMN-2.0 ist die fachliche Quellnotation fuer Prozesse.
- Mermaid darf nur als Uebersicht eingesetzt werden.

## Erststart fuer VS Code + Copilot

1. Lies [docs/de/vscode-copilot-start.md](../docs/de/vscode-copilot-start.md) oder [docs/en/vscode-copilot-start.md](../docs/en/vscode-copilot-start.md).
2. Fuehre `python scripts/startup_check.py --profile base --ide vscode --run-tests` aus.
   Fuer Plugin-Entwicklung zusaetzlich `python scripts/startup_check.py --profile plugin-dev --ide vscode`.
   Fuer Kartenleser-, morris- oder XNP-nahe Arbeit zusaetzlich `python scripts/startup_check.py --profile notary-workstation --ide vscode`.
3. Waehle das passende Branchen-Onboarding unter [prompts/de/onboarding/](../prompts/de/onboarding) oder [prompts/en/onboarding/](../prompts/en/onboarding).
   Bevorzugte Defaults: `software-company-first-setup.md`, `notary-first-setup.md`, `wealth-management-first-setup.md`.
   Zusaetzlicher MVP-Pfad: `property-management-first-setup.md`.
4. Beginne mit einem Pilotprozess statt Vollausrollung.
5. Nutze fuer Fork-Betrieb, Sync und Mischbetrieb die neuen Betriebsdokumente in [docs/de/](../docs/de) und [docs/en/](../docs/en).
