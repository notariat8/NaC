# AGENTS.md

Dieses Repository ist ein Muster fuer `Organization as Code` mit `OaC8` als konkreter Betriebsauspraegung.

## Prioritaet der Vorgaben

1. Gesetzliche und regulatorische Pflichten
2. Verbindliche Prozess- und Governance-Regeln
3. Unternehmensspezifische Branchenregeln
4. Kultur- und Sprachregeln

## Arbeitsprinzip

- Das LLM ist Eingabeoberflaeche, nicht die fachliche Wahrheit.
- Das Zielmodell ist `Organization as Code`, der operative Aenderungsfluss ist `Enterprise GitOps`.
- Fachliche Wahrheit entsteht durch versionierte Aenderung + Review + Freigabe.
- Sensible Schritte brauchen Vier-Augen-Freigabe.
- Prozessaenderungen werden immer mit Begruendung dokumentiert.
- Konzeptaenderungen werden IDE-uebergreifend synchron gepflegt (Cursor und VS Code + Copilot).
- Onboarding wird nie nur fuer eine Plattform gepflegt, sondern fuer alle unterstuetzten Plattformen.
- Der verbindliche Technikstack steht in `policies/technology-policy.yaml`.
- Keine realen Secrets oder personenbezogenen Daten im Repository speichern (`policies/data-protection-policy.yaml`).
- Bei SaaS-Verarbeitung mit personenbezogenen Daten ist ein AVV verpflichtend (`docs/avv-checkliste-eventlock-saas.md`).
- SBOM-Vorgaben sind verbindlich nach `policies/sbom-policy.yaml`.
- Rollen und Qualifikationsgrenzen sind verbindlich nach `policies/role-model-policy.yaml`.
- Rollen-, Rechte- und Issue-Sichtbarkeitsvorgaben sind verbindlich nach `policies/access-control-policy.yaml`.
- Revisionssichere Ereignisablage ist verbindlich nach `policies/revisionssicherheit-eventstream-policy.yaml`.
- Technische Umsetzungsvarianten stehen in `docs/eventstream-implementation-templates.md`.
- Cloud-Runbooks sind fuer AWS, Azure, GCP und OCI gleichwertig zu pflegen.
- Tenant-Ownership und Provider/Kunden-Grenzen sind verbindlich nach `policies/tenant-ownership-policy.yaml`.
- Function8-Leistungen mit AVV-Relevanz muessen transparent im Repo dokumentiert und ersetzbar sein (`policies/provider-open-services-policy.yaml`).
- GitHub-Identitaeten und Rollenbindung sind verbindlich nach `policies/github-identity-registry.json`.
- Aenderungen an AI-Regelflaechen erfolgen nur als Spiegel von Policy-Aenderungen unter `policies/`.
- Unternehmensbetrieb mit zentralem Upstream erfolgt nach `docs/fork-and-release-operating-model.md`.
- Upstream-Uebernahmen erfolgen nach `docs/release-sync-playbook.md`.
- Mischbetrieb alt/neu erfolgt mit Version-Binding nach `docs/parallelbetrieb-version-binding.md`.
- Core/Vertical-Struktur fuer Dienstleister erfolgt nach `docs/service-business-core-vertical-blueprint.md`.
- Starter-Prozesse je Vertical stehen in `docs/vertical-starter-prozesskatalog.md`.
- Arbeitsmethode und Team-Cadence werden nach `docs/arbeitsmodell-agile-cadence.md` dokumentiert.
- Rollen-/Rechtebetrieb und Issue-Sichtbarkeit stehen in `docs/access-and-issue-operations.md`.

## Erststart fuer neue Nutzer

1. `docs/START_HERE.md` lesen.
2. `policies/culture-policy.yaml`, `policies/process-policy.yaml`, `policies/technology-policy.yaml`, `policies/data-protection-policy.yaml` und `policies/role-model-policy.yaml` bestaetigen.
3. `python scripts/startup_check.py --ide auto --run-tests` erfolgreich ausfuehren.
4. Passendes Onboarding-Prompt unter `prompts/onboarding/` starten.
   Standard-MVP-Set im Referenzrepo: `software_company`, `notary`, `wealth_management`.
5. Erst danach mit produktiven Prozessaenderungen beginnen.
6. Fuer Greenfield/Brownfield den Pfad aus `docs/einfuehrung-greenfield-brownfield.md` waehlen.

## Plattform-Synchronitaet

- Bei Regel- oder Konzeptaenderungen immer beide Pfade aktualisieren:
  - Cursor: `.cursor/rules/`
  - VS Code + Copilot: `.github/copilot-instructions.md` und `docs/vscode-copilot-start.md`
