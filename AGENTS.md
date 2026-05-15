# AGENTS.md

Dieses Repository ist ein Muster fuer `Notariat as Code` mit `NoC` als konkreter Betriebsauspraegung.

## Prioritaet der Vorgaben

1. Gesetzliche und regulatorische Pflichten
2. Verbindliche Prozess- und Governance-Regeln
3. Unternehmensspezifische Branchenregeln
4. Kultur- und Sprachregeln

## Arbeitsprinzip

- Das LLM ist Eingabeoberflaeche, nicht die fachliche Wahrheit.
- Das Zielmodell ist `Notariat as Code`, der operative Aenderungsfluss ist `Enterprise GitOps`.
- Fachliche Wahrheit entsteht durch versionierte Aenderung + Review + Freigabe.
- Sensible Schritte brauchen Vier-Augen-Freigabe.
- Prozessaenderungen werden immer mit Begruendung dokumentiert.
- Ein Update gilt erst als abgeschlossen, wenn die Aenderung validiert, committed, zu GitHub gepusht und in den Zielbranch gemerged wurde.
- Wenn gefragt wird, ob die Arbeit fertig ist, darf `fertig` nur gemeldet werden, wenn der gepruefte Stand in `main` gemerged ist und der lokale Workspace auf dem aktuellen `main` sauber ist.
- Jeder Push muss [roadmap/GANTT.md](roadmap/GANTT.md) aktualisieren; Aenderungen unter [plugins/](plugins), [workflows/](workflows) oder [usecases/](usecases) muessen zusaetzlich das jeweilige Themen-Gantt aktualisieren.
- Das Repo trennt installierbare Plugin-Artefakte in [plugins/](plugins), ausfuehrbare Notariats-Workflows in [workflows/](workflows) und konkrete notarielle Usecases in [usecases/](usecases).
- Knowledge-Graph-Artefakte liegen usecase-lokal als `knowledge-graph.graph.json` und `knowledge-graph.md`; ein zentraler `knowledge-graph/` Ordner ist nicht zulaessig.
- Konzeptaenderungen werden IDE-uebergreifend synchron gepflegt (Cursor und VS Code + Copilot).
- Onboarding wird nie nur fuer eine Plattform gepflegt, sondern fuer alle unterstuetzten Plattformen.
- README-, START_HERE-, Index- und Agentenregel-Dateien muessen interne Repo-Verweise als klickbare Markdown-Links fuehren; reine Code-Formatierung ist fuer Befehle, Konfigurationsschluessel, Dateimuster und Code-Identifier reserviert.
- Der verbindliche Technikstack steht in [policies/technology-policy.yaml](policies/technology-policy.yaml).
- Keine realen Secrets oder personenbezogenen Daten im Repository speichern ([policies/data-protection-policy.yaml](policies/data-protection-policy.yaml)).
- Bei SaaS-Verarbeitung mit personenbezogenen Daten ist ein AVV verpflichtend ([docs/de/avv-checkliste-eventlock-saas.md](docs/de/avv-checkliste-eventlock-saas.md)).
- SBOM-Vorgaben sind verbindlich nach [policies/sbom-policy.yaml](policies/sbom-policy.yaml).
- AI-SBOM gilt repo-weit fuer AI-faehige Plugins, Workflows, Usecases, Prompts und externe Modellaufrufe; Mindestcluster und Artefakte stehen in [docs/de/sbom-for-ai.md](docs/de/sbom-for-ai.md) und [docs/en/sbom-for-ai.md](docs/en/sbom-for-ai.md).
- Mindestvoraussetzungen fuer Base-Workspace, Plugin-Entwicklung und lokalen Notariatsarbeitsplatz stehen in [docs/de/minimum-requirements.md](docs/de/minimum-requirements.md) und [docs/en/minimum-requirements.md](docs/en/minimum-requirements.md) und muessen in der SBOM/AI-SBOM gespiegelt werden.
- Rollen und Qualifikationsgrenzen sind verbindlich nach [policies/role-model-policy.yaml](policies/role-model-policy.yaml).
- Rollen-, Rechte- und Issue-Sichtbarkeitsvorgaben sind verbindlich nach [policies/access-control-policy.yaml](policies/access-control-policy.yaml).
- Revisionssichere Ereignisablage ist verbindlich nach [policies/revisionssicherheit-eventstream-policy.yaml](policies/revisionssicherheit-eventstream-policy.yaml).
- Technische Umsetzungsvarianten stehen in [docs/de/eventstream/implementation-templates.md](docs/de/eventstream/implementation-templates.md).
- Cloud-Runbooks sind fuer AWS, Azure, GCP und OCI gleichwertig zu pflegen.
- Tenant-Ownership und Provider/Kunden-Grenzen sind verbindlich nach [policies/tenant-ownership-policy.yaml](policies/tenant-ownership-policy.yaml).
- Function8-Leistungen mit AVV-Relevanz muessen transparent im Repo dokumentiert und ersetzbar sein ([policies/provider-open-services-policy.yaml](policies/provider-open-services-policy.yaml)).
- GitHub-Identitaeten und Rollenbindung sind verbindlich nach [policies/github-identity-registry.json](policies/github-identity-registry.json).
- Aenderungen an AI-Regelflaechen erfolgen nur als Spiegel von Policy-Aenderungen unter [policies/](policies).
- Unternehmensbetrieb mit zentralem Upstream erfolgt nach [docs/de/operations/fork-and-release-operating-model.md](docs/de/operations/fork-and-release-operating-model.md).
- Upstream-Uebernahmen erfolgen nach [docs/de/operations/release-sync-playbook.md](docs/de/operations/release-sync-playbook.md).
- Mischbetrieb alt/neu erfolgt mit Version-Binding nach [docs/de/operations/parallelbetrieb-version-binding.md](docs/de/operations/parallelbetrieb-version-binding.md).
- Core/Vertical-Struktur fuer Dienstleister erfolgt nach [docs/de/service-model/core-vertical-blueprint.md](docs/de/service-model/core-vertical-blueprint.md).
- Starter-Prozesse je Vertical stehen in [docs/de/service-model/vertical-starter-process-catalog.md](docs/de/service-model/vertical-starter-process-catalog.md).
- Arbeitsmethode und Team-Cadence werden nach [docs/de/operations/agile-cadence.md](docs/de/operations/agile-cadence.md) dokumentiert.
- Rollen-/Rechtebetrieb und Issue-Sichtbarkeit stehen in [docs/de/issues/operations.md](docs/de/issues/operations.md).
- Plugin- und Connector-Plaene werden unter [docs/de/plugin-plans/](docs/de/plugin-plans) und [docs/en/plugin-plans/](docs/en/plugin-plans) gepflegt.
- NoC-Ausfuehrung erfolgt lokal im genehmigten Workspace; Omnistation ist fuer NoC kein Ausfuehrungsort. Kartenleser-, morris- und XNP-Pfade werden ueber das lokale Profil `notary-workstation` geprueft.
- Mehrsprachigkeit ist verbindlich nach [policies/language-policy.yaml](policies/language-policy.yaml).
- Sprachabhaengige Inhalte werden in ISO-639-Sprachordnern gepflegt, mindestens `de` und `en`.
- Unabhaengig von der Sprache des Prompts muessen Aenderungen an lokalisierten Inhalten immer alle Standardsprachen pflegen.
- Fuer deutsches Recht und notarielle Usecases ist Deutsch die fuehrende und rechtlich bindende Sprache; Englisch ist nur Uebersetzung oder Orientierung. Usecase-Indizes und fachliche Usecase-Inhalte werden deshalb deutsch gefuehrt, waehrend stabile technische Identifier englisch bleiben duerfen.

## Erststart fuer neue Nutzer

1. [docs/de/START_HERE.md](docs/de/START_HERE.md) oder [docs/en/START_HERE.md](docs/en/START_HERE.md) lesen.
2. [docs/de/minimum-requirements.md](docs/de/minimum-requirements.md) oder [docs/en/minimum-requirements.md](docs/en/minimum-requirements.md) lesen.
3. [policies/culture-policy.yaml](policies/culture-policy.yaml), [policies/process-policy.yaml](policies/process-policy.yaml), [policies/technology-policy.yaml](policies/technology-policy.yaml), [policies/data-protection-policy.yaml](policies/data-protection-policy.yaml), [policies/role-model-policy.yaml](policies/role-model-policy.yaml) und [policies/language-policy.yaml](policies/language-policy.yaml) bestaetigen.
4. `python scripts/startup_check.py --profile base --ide auto --run-tests` erfolgreich ausfuehren.
   Fuer Plugin-Arbeit zusaetzlich `python scripts/startup_check.py --profile plugin-dev --ide auto`.
   Fuer Kartenleser-, morris- oder XNP-nahe Arbeit zusaetzlich `python scripts/startup_check.py --profile notary-workstation --ide auto`.
5. Passendes Onboarding-Prompt unter [prompts/de/onboarding/](prompts/de/onboarding) oder [prompts/en/onboarding/](prompts/en/onboarding) starten.
   Standard-MVP-Set im Referenzrepo: `software_company`, `notary`, `wealth_management`.
   Zusaetzlicher MVP-Use-Case: `property_management`.
6. Erst danach mit produktiven Prozessaenderungen beginnen.
7. Fuer Greenfield/Brownfield den Pfad aus [docs/de/einfuehrung-greenfield-brownfield.md](docs/de/einfuehrung-greenfield-brownfield.md) oder [docs/en/einfuehrung-greenfield-brownfield.md](docs/en/einfuehrung-greenfield-brownfield.md) waehlen.

## Plattform-Synchronitaet

- Bei Regel- oder Konzeptaenderungen immer beide Pfade aktualisieren:
  - Cursor: [.cursor/rules/](.cursor/rules)
  - VS Code + Copilot: [.github/copilot-instructions.md](.github/copilot-instructions.md), [docs/de/vscode-copilot-start.md](docs/de/vscode-copilot-start.md) und [docs/en/vscode-copilot-start.md](docs/en/vscode-copilot-start.md)
- Bei sprachabhaengigen Aenderungen immer alle Standardsprachen nach [policies/language-policy.yaml](policies/language-policy.yaml) aktualisieren.
