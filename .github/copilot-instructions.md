# GitHub Copilot Instructions

Dieses Repository ist ein Muster für `Notariat as Code` mit `NaC` als konkreter Betriebsausprägung.

## Verbindliche Priorität

1. Compliance und rechtliche Pflichten
2. Prozessgovernance (Review, Freigaben, Nachvollziehbarkeit)
3. Notarielle Fach- und Berufsregeln
4. Kultur- und Sprachvorgaben

## Arbeitsweise

- Behandle das LLM als Assistent für Eingaben, nicht als finale fachliche Autorität.
- Rahmen: `Notariat as Code` + `Enterprise GitOps`; `NaC` ist die konkrete Umsetzung.
- NaC ist ausschließlich für Notariate und notarielle Vorgangsarten gedacht. Nicht-notarielle Produktpfade oder Beispiele sind keine gültigen NaC-Beispiele.
- Die verbindliche Regelarchitektur steht in [docs/de/regelarchitektur.md](../docs/de/regelarchitektur.md) und [docs/en/regelarchitektur.md](../docs/en/regelarchitektur.md).
- Produktive Forks und sensible Prozessänderungen nutzen Branch + Pull Request + Review; im aktiven Referenzrepo ist Owner-Direct auf `main` zulässig, wenn der Owner direkte Lieferung ausdrücklich beauftragt.
- GitHub-first gilt für nichttriviale agentische Arbeit: ein führendes Issue beschreibt Auftrag, Scope, Akzeptanzkriterien, Risk Gate, Delivery Mode und Validierung; das Organization Project `NaC Control Plane` zeigt Status und Blocker; ein Update ist erst nach dem jeweiligen Delivery Mode und erfolgreichen `remote_ci_checks` fertig.
- Spec-Traceability gilt für neue oder geänderte nichttriviale Specs: Issue, Spec, Plan, AC-IDs und Validierungsbefehle werden nach [workflows/contracts/spec-traceability.contract.json](../workflows/contracts/spec-traceability.contract.json) verbunden und mit [scripts/validate_spec_traceability.py](../scripts/validate_spec_traceability.py) geprüft.
- Nichttriviale agentische Arbeit folgt `plan -> review -> fix` vor der Umsetzung und `implement -> review -> fix` vor der Abnahme. Bei wiederholten, unklaren oder schichtübergreifenden Fehlern gilt Diagnose vor Fix.
- Vor Merge, Owner-Merge oder PR-Abschluss wird die vollständige PR-Diff gegen den Zielbranch geprüft: `base...head`, Datei- und Commitliste. Ein einzelner HEAD-Commit reicht nicht. Wenn die Diff nicht freigegebenen Scope enthält, stoppen und Branch neu schneiden oder den kombinierten Scope ausdrücklich dokumentieren.
- Sensible Prozessschritte, insbesondere notarielle Freigaben, Register- oder Kostengates, brauchen Vier-Augen-Prinzip.
- Jede Prozessänderung muss begründet und versioniert sein.
- Ein Update gilt erst als abgeschlossen, wenn die Änderung validiert, committed, zu GitHub gepusht, je nach Auslieferungsmodus entweder in den Zielbranch gemerged oder direkt auf dem Zielbranch angekommen ist und die verpflichtenden `remote_ci_checks` erfolgreich sind.
- Wenn nach `fertig` gefragt wird, ist nur ein mit `nac doctor --profile strict` geprüfter, mit GitHub synchroner und lokal sauberer Stand fertig, wenn zusätzlich `Privacy and Secrets Guard / secret-scan`, `Privacy and Secrets Guard / privacy-lint` und `NaC Quality Gate / quality-gate` erfolgreich sind.
- [roadmap/GANTT.md](../roadmap/GANTT.md) wird aktualisiert, wenn Roadmap, Scope, Status, Meilenstein oder aktives Build-Board betroffen sind; Änderungen unter [plugins/](../plugins), [workflows/](../workflows) oder [usecases/](../usecases) aktualisieren das jeweilige Themen-Gantt nur bei fachlicher Scope-, Status- oder Meilensteinwirkung. Kleine Bugfixes, Tippfehler, lokale Doku-Klarstellungen, Test-/Validator-Fixes oder UI-Details ohne Roadmap-Wirkung brauchen keine künstliche Gantt-Änderung.
- Für das Fortschrittsbild genügt ein wöchentliches Gantt-Update; unter der Woche wird nur bei echter Roadmap-, Scope-, Status-, Meilenstein-, Pilotbereitschafts- oder Build-Board-Wirkung aktualisiert.
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
- 8-Brand-Assets für `n8` und künftige `*8`-Repos stammen kanonisch aus `bild8/www-b8` und den veröffentlichten Pfaden unter `https://bild8.de/assets/8/`. Lokale Kopien sind nur für Offline-Oberflächen oder Tests zulässig und müssen mit dieser Quelle synchron bleiben.
- Der synchrone MVP-Scope im Referenzrepo ist `notary`.
- Produktbeispiele kommen ausschließlich aus [usecases/](../usecases), zum Beispiel Immobilienkaufvertrag, Unterschriftsbeglaubigung, Online-GmbH-Gründung oder Handelsregisteranmeldung.
- Plugin- und Connector-Pläne liegen unter [docs/de/plugin-plans/](../docs/de/plugin-plans) und
  [docs/en/plugin-plans/](../docs/en/plugin-plans).
- Mindestvoraussetzungen für Base-Workspace, Plugin-Entwicklung und lokalen Notariatsarbeitsplatz stehen in [docs/de/minimum-requirements.md](../docs/de/minimum-requirements.md) und [docs/en/minimum-requirements.md](../docs/en/minimum-requirements.md).
- NaC-Ausführung und Plugin-Regeneration erfolgen lokal im genehmigten Workspace, nicht über Omnistation.
- Repo-lokale Plugins werden für neue Rechner mit `python scripts/nac.py plugins install --mode link`
  in die lokale Codex-Discovery gespiegelt; danach Codex neu starten oder eine
  neue Session öffnen.
- Bei offenem Scope, Issue-getriebener Arbeit oder mehreren relevanten Lösungswegen zuerst erkunden, einen kurzen Plan mit Zweck/Risiko nennen und Bestätigung einholen, bevor Code geändert wird.
- Nichttriviale Arbeit in zwei Schleifen führen: `plan -> review -> fix` klärt Anforderungen, Scope, Risiko und Akzeptanzkriterien; `implement -> review -> fix` prüft Umsetzung gegen Plan, Repo-Muster, Fehlerbehandlung, Tests und Sicherheit.
- Vor jedem Merge die vollständige PR-Diff gegen den Zielbranch prüfen: `base...head`, Datei- und Commitliste. Nicht nur den letzten Commit betrachten.
- Neue oder geänderte nichttriviale Specs führen nachvollziehbare AC-IDs, Spec-/Plan-Verweise und konkrete Test- oder Validator-Nachweise; historische Specs dürfen ohne Manifest bleiben, solange sie nicht fachlich weiterentwickelt werden.
- Für schichtübergreifende oder riskante NaC-Änderungen darf der [Codex Parallel Review Workflow](../docs/de/codex-parallel-review-workflow.md) genutzt werden: `nac_scope_mapper` mappt Scope und Risiken, passende read-only Spezialagenten prüfen unabhängig, und der führende Lauf setzt nur nach Freigabe um.
- Bei wiederholten oder unklaren Fehlern zuerst Diagnose und Ursache dokumentieren, dann erst ändern. Bei Änderungen an Daten-, Controller-/Logik- oder View-Schicht explizit prüfen, dass diese Schichten synchron bleiben.
- Wenn dieselbe Freigabeanforderung, derselbe Fehlerpfad, dieselbe Arbeitsunterbrechung oder derselbe Sandbox-/Operator-Reibungspunkt zweimal in einer Session oder dreimal über Issues/PRs hinweg auftritt, vor dem nächsten Retry stoppen, das Muster benennen und eine dauerhafte Optimierung vorschlagen. Zulässige Optimierungen sind Runbook, Policy-Regel, Agent-Spiegel, Approval-Text, Validator/Test, Command-Prefix-Anfrage oder Tooling-Wrapper. Ein read-only Optimierungsagent darf im Hintergrund prüfen und Vorschläge liefern; Änderungen und OCI-Schreibaktionen bleiben Owner-gated.
- Vor NaC-Releases über OCI DevOps, Functions, OCIR oder API Gateway ist die repo-lokale Release-Erinnerung [workflows/skills/nac-release-memory/SKILL.md](../workflows/skills/nac-release-memory/SKILL.md) zu lesen. Sie spiegelt [policies/process-policy.yaml](../policies/process-policy.yaml) `agent_workflows.release_memory` und ist der agentenlesbare Speicher für commitgebundene Releases, Time-Ledger-Nutzung, wiederholte Release-Reibung und OCI-Timeouts.
- Für wiederholte Release-Arbeit gilt zusätzlich das Release-Lane Context Pack in [release-lane-context.dev.json](https://github.com/notariat8/oci-landing-zone/blob/main/runbooks/release-lane-context.dev.json): Es enthält dev-only nicht-sensitive Release-Lane-OCIDs, Stack-Variablenschlüssel und Hotpath-Kommandos, damit keine broad `list` discovery als Standardpfad wiederholt wird.
- Jeder OCI-DevOps-Release-Build bleibt commitgebunden: `commit-info` ist nur Audit-Metadatum, der geprüfte Commit muss zusätzlich als `NAC_RELEASE_COMMIT` übergeben werden.
- Wiederkehrende OCI-/GitHub-Read-only-Checks im Release-Hotpath werden direkt mit den genehmigten CLI-Prefixen ausgeführt; keine `bash -lc`-Wrapper, Pipes, Environment-Präfixe oder `nac time-ledger run`-Wrapper verwenden, wenn dadurch Sandbox-/Approval-Prefixe nicht greifen. Observability danach separat protokollieren.
- routine GitHub-/OCI-Read-only-Checks brauchen keine Owner-Freigabe, solange sie nur Status, Metadaten, Logs oder GitHub-Informationen lesen, keine Secrets ausgeben und keine GitHub- oder OCI-Schreiboperation starten. Design/Release/Apply/Secret/destruktiv bleiben Owner-gated.
- Wenn mehrere unabhängige Gate-Vorbereitungen bekannt sind, werden unabhängige Gate-Vorbereitungen parallel vorbereitet; nur echte Design-, Release-, Apply-, Secret- oder destruktive Gates werden als Owner-Freigabe vorgelegt.
- Bei klar beauftragten, eng abgegrenzten Änderungen darf direkt umgesetzt werden; Annahmen und Validierung bleiben sichtbar.
- Codeänderungen brauchen Test- oder Validierungsnachweis. Bei nichttrivialem Verhalten zuerst Test, Prüfziel oder Testlücke festhalten, dann implementieren, iterieren und erneut validieren.
- UI-, Frontend- und andere visuelle Änderungen brauchen Screenshot oder vergleichbaren visuellen Nachweis vor Abschluss.
- Genehmigungspflichtige Commands müssen Zweck, Umfang und Bezug zur Aufgabe nennen; unklare Approval-Anfragen werden abgelehnt und konkret neu gestellt.

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
- [docs/de/service-model/notariat-scope-blueprint.md](../docs/de/service-model/notariat-scope-blueprint.md)
- [docs/de/service-model/notarial-usecase-starter.md](../docs/de/service-model/notarial-usecase-starter.md)
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
- Secret-Scanning-CI muss ohne unkonfigurierte kommerzielle Lizenz lauffähig sein oder die erforderliche Lizenz als GitHub-Secret dokumentiert erzwingen.
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
3. Wähle das Notariats-Onboarding unter [prompts/de/onboarding/notary-first-setup.md](../prompts/de/onboarding/notary-first-setup.md) oder [prompts/en/onboarding/notary-first-setup.md](../prompts/en/onboarding/notary-first-setup.md).
   Weitere fachliche Beispiele werden nur aus dem kanonischen [usecases/](../usecases)-Katalog abgeleitet.
4. Beginne mit einem Pilotprozess statt Vollausrollung.
5. Nutze für Fork-Betrieb, Sync und Mischbetrieb die neuen Betriebsdokumente in [docs/de/](../docs/de) und [docs/en/](../docs/en).
