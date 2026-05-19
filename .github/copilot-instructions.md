# GitHub Copilot Instructions

Dieses Repository ist ein Muster für `Notariat as Code` mit `NaC` als konkreter Betriebsausprägung.

## Verbindliche Priorität

1. Compliance und rechtliche Pflichten
2. Prozessgovernance (Review, Freigaben, Nachvollziehbarkeit)
3. Branchenmodule
4. Kultur- und Sprachvorgaben

## Arbeitsweise

- Behandle das LLM als Assistent für Eingaben, nicht als finale fachliche Autorität.
- Rahmen: `Notariat as Code` + `Enterprise GitOps`; `NaC` ist die konkrete Umsetzung.
- Schlage keine direkten Änderungen an `main` vor.
- Erzwinge Vorschläge über Branch + Pull Request + Review.
- Sensible Prozessschritte (z. B. Steuer, Zahlungsfreigaben) brauchen Vier-Augen-Prinzip.
- Jede Prozessänderung muss begründet und versioniert sein.
- Ein Update gilt erst als abgeschlossen, wenn die Änderung validiert, committed, zu GitHub gepusht und in den Zielbranch gemerged wurde.
- Wenn nach `fertig` gefragt wird, ist nur ein in `main` gemergter, geprüfter und lokal sauberer Stand fertig.
- Jeder Push muss [roadmap/GANTT.md](../roadmap/GANTT.md) aktualisieren; Änderungen unter [plugins/](../plugins), [workflows/](../workflows) oder [usecases/](../usecases) müssen zusätzlich das jeweilige Themen-Gantt aktualisieren.
- Lizenzmodell ist verbindlich nach [policies/license-policy.yaml](../policies/license-policy.yaml): Code, Plugins, Workflows, Validatoren, Schemas und ausführbare Beispiele stehen unter `AGPL-3.0-or-later`; Dokumentation, Policies, Roadmap, Prompts und fachliche Usecases stehen unter `CC-BY-4.0`.
- Attribution nach [NOTICE](../NOTICE), [AUTHORS.md](../AUTHORS.md) und [CITATION.cff](../CITATION.cff) sichtbar erhalten; Marken- und Namensgrenzen nach [TRADEMARK.md](../TRADEMARK.md) beachten.
- Trenne installierbare Plugin-Artefakte ([plugins/](../plugins)), ausführbare Notariats-Workflows ([workflows/](../workflows)) und konkrete notarielle Usecases ([usecases/](../usecases)).
- Knowledge-Graph-Artefakte liegen usecase-lokal als `knowledge-graph.graph.json` und `knowledge-graph.md`; ein zentraler `knowledge-graph/` Ordner ist nicht zulässig.
- Konzept- und Regelupdates müssen plattformübergreifend synchronisiert werden (Cursor und VS Code + Copilot).
- Onboarding-Updates müssen für alle unterstützten Plattformen parallel gepflegt werden.
- README-, START_HERE-, Index- und Agentenregel-Dateien müssen interne Repo-Verweise als klickbare Markdown-Links führen; Code-Formatierung ist für Befehle, Konfigurationsschlüssel, Dateimuster und Code-Identifier reserviert.
- Access- und Rollenregeln sind nur unter [policies/](../policies) zu ändern; AI-Regelflächen sind Spiegel dieser Policy.
- Neue NaC-Funktionalität braucht eine Bedienkante in der zentralen `nac`-CLI; direkte Skripte dürfen als interne Kompatibilität bleiben, aber Produktdokumentation führt über [docs/de/cli.md](../docs/de/cli.md) und [docs/en/cli.md](../docs/en/cli.md).
- Mehrsprachigkeit ist repo-weit verbindlich nach [policies/language-policy.yaml](../policies/language-policy.yaml); die Policy gilt für alle menschlich lesbaren Inhalte, inklusive GitHub-Root-[README.md](../README.md).
- Sprachabhängige Inhalte liegen in ISO-639-Ordnern; `de` und `en` sind immer zu pflegen.
- Die Sprache des Prompts begrenzt die Änderung nicht: bei lokalisierten Inhalten immer alle Standardsprachen aktualisieren.
- Lokalisierte Markdown-Links bleiben im Sprachpfad der Quelldatei: deutsche Inhalte verlinken deutsch, englische Inhalte verlinken englisch.
- Für deutsches Recht und notarielle Usecases ist Deutsch die führende und rechtlich bindende Sprache; Englisch ist nur Übersetzung oder Orientierung. Usecase-Indizes und fachliche Usecase-Inhalte werden deutsch geführt.
- Plugin-Anzeigenamen, Plugin-Beschreibungen, Plugin-README-Überschriften, Marketplace-Kategorien, Starter-Prompts und Skill-Frontmatter-Beschreibungen werden deutsch geführt. Skill-Namen, Ordner, Commands, IDs, Akronyme, Produktnamen und technische Output-Labels dürfen englisch/ASCII bleiben. Jeder Skill braucht im Body eine kurze englische Summary.
- Deutsche menschlich lesbare Inhalte nutzen echte Umlaute und ß; ASCII-Umschreibungen bleiben nur für technische Identifier, Pfade, URLs, Commands und Code zulässig.
- Plugin-Karten müssen kurze lesbare Anzeigenamen, knappe Kurzbeschreibungen und echte Icon-/Logo-Assets haben; leere Platzhalterbilder sind nicht zulässig.
- Standard-MVP-Module im Referenzrepo sind synchron: `software_company`, `notary`, `wealth_management`.
- Zusätzlicher MVP-Use-Case: `property_management`.
- Plugin- und Connector-Pläne liegen unter [docs/de/plugin-plans/](../docs/de/plugin-plans) und
  [docs/en/plugin-plans/](../docs/en/plugin-plans).
- Mindestvoraussetzungen für Base-Workspace, Plugin-Entwicklung und lokalen Notariatsarbeitsplatz stehen in [docs/de/minimum-requirements.md](../docs/de/minimum-requirements.md) und [docs/en/minimum-requirements.md](../docs/en/minimum-requirements.md).
- NaC-Ausführung und Plugin-Regeneration erfolgen lokal im genehmigten Workspace, nicht über Omnistation.
- Repo-lokale Plugins werden für neue Rechner mit `python scripts/nac.py plugins install --mode link`
  in die lokale Codex-Discovery gespiegelt; danach Codex neu starten oder eine
  neue Session öffnen.

## Pflichtquellen im Repository

- [docs/de/START_HERE.md](../docs/de/START_HERE.md)
- [docs/en/START_HERE.md](../docs/en/START_HERE.md)
- [docs/de/fachanwender-guide.md](../docs/de/fachanwender-guide.md)
- [docs/en/fachanwender-guide.md](../docs/en/fachanwender-guide.md)
- [docs/de/cli.md](../docs/de/cli.md)
- [docs/en/cli.md](../docs/en/cli.md)
- [policies/culture-policy.yaml](../policies/culture-policy.yaml)
- [policies/process-policy.yaml](../policies/process-policy.yaml)
- [policies/technology-policy.yaml](../policies/technology-policy.yaml)
- [policies/data-protection-policy.yaml](../policies/data-protection-policy.yaml)
- [policies/language-policy.yaml](../policies/language-policy.yaml)
- [policies/license-policy.yaml](../policies/license-policy.yaml)
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
- [../docs/de/einfuehrung-greenfield-brownfield.md](../docs/de/einfuehrung-greenfield-brownfield.md)
- [docs/de/service-model/core-vertical-blueprint.md](../docs/de/service-model/core-vertical-blueprint.md)
- [docs/de/service-model/vertical-starter-process-catalog.md](../docs/de/service-model/vertical-starter-process-catalog.md)
- [docs/de/operations/single-repo-refactor-plan.md](../docs/de/operations/single-repo-refactor-plan.md)
- [docs/de/plugin-plans/README.md](../docs/de/plugin-plans/README.md)
- [docs/de/operations/agile-cadence.md](../docs/de/operations/agile-cadence.md)
- [docs/de/issues/operations.md](../docs/de/issues/operations.md)

## Sprache und Kultur

- Folge immer [policies/culture-policy.yaml](../policies/culture-policy.yaml).
- Folge immer [policies/language-policy.yaml](../policies/language-policy.yaml).
- Lokal gepflegte Inhalte müssen immer in `de` und `en` aktualisiert werden.
- Lokalisierte Markdown-Links dürfen nicht in den anderen Sprachpfad springen.
- Plugins und Skills: deutsche UX- und fachliche Anweisung führt; englische Summary dient nur technischer Orientierung.
- Bei Genderfragen gilt die konfigurierte Policy.
- Wenn keine Policy gesetzt ist, nutze neutrale Sprache und bitte einmal um Entscheidung.

## Datenschutz und Sicherheit

- Keine echten Zugangsdaten, Keys oder Tokens in Vorschlägen speichern.
- Keine echten personenbezogenen Daten in Prozessbeispielen speichern.
- Für Beispieldaten nur Testdomains und Platzhalter verwenden.
- AI-SBOM gilt repo-weit für AI-fähige Plugins, Workflows, Usecases, Prompts und externe Modellaufrufe; lokale Runtime-, Hardware- und Middleware-Mindestvoraussetzungen müssen in der AI-SBOM geführt werden; keine Mandatsinhalte, Secrets oder personenbezogenen Daten in AI-SBOM-Artefakten speichern.

## Technikvorgaben

- Folge [policies/technology-policy.yaml](../policies/technology-policy.yaml) als verbindlichem Stack.
- Markdown ist die einzige manuell gepflegte Doku-Quelle.
- BPMN-2.0 ist die fachliche Quellnotation für Prozesse.
- `bpmn-js` ist die geplante visuelle Bearbeitungsschicht für BPMN-Modelle.
- NaC-BPMN-Properties stehen in [bpmn/nac-moddle.json](../bpmn/nac-moddle.json);
  BPMN-Modelle müssen mit [scripts/validate_bpmn_models.py](../scripts/validate_bpmn_models.py)
  validierbar sein.
- Mermaid darf nur als Übersicht eingesetzt werden.

## Erststart für VS Code + Copilot

1. Lies [docs/de/vscode-copilot-start.md](../docs/de/vscode-copilot-start.md) oder [docs/en/vscode-copilot-start.md](../docs/en/vscode-copilot-start.md).
2. Führe `python scripts/startup_check.py --profile base --ide vscode --run-tests` aus.
   Für Plugin-Entwicklung zusätzlich `python scripts/nac.py plugins validate`,
   `python scripts/nac.py plugins install --mode link` und
   `python scripts/startup_check.py --profile plugin-dev --ide vscode`.
   Danach Codex neu starten oder eine neue Session öffnen.
   Für Kartenleser-, morris- oder XNP-nahe Arbeit zusätzlich `python scripts/startup_check.py --profile notary-workstation --ide vscode`.
3. Wähle das passende Branchen-Onboarding unter [prompts/de/onboarding/](../prompts/de/onboarding) oder [prompts/en/onboarding/](../prompts/en/onboarding).
   Bevorzugte Defaults: `software-company-first-setup.md`, `notary-first-setup.md`, `wealth-management-first-setup.md`.
   Zusätzlicher MVP-Pfad: `property-management-first-setup.md`.
4. Beginne mit einem Pilotprozess statt Vollausrollung.
5. Nutze für Fork-Betrieb, Sync und Mischbetrieb die neuen Betriebsdokumente in [docs/de/](../docs/de) und [docs/en/](../docs/en).
