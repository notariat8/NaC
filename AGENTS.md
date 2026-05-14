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
- Jeder Push muss `roadmap/GANTT.md` aktualisieren; Aenderungen unter `plugins/`, `workflows/` oder `usecases/` muessen zusaetzlich das jeweilige Themen-Gantt aktualisieren.
- Das Repo trennt installierbare Plugin-Artefakte in `plugins/`, ausfuehrbare Notariats-Workflows in `workflows/` und konkrete notarielle Usecases in `usecases/`.
- Konzeptaenderungen werden IDE-uebergreifend synchron gepflegt (Cursor und VS Code + Copilot).
- Onboarding wird nie nur fuer eine Plattform gepflegt, sondern fuer alle unterstuetzten Plattformen.
- Der verbindliche Technikstack steht in `policies/technology-policy.yaml`.
- Keine realen Secrets oder personenbezogenen Daten im Repository speichern (`policies/data-protection-policy.yaml`).
- Bei SaaS-Verarbeitung mit personenbezogenen Daten ist ein AVV verpflichtend (`docs/de/avv-checkliste-eventlock-saas.md`).
- SBOM-Vorgaben sind verbindlich nach `policies/sbom-policy.yaml`.
- Rollen und Qualifikationsgrenzen sind verbindlich nach `policies/role-model-policy.yaml`.
- Rollen-, Rechte- und Issue-Sichtbarkeitsvorgaben sind verbindlich nach `policies/access-control-policy.yaml`.
- Revisionssichere Ereignisablage ist verbindlich nach `policies/revisionssicherheit-eventstream-policy.yaml`.
- Technische Umsetzungsvarianten stehen in `docs/de/eventstream-implementation-templates.md`.
- Cloud-Runbooks sind fuer AWS, Azure, GCP und OCI gleichwertig zu pflegen.
- Tenant-Ownership und Provider/Kunden-Grenzen sind verbindlich nach `policies/tenant-ownership-policy.yaml`.
- Function8-Leistungen mit AVV-Relevanz muessen transparent im Repo dokumentiert und ersetzbar sein (`policies/provider-open-services-policy.yaml`).
- GitHub-Identitaeten und Rollenbindung sind verbindlich nach `policies/github-identity-registry.json`.
- Aenderungen an AI-Regelflaechen erfolgen nur als Spiegel von Policy-Aenderungen unter `policies/`.
- Unternehmensbetrieb mit zentralem Upstream erfolgt nach `docs/de/fork-and-release-operating-model.md`.
- Upstream-Uebernahmen erfolgen nach `docs/de/release-sync-playbook.md`.
- Mischbetrieb alt/neu erfolgt mit Version-Binding nach `docs/de/parallelbetrieb-version-binding.md`.
- Core/Vertical-Struktur fuer Dienstleister erfolgt nach `docs/de/service-business-core-vertical-blueprint.md`.
- Starter-Prozesse je Vertical stehen in `docs/de/vertical-starter-prozesskatalog.md`.
- Arbeitsmethode und Team-Cadence werden nach `docs/de/arbeitsmodell-agile-cadence.md` dokumentiert.
- Rollen-/Rechtebetrieb und Issue-Sichtbarkeit stehen in `docs/de/access-and-issue-operations.md`.
- Plugin- und Connector-Plaene werden unter `docs/de/plugin-plans/` und `docs/en/plugin-plans/` gepflegt.
- NoC-Ausfuehrung erfolgt lokal im Workspace `~/NoC`; Omnistation ist fuer NoC kein Ausfuehrungsort.
- Mehrsprachigkeit ist verbindlich nach `policies/language-policy.yaml`.
- Sprachabhaengige Inhalte werden in ISO-639-Sprachordnern gepflegt, mindestens `de` und `en`.
- Unabhaengig von der Sprache des Prompts muessen Aenderungen an lokalisierten Inhalten immer alle Standardsprachen pflegen.

## Erststart fuer neue Nutzer

1. `docs/de/START_HERE.md` oder `docs/en/START_HERE.md` lesen.
2. `policies/culture-policy.yaml`, `policies/process-policy.yaml`, `policies/technology-policy.yaml`, `policies/data-protection-policy.yaml`, `policies/role-model-policy.yaml` und `policies/language-policy.yaml` bestaetigen.
3. `python scripts/startup_check.py --ide auto --run-tests` erfolgreich ausfuehren.
4. Passendes Onboarding-Prompt unter `prompts/de/onboarding/` oder `prompts/en/onboarding/` starten.
   Standard-MVP-Set im Referenzrepo: `software_company`, `notary`, `wealth_management`.
   Zusaetzlicher MVP-Use-Case: `property_management`.
5. Erst danach mit produktiven Prozessaenderungen beginnen.
6. Fuer Greenfield/Brownfield den Pfad aus `docs/de/einfuehrung-greenfield-brownfield.md` oder `docs/en/einfuehrung-greenfield-brownfield.md` waehlen.

## Plattform-Synchronitaet

- Bei Regel- oder Konzeptaenderungen immer beide Pfade aktualisieren:
  - Cursor: `.cursor/rules/`
  - VS Code + Copilot: `.github/copilot-instructions.md`, `docs/de/vscode-copilot-start.md` und `docs/en/vscode-copilot-start.md`
- Bei sprachabhaengigen Aenderungen immer alle Standardsprachen nach `policies/language-policy.yaml` aktualisieren.
