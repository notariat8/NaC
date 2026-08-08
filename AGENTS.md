# AGENTS.md

Dieses Repository ist ein Muster für `Notariat as Code` mit `NaC` als konkreter Betriebsausprägung.

## Priorität der Vorgaben

1. Gesetzliche und regulatorische Pflichten
2. Verbindliche Prozess- und Governance-Regeln
3. Notarielle Fach- und Berufsregeln
4. Kultur- und Sprachregeln

## Arbeitsprinzip

- Das LLM ist Eingabeoberfläche, nicht die fachliche Wahrheit.
- Das Zielmodell ist `Notariat as Code`, der operative Änderungsfluss ist `Enterprise GitOps`.
- NaC ist ausschließlich für Notariate und notarielle Vorgangsarten gedacht. Nicht-notarielle Produktpfade oder Beispiele sind keine gültigen NaC-Beispiele.
- Fachliche Wahrheit entsteht durch versionierte Änderung + Review + Freigabe.
- Sensible Schritte brauchen Vier-Augen-Freigabe.
- Prozessänderungen werden immer mit Begründung dokumentiert.
- Die verbindliche Regelarchitektur steht in [docs/de/regelarchitektur.md](docs/de/regelarchitektur.md) und [docs/en/regelarchitektur.md](docs/en/regelarchitektur.md).
- Produktive Forks und sensible Prozessänderungen nutzen Branch + Pull Request + Review; im aktiven Referenzrepo ist Owner-Direct auf `main` zulässig, wenn der Owner direkte Lieferung ausdrücklich beauftragt.
- GitHub-first gilt für nichttriviale agentische Arbeit: ein führendes Issue beschreibt Auftrag, Scope, Akzeptanzkriterien, Risk Gate, Delivery Mode und Validierung; das Organization Project `NaC Control Plane` zeigt Status und Blocker; ein Update ist erst nach dem jeweiligen Delivery Mode und erfolgreichen `remote_ci_checks` fertig.
- Spec-Traceability gilt für neue oder geänderte nichttriviale Specs: Issue, Spec, Plan, AC-IDs und Validierungsbefehle werden nach [workflows/contracts/spec-traceability.contract.json](workflows/contracts/spec-traceability.contract.json) verbunden und mit [scripts/validate_spec_traceability.py](scripts/validate_spec_traceability.py) geprüft.
- Nichttriviale agentische Arbeit folgt `plan -> review -> fix` vor der Umsetzung und `implement -> review -> fix` vor der Abnahme. Bei wiederholten, unklaren oder schichtübergreifenden Fehlern gilt Diagnose vor Fix.
- Vor Merge, Owner-Merge oder PR-Abschluss wird die vollständige PR-Diff gegen den Zielbranch geprüft: `base...head`, Datei- und Commitliste. Ein einzelner HEAD-Commit reicht nicht. Wenn die Diff nicht freigegebenen Scope enthält, stoppen und Branch neu schneiden oder den kombinierten Scope ausdrücklich dokumentieren.
- Ein Update gilt erst als abgeschlossen, wenn die Änderung validiert, committed, zu GitHub gepusht, je nach Auslieferungsmodus entweder in den Zielbranch gemerged oder direkt auf dem Zielbranch angekommen ist und die verpflichtenden `remote_ci_checks` erfolgreich sind.
- Wenn gefragt wird, ob die Arbeit fertig ist, darf `fertig` nur gemeldet werden, wenn `nac doctor --profile strict` frisch bestanden hat, `HEAD` dem GitHub-Zielstand entspricht, der lokale Workspace sauber ist und die GitHub-Checks `Privacy and Secrets Guard / secret-scan`, `Privacy and Secrets Guard / privacy-lint` und `NaC Quality Gate / quality-gate` erfolgreich sind.
- Jede Abschlussmeldung enthält einen expliziten Abschnitt `Nächster Schritt`. Dort steht, ob Owner-Input nötig ist, welcher konkrete technische oder operative Folgeschritt ansteht, oder dass aktuell kein Owner-Input nötig ist. Ein Agent darf nicht mit einem uneindeutigen Wartezustand schließen.
- `Fertig` bedeutet tatsächlicher Abschluss der agentisch ausführbaren Arbeit. Wenn unter `Nächster Schritt` kein Owner-Input nötig ist und der Schritt mit den verfügbaren Tools ausführbar ist, arbeitet der Agent weiter, statt den Turn zu beenden. Wenn Owner-Input nötig ist, muss die Anfrage konkret, begründet und unmittelbar handlungsfähig sein.
- [roadmap/GANTT.md](roadmap/GANTT.md) wird aktualisiert, wenn Roadmap, Scope, Status, Meilenstein oder aktives Build-Board betroffen sind; Änderungen unter [plugins/](plugins), [workflows/](workflows) oder [usecases/](usecases) aktualisieren das jeweilige Themen-Gantt nur bei fachlicher Scope-, Status- oder Meilensteinwirkung. Kleine Bugfixes, Tippfehler, lokale Doku-Klarstellungen, Test-/Validator-Fixes oder UI-Details ohne Roadmap-Wirkung brauchen keine künstliche Gantt-Änderung.
- Für das Fortschrittsbild genügt ein wöchentliches Gantt-Update; unter der Woche wird nur bei echter Roadmap-, Scope-, Status-, Meilenstein-, Pilotbereitschafts- oder Build-Board-Wirkung aktualisiert.
- Lizenzmodell ist verbindlich nach [policies/license-policy.yaml](policies/license-policy.yaml): Code, Plugins, Workflows, Validatoren, Schemas und ausführbare Beispiele stehen unter `AGPL-3.0-or-later`; Dokumentation, Policies, Roadmap, Prompts und fachliche Usecases stehen unter `CC-BY-4.0`.
- Attribution nach [NOTICE](NOTICE), [AUTHORS.md](AUTHORS.md) und [CITATION.cff](CITATION.cff) sichtbar erhalten; Marken- und Namensgrenzen nach [TRADEMARK.md](TRADEMARK.md) beachten.
- Das Repo trennt installierbare Plugin-Artefakte in [plugins/](plugins), ausführbare Notariats-Workflows in [workflows/](workflows) und konkrete notarielle Usecases in [usecases/](usecases).
- Knowledge-Graph-Artefakte liegen usecase-lokal als `knowledge-graph.graph.json` und `knowledge-graph.md`; ein zentraler `knowledge-graph/` Ordner ist nicht zulässig.
- Konzeptänderungen werden plattformübergreifend synchron zwischen Policy, AGENTS.md, Codex-Agentenprofilen und pi-Subagenten gepflegt.
- Onboarding wird für den Codex-Pfad, den pi-Pfad und alle aktiven Repo-Startdokumente gepflegt.
- Progressive Disclosure gilt für Agentenkontext: [AGENTS.md](AGENTS.md) ist Router, nicht Enzyklopädie. Always-on-Regeln bleiben hier; scoped Regeln stehen in verschachtelten [AGENTS.md](AGENTS.md)-Dateien; on-demand Maps, History, Guardrails und Verification Contracts stehen im maschinenlesbaren [agent-context/index.json](agent-context/index.json); Runtime-Kontext entsteht nur aus aktueller Toolausgabe, Logs, Diffs und Evidence.
- README-, START_HERE-, Index- und Agentenregel-Dateien müssen interne Repo-Verweise als klickbare Markdown-Links führen; reine Code-Formatierung ist für Befehle, Konfigurationsschlüssel, Dateimuster und Code-Identifier reserviert.
- Der verbindliche Technikstack steht in [policies/technology-policy.yaml](policies/technology-policy.yaml).
- Neue NaC-Funktionalität braucht eine Bedienkante in der zentralen `nac`-CLI; direkte Skripte dürfen als interne Kompatibilität bleiben, aber Produktdokumentation führt über [docs/de/cli.md](docs/de/cli.md) und [docs/en/cli.md](docs/en/cli.md).
- Fachliche Prozessmodelle sind BPMN-2.0-first; `bpmn-js` ist die geplante visuelle Bearbeitungsschicht, NaC-BPMN-Properties stehen in [bpmn/nac-moddle.json](bpmn/nac-moddle.json), und BPMN-Modelle müssen mit [scripts/validate_bpmn_models.py](scripts/validate_bpmn_models.py) validierbar sein.
- Keine realen Secrets oder personenbezogenen Daten im Repository speichern ([policies/data-protection-policy.yaml](policies/data-protection-policy.yaml)); Secret-Scanning-CI muss ohne unkonfigurierte kommerzielle Lizenz lauffähig sein oder die erforderliche Lizenz als GitHub-Secret dokumentiert erzwingen.
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
- Der Notariats-Scope erfolgt nach [docs/de/service-model/notariat-scope-blueprint.md](docs/de/service-model/notariat-scope-blueprint.md).
- Starter-Beispiele sind ausschließlich notarielle Usecases nach [docs/de/service-model/notarial-usecase-starter.md](docs/de/service-model/notarial-usecase-starter.md) und [usecases/README.md](usecases/README.md).
- Arbeitsmethode und Team-Cadence werden nach [docs/de/operations/agile-cadence.md](docs/de/operations/agile-cadence.md) dokumentiert.
- Rollen-/Rechtebetrieb und Issue-Sichtbarkeit stehen in [docs/de/issues/operations.md](docs/de/issues/operations.md).
- Plugin- und Connector-Pläne werden unter [docs/de/plugin-plans/](docs/de/plugin-plans) und [docs/en/plugin-plans/](docs/en/plugin-plans) gepflegt.
- NaC-Ausführung erfolgt lokal im genehmigten Workspace; Omnistation ist für NaC kein Ausführungsort. Kartenleser-, morris- und XNP-Pfade werden über das lokale Profil `notary-workstation` geprüft.
- Mehrsprachigkeit ist repo-weit verbindlich nach [policies/language-policy.yaml](policies/language-policy.yaml); die Policy gilt für alle menschlich lesbaren Inhalte, inklusive GitHub-Root-[README.md](README.md).
- Sprachabhängige Inhalte werden in ISO-639-Sprachordnern gepflegt, mindestens `de` und `en`.
- Unabhängig von der Sprache des Prompts müssen Änderungen an lokalisierten Inhalten immer alle Standardsprachen pflegen.
- Lokalisierte Markdown-Links bleiben im Sprachpfad der Quelldatei: deutsche Inhalte verlinken deutsch, englische Inhalte verlinken englisch; Sprachwechsel gehören in explizite Sprachübersichten, nicht in den fachlichen Lesefluss.
- Für deutsches Recht und notarielle Usecases ist Deutsch die führende und rechtlich bindende Sprache; Englisch ist nur Übersetzung oder Orientierung. Usecase-Indizes, fachliche Usecase-Inhalte, Plugin-Anzeigenamen, Plugin-Beschreibungen, Plugin-README-Überschriften, Marketplace-Kategorien, Starter-Prompts und Skill-Frontmatter-Beschreibungen werden deshalb deutsch geführt, während stabile technische Identifier englisch bleiben dürfen.
- Deutsche menschlich lesbare Inhalte nutzen echte Umlaute und ß; ASCII-Umschreibungen bleiben nur für technische Identifier, Pfade, URLs, Commands und Code zulässig.
- Plugin-Karten müssen kurze lesbare Anzeigenamen, knappe Kurzbeschreibungen und echte Icon-/Logo-Assets haben; leere Platzhalterbilder sind nicht zulässig.
- 8-Brand-Assets für `n8` und künftige `*8`-Repos stammen kanonisch aus `bild8/www-b8` und den veröffentlichten Pfaden unter `https://bild8.de/assets/8/`. Lokale Kopien sind nur für Offline-Oberflächen oder Tests zulässig und müssen mit dieser Quelle synchron bleiben.

## Gemeinsame Agenten-Workflows

- Wenn Aufgaben offen formuliert sind, aus einem Issue abgeleitet werden oder mehrere fachlich relevante Lösungswege haben, erst erkunden, einen kurzen Plan mit Zweck/Risiko nennen und Bestätigung einholen, bevor Code geändert wird.
- Nichttriviale Arbeit in zwei Schleifen führen: `plan -> review -> fix` klärt Anforderungen, Scope, Risiko und Akzeptanzkriterien; `implement -> review -> fix` prüft Umsetzung gegen Plan, Repo-Muster, Fehlerbehandlung, Tests und Sicherheit.
- Vor jedem Merge die vollständige PR-Diff gegen den Zielbranch prüfen: `base...head`, Datei- und Commitliste. Nicht nur den letzten Commit betrachten.
- Neue oder geänderte nichttriviale Specs führen nachvollziehbare AC-IDs, Spec-/Plan-Verweise und konkrete Test- oder Validator-Nachweise; historische Specs dürfen ohne Manifest bleiben, solange sie nicht fachlich weiterentwickelt werden.
- Für schichtübergreifende, riskante oder mehrfach parallel prüfbare NaC-Änderungen ist der [Codex Parallel Review Workflow](docs/de/codex-parallel-review-workflow.md) der Default, sobald die Abschätzung einen Netto-Nutzen zeigt: `nac_scope_mapper` mappt Scope und Risiken, passende read-only Spezialagenten prüfen unabhängig, und der führende Lauf setzt nur nach Freigabe um. Implementierung, Secrets, OCI-Schreibaktionen, Apply-, Release- und destruktive Gates bleiben im Hauptlauf und Owner-gated.
- NaC-Subagents werden immer mit isoliertem Kontext gestartet: `fork_context: false` ist verbindlicher Default, Full-History-Forks sind verboten. Der führende Lauf übergibt ausschließlich den abgegrenzten Auftrag, relevante Pfade, Issue/PR und benötigte Regeln und schließt abgeschlossene Subagents unverzüglich. Der vollständige Haupttask-Verlauf darf nicht als Subagent-Session vervielfältigt werden.
- Bei wiederholten oder unklaren Fehlern zuerst Diagnose und Ursache dokumentieren, dann erst ändern. Bei Änderungen an Daten-, Controller-/Logik- oder View-Schicht explizit prüfen, dass diese Schichten synchron bleiben.
- Wenn dieselbe Freigabeanforderung, derselbe Fehlerpfad, dieselbe Arbeitsunterbrechung oder derselbe Sandbox-/Operator-Reibungspunkt zweimal in einer Session oder dreimal über Issues/PRs hinweg auftritt, vor dem nächsten Retry stoppen, das Muster benennen und eine dauerhafte Optimierung vorschlagen. Zulässige Optimierungen sind Runbook, Policy-Regel, Agent-Spiegel, Approval-Text, Validator/Test, Command-Prefix-Anfrage oder Tooling-Wrapper. Ein read-only Optimierungsagent darf im Hintergrund prüfen und Vorschläge liefern; Änderungen und OCI-Schreibaktionen bleiben Owner-gated.
- Der frühere OCI-Releasepfad über OCI DevOps, Functions, OCIR oder API Gateway ist für den M365-MVP archiviert. [workflows/skills/nac-release-memory/SKILL.md](workflows/skills/nac-release-memory/SKILL.md) und das frühere Release-Lane Context Pack bleiben nur Legacy-Referenzen, falls OCI später ausdrücklich reaktiviert wird.
- Die alten OCI-Release-Regeln zu commitgebundenem DevOps-Build, OCI-Read-only-Hotpath und Release-Observability gelten nur nach ausdrücklicher Reaktivierung dieses Legacy-Pfads. Der aktive MVP-Pfad ist Entra ID, Microsoft Teams, SharePoint Team Site und Microsoft Graph REST/MCP.
- Legacy-Hinweis bei ausdrücklich reaktiviertem OCI-Pfad: routine GitHub-/OCI-Read-only-Checks brauchen keine Owner-Freigabe, solange sie nur Status, Metadaten, Logs oder GitHub-Informationen lesen, keine Secrets ausgeben und keine GitHub- oder OCI-Schreiboperation starten. Design/Release/Apply/Secret/destruktiv bleiben Owner-gated.
- Wenn mehrere unabhängige Gate-Vorbereitungen bekannt sind, werden unabhängige Gate-Vorbereitungen parallel vorbereitet; nur echte Design-, Release-, Apply-, Secret- oder destruktive Gates werden als Owner-Freigabe vorgelegt.
- Jede Abschlussmeldung nennt unter `Nächster Schritt` die konkrete Fortsetzung und ob Owner-Input benötigt wird. Wenn kein weiterer Owner-Input nötig ist, wird das ausdrücklich gesagt.
- Ein Agent meldet erst dann `fertig`, wenn keine eigene agentisch ausführbare Fortsetzung mehr offen ist. `Kein Owner-Input nötig` ist kein Wartezustand; in diesem Fall wird die nächste technische Fortsetzung direkt ausgeführt. Nur konkrete externe Blocker, fehlende Daten, Owner-Gates oder nicht verfügbare Werkzeuge dürfen als wartender nächster Schritt stehen bleiben.
- Persistente Owner-Arbeitsvereinbarung: Diese Abschluss- und Weiterarbeitsregel gilt turn-, session- und kontextwechselübergreifend, sobald die Repo-Regelflächen gelesen wurden, bis der Owner sie ausdrücklich ersetzt oder aufhebt. Vor jeder Abschlussmeldung führt der Agent einen Pre-Final-Check aus: Gibt es einen agentisch ausführbaren Schritt ohne Owner-Input, wird weitergearbeitet; bleibt nur ein Owner-Gate, wird genau ein konkreter kopierbarer Freigabetext geliefert; bleibt keine agentisch ausführbare Fortsetzung, darf abgeschlossen werden. Wiederkehrende Gate-Ketten werden als Batch-/One-Shot-Freigabe vorbereitet, soweit Risk Gates das zulassen.
- Bei klar beauftragten, eng abgegrenzten Änderungen darf direkt umgesetzt werden; Annahmen und Validierung werden trotzdem dokumentiert.
- Codeänderungen brauchen vor Abschluss Test- oder Validierungsnachweis. Bei nichttrivialem Verhalten zuerst Test, Prüfziel oder bestehende Testlücke festhalten, dann implementieren, iterieren und erneut validieren.
- UI-, Frontend- und andere visuelle Änderungen brauchen vor Abschluss Screenshot oder vergleichbaren visuellen Nachweis und Iteration, bis das Ergebnis zur Anforderung passt.
- Genehmigungspflichtige Commands dürfen nur mit erkennbarem Zweck und Umfang angefragt werden. Unklare Approval-Anfragen werden abgelehnt und mit konkreter Begründung neu gestellt.

## Erststart für neue Nutzer

1. [docs/de/START_HERE.md](docs/de/START_HERE.md) oder [docs/en/START_HERE.md](docs/en/START_HERE.md) lesen.
2. [docs/de/minimum-requirements.md](docs/de/minimum-requirements.md) oder [docs/en/minimum-requirements.md](docs/en/minimum-requirements.md) lesen.
3. [policies/culture-policy.yaml](policies/culture-policy.yaml), [policies/process-policy.yaml](policies/process-policy.yaml), [policies/technology-policy.yaml](policies/technology-policy.yaml), [policies/data-protection-policy.yaml](policies/data-protection-policy.yaml), [policies/role-model-policy.yaml](policies/role-model-policy.yaml), [policies/language-policy.yaml](policies/language-policy.yaml) und [policies/license-policy.yaml](policies/license-policy.yaml) bestätigen.
4. `python scripts/startup_check.py --profile base --ide auto --run-tests` erfolgreich ausführen.
   Für Plugin-Arbeit zusätzlich `python scripts/nac.py plugins validate`,
   `python scripts/nac.py plugins install --mode link` und
   `python scripts/startup_check.py --profile plugin-dev --ide auto`.
   Danach Codex neu starten oder eine neue Session öffnen, weil Plugins beim
   Session-Start geladen werden.
   Für Kartenleser-, morris- oder XNP-nahe Arbeit zusätzlich `python scripts/startup_check.py --profile notary-workstation --ide auto`.
5. Notariats-Onboarding-Prompt unter [prompts/de/onboarding/notary-first-setup.md](prompts/de/onboarding/notary-first-setup.md) oder [prompts/en/onboarding/notary-first-setup.md](prompts/en/onboarding/notary-first-setup.md) starten.
   Produktbeispiele kommen ausschließlich aus [usecases/](usecases), zum Beispiel Immobilienkaufvertrag, Unterschriftsbeglaubigung, Online-GmbH-Gründung oder Handelsregisteranmeldung.
6. Erst danach mit produktiven Prozessänderungen beginnen.
7. Für Greenfield/Brownfield den Pfad aus [docs/de/einfuehrung-greenfield-brownfield.md](docs/de/einfuehrung-greenfield-brownfield.md) oder [docs/en/einfuehrung-greenfield-brownfield.md](docs/en/einfuehrung-greenfield-brownfield.md) wählen.

## Plattform-Synchronität

- Bei Regel- oder Konzeptänderungen immer alle Plattformpfade aktualisieren:
  - Codex: [AGENTS.md](AGENTS.md), [.codex/agents/](.codex/agents) und die Startdokumente unter [docs/de/START_HERE.md](docs/de/START_HERE.md) sowie [docs/en/START_HERE.md](docs/en/START_HERE.md)
  - pi: [.pi/agents/](.pi/agents) als Markdown-Spiegel der Codex-Review-Profile, [.pi/settings.json](.pi/settings.json) für repo-lokale Skills und [.pi/README.md](.pi/README.md) für den Plattformpfad; siehe [docs/de/platform-onboarding-matrix.md](docs/de/platform-onboarding-matrix.md) und [docs/en/platform-onboarding-matrix.md](docs/en/platform-onboarding-matrix.md)
- Bei sprachabhängigen Änderungen immer alle Standardsprachen nach [policies/language-policy.yaml](policies/language-policy.yaml) aktualisieren.
