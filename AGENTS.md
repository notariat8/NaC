# AGENTS.md

Dieses Repository ist ein Muster für `Notariat as Code` mit `NaC` als konkreter Betriebsausprägung.

## Priorität der Vorgaben

1. Gesetzliche und regulatorische Pflichten
2. Verbindliche Prozess- und Governance-Regeln
3. Unternehmensspezifische Branchenregeln
4. Kultur- und Sprachregeln

## Arbeitsprinzip

- Das LLM ist Eingabeoberfläche, nicht die fachliche Wahrheit.
- Das Zielmodell ist `Notariat as Code`, der operative Änderungsfluss ist `Enterprise GitOps`.
- Fachliche Wahrheit entsteht durch versionierte Änderung + Review + Freigabe.
- Sensible Schritte brauchen Vier-Augen-Freigabe.
- Prozessänderungen werden immer mit Begründung dokumentiert.
- Ein Update gilt erst als abgeschlossen, wenn die Änderung validiert, committed, zu GitHub gepusht und in den Zielbranch gemerged wurde.
- Wenn gefragt wird, ob die Arbeit fertig ist, darf `fertig` nur gemeldet werden, wenn der geprüfte Stand in `main` gemerged ist und der lokale Workspace auf dem aktuellen `main` sauber ist.
- Jeder Push muss [roadmap/GANTT.md](roadmap/GANTT.md) aktualisieren; Änderungen unter [plugins/](plugins), [workflows/](workflows) oder [usecases/](usecases) müssen zusätzlich das jeweilige Themen-Gantt aktualisieren.
- Lizenzmodell ist verbindlich nach [policies/license-policy.yaml](policies/license-policy.yaml): Code, Plugins, Workflows, Validatoren, Schemas und ausführbare Beispiele stehen unter `AGPL-3.0-or-later`; Dokumentation, Policies, Roadmap, Prompts und fachliche Usecases stehen unter `CC-BY-4.0`.
- Attribution nach [NOTICE](NOTICE), [AUTHORS.md](AUTHORS.md) und [CITATION.cff](CITATION.cff) sichtbar erhalten; Marken- und Namensgrenzen nach [TRADEMARK.md](TRADEMARK.md) beachten.
- Das Repo trennt installierbare Plugin-Artefakte in [plugins/](plugins), ausführbare Notariats-Workflows in [workflows/](workflows) und konkrete notarielle Usecases in [usecases/](usecases).
- Knowledge-Graph-Artefakte liegen usecase-lokal als `knowledge-graph.graph.json` und `knowledge-graph.md`; ein zentraler `knowledge-graph/` Ordner ist nicht zulässig.
- Konzeptänderungen werden IDE-übergreifend synchron gepflegt (Cursor und VS Code + Copilot).
- Onboarding wird nie nur für eine Plattform gepflegt, sondern für alle unterstützten Plattformen.
- README-, START_HERE-, Index- und Agentenregel-Dateien müssen interne Repo-Verweise als klickbare Markdown-Links führen; reine Code-Formatierung ist für Befehle, Konfigurationsschlüssel, Dateimuster und Code-Identifier reserviert.
- Der verbindliche Technikstack steht in [policies/technology-policy.yaml](policies/technology-policy.yaml).
- Fachliche Prozessmodelle sind BPMN-2.0-first; `bpmn-js` ist die geplante visuelle Bearbeitungsschicht, NaC-BPMN-Properties stehen in [bpmn/nac-moddle.json](bpmn/nac-moddle.json), und BPMN-Modelle müssen mit [scripts/validate_bpmn_models.py](scripts/validate_bpmn_models.py) validierbar sein.
- Keine realen Secrets oder personenbezogenen Daten im Repository speichern ([policies/data-protection-policy.yaml](policies/data-protection-policy.yaml)).
- Bei SaaS-Verarbeitung mit personenbezogenen Daten ist ein AVV verpflichtend ([docs/de/avv-checkliste-eventlock-saas.md](docs/de/avv-checkliste-eventlock-saas.md)).
- SBOM-Vorgaben sind verbindlich nach [policies/sbom-policy.yaml](policies/sbom-policy.yaml).
- AI-SBOM gilt repo-weit für AI-fähige Plugins, Workflows, Usecases, Prompts und externe Modellaufrufe; Mindestcluster und Artefakte stehen in [docs/de/sbom-for-ai.md](docs/de/sbom-for-ai.md) und [docs/en/sbom-for-ai.md](docs/en/sbom-for-ai.md).
- Mindestvoraussetzungen für Base-Workspace, Plugin-Entwicklung und lokalen Notariatsarbeitsplatz stehen in [docs/de/minimum-requirements.md](docs/de/minimum-requirements.md) und [docs/en/minimum-requirements.md](docs/en/minimum-requirements.md) und müssen in der SBOM/AI-SBOM gespiegelt werden.
- Rollen und Qualifikationsgrenzen sind verbindlich nach [policies/role-model-policy.yaml](policies/role-model-policy.yaml).
- Rollen-, Rechte- und Issue-Sichtbarkeitsvorgaben sind verbindlich nach [policies/access-control-policy.yaml](policies/access-control-policy.yaml).
- Revisionssichere Ereignisablage ist verbindlich nach [policies/revisionssicherheit-eventstream-policy.yaml](policies/revisionssicherheit-eventstream-policy.yaml).
- Technische Umsetzungsvarianten stehen in [docs/de/eventstream/implementation-templates.md](docs/de/eventstream/implementation-templates.md).
- Cloud-Runbooks sind für AWS, Azure, GCP und OCI gleichwertig zu pflegen.
- Tenant-Ownership und Provider/Kunden-Grenzen sind verbindlich nach [policies/tenant-ownership-policy.yaml](policies/tenant-ownership-policy.yaml).
- Function8-Leistungen mit AVV-Relevanz müssen transparent im Repo dokumentiert und ersetzbar sein ([policies/provider-open-services-policy.yaml](policies/provider-open-services-policy.yaml)).
- GitHub-Identitäten und Rollenbindung sind verbindlich nach [policies/github-identity-registry.json](policies/github-identity-registry.json).
- Änderungen an AI-Regelflächen erfolgen nur als Spiegel von Policy-Änderungen unter [policies/](policies).
- Unternehmensbetrieb mit zentralem Upstream erfolgt nach [docs/de/operations/fork-and-release-operating-model.md](docs/de/operations/fork-and-release-operating-model.md).
- Upstream-Übernahmen erfolgen nach [docs/de/operations/release-sync-playbook.md](docs/de/operations/release-sync-playbook.md).
- Mischbetrieb alt/neu erfolgt mit Version-Binding nach [docs/de/operations/parallelbetrieb-version-binding.md](docs/de/operations/parallelbetrieb-version-binding.md).
- Core/Vertical-Struktur für Dienstleister erfolgt nach [docs/de/service-model/core-vertical-blueprint.md](docs/de/service-model/core-vertical-blueprint.md).
- Starter-Prozesse je Vertical stehen in [docs/de/service-model/vertical-starter-process-catalog.md](docs/de/service-model/vertical-starter-process-catalog.md).
- Arbeitsmethode und Team-Cadence werden nach [docs/de/operations/agile-cadence.md](docs/de/operations/agile-cadence.md) dokumentiert.
- Rollen-/Rechtebetrieb und Issue-Sichtbarkeit stehen in [docs/de/issues/operations.md](docs/de/issues/operations.md).
- Plugin- und Connector-Pläne werden unter [docs/de/plugin-plans/](docs/de/plugin-plans) und [docs/en/plugin-plans/](docs/en/plugin-plans) gepflegt.
- NaC-Ausführung erfolgt lokal im genehmigten Workspace; Omnistation ist für NaC kein Ausführungsort. Kartenleser-, morris- und XNP-Pfade werden über das lokale Profil `notary-workstation` geprüft.
- Mehrsprachigkeit ist repo-weit verbindlich nach [policies/language-policy.yaml](policies/language-policy.yaml); die Policy gilt für alle menschlich lesbaren Inhalte, inklusive GitHub-Root-[README.md](README.md).
- Sprachabhängige Inhalte werden in ISO-639-Sprachordnern gepflegt, mindestens `de` und `en`.
- Unabhängig von der Sprache des Prompts müssen Änderungen an lokalisierten Inhalten immer alle Standardsprachen pflegen.
- Für deutsches Recht und notarielle Usecases ist Deutsch die führende und rechtlich bindende Sprache; Englisch ist nur Übersetzung oder Orientierung. Usecase-Indizes, fachliche Usecase-Inhalte, Plugin-Anzeigenamen, Plugin-Beschreibungen, Plugin-README-Überschriften, Marketplace-Kategorien, Starter-Prompts und Skill-Frontmatter-Beschreibungen werden deshalb deutsch geführt, während stabile technische Identifier englisch bleiben dürfen.
- Deutsche menschlich lesbare Inhalte nutzen echte Umlaute und ß; ASCII-Umschreibungen bleiben nur für technische Identifier, Pfade, URLs, Commands und Code zulässig.
- Plugin-Karten müssen kurze lesbare Anzeigenamen, knappe Kurzbeschreibungen und echte Icon-/Logo-Assets haben; leere Platzhalterbilder sind nicht zulässig.

## Erststart für neue Nutzer

1. [docs/de/START_HERE.md](docs/de/START_HERE.md) oder [docs/en/START_HERE.md](docs/en/START_HERE.md) lesen.
2. [docs/de/minimum-requirements.md](docs/de/minimum-requirements.md) oder [docs/en/minimum-requirements.md](docs/en/minimum-requirements.md) lesen.
3. [policies/culture-policy.yaml](policies/culture-policy.yaml), [policies/process-policy.yaml](policies/process-policy.yaml), [policies/technology-policy.yaml](policies/technology-policy.yaml), [policies/data-protection-policy.yaml](policies/data-protection-policy.yaml), [policies/role-model-policy.yaml](policies/role-model-policy.yaml), [policies/language-policy.yaml](policies/language-policy.yaml) und [policies/license-policy.yaml](policies/license-policy.yaml) bestätigen.
4. `python scripts/startup_check.py --profile base --ide auto --run-tests` erfolgreich ausführen.
   Für Plugin-Arbeit zusätzlich `python scripts/validate_plugins.py`,
   `python scripts/install_local_plugins.py --mode link` und
   `python scripts/startup_check.py --profile plugin-dev --ide auto`.
   Danach Codex neu starten oder eine neue Session öffnen, weil Plugins beim
   Session-Start geladen werden.
   Für Kartenleser-, morris- oder XNP-nahe Arbeit zusätzlich `python scripts/startup_check.py --profile notary-workstation --ide auto`.
5. Passendes Onboarding-Prompt unter [prompts/de/onboarding/](prompts/de/onboarding) oder [prompts/en/onboarding/](prompts/en/onboarding) starten.
   Standard-MVP-Set im Referenzrepo: `software_company`, `notary`, `wealth_management`.
   Zusätzlicher MVP-Use-Case: `property_management`.
6. Erst danach mit produktiven Prozessänderungen beginnen.
7. Für Greenfield/Brownfield den Pfad aus [docs/de/einfuehrung-greenfield-brownfield.md](docs/de/einfuehrung-greenfield-brownfield.md) oder [docs/en/einfuehrung-greenfield-brownfield.md](docs/en/einfuehrung-greenfield-brownfield.md) wählen.

## Plattform-Synchronität

- Bei Regel- oder Konzeptänderungen immer beide Pfade aktualisieren:
  - Cursor: [.cursor/rules/](.cursor/rules)
  - VS Code + Copilot: [.github/copilot-instructions.md](.github/copilot-instructions.md), [docs/de/vscode-copilot-start.md](docs/de/vscode-copilot-start.md) und [docs/en/vscode-copilot-start.md](docs/en/vscode-copilot-start.md)
- Bei sprachabhängigen Änderungen immer alle Standardsprachen nach [policies/language-policy.yaml](policies/language-policy.yaml) aktualisieren.
