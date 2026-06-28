# NaC-On-Prem-Agent-Runtime

Status: Vertrags- und Zielsystemgrenze
Letzte inhaltliche Anpassung: 2026-06-28

## Zweck

Diese Seite beschreibt, wie NaC als agentische On-Prem-Plattform auf einem
NemoClaw-/OpenClaw-Zielsystem betrieben werden kann, ohne die GitOps-Grenzen
des NaC-Repositorys aufzugeben. Sie ergänzt das
[NemoClaw-Betriebsmodell](nemoclaw-operating-model.md) um die technische
Runtime-Grenze zwischen Quellrepo, Target-Control und produktiven
Notariats-Workflows.

Der aktuelle Zielsystemlauf auf `notoclaw01` ist ein
Target-Control-Sandboxlauf. Er beweist, dass Manifest, Skill, MCP-Schnittstelle,
Connector-Platzhalter, Smokes und Evidence auf dem Zielsystem liegen können.
Er ersetzt keine NaC-Repo-Änderung, keinen Pull Request, keine fachliche
Freigabe und keinen produktiven Connector-Apply.

## Führende Quellen

| Ebene | Führende Quelle | Bedeutung |
| --- | --- | --- |
| NaC-GitOps | NaC-Repository auf `brev01` | Code, Verträge, Doku, Policies, BPMN, KG, Tests, PRs und Releases. |
| Zielsystem-Control | `/home/ubuntu/nac-target-control` auf `notoclaw01` | Nicht-sensitive Manifeste, Runbooks, lokale Smokes und Evidence für NemoClaw/OpenClaw. |
| OpenClaw-Workspaces | `/sandbox/.openclaw/workspace-*` | Laufzeitnahe Agent-Workspaces; nicht die GitOps-Quelle für NaC. |
| Codex-Runtime | `/home/ubuntu/.codex` | Codex-Konfiguration und Thread-State; keine NaC-Artefaktquelle. |
| NemoClaw-State | `/home/ubuntu/.nemoclaw` | Runtime-State; keine GitOps-Quellartefakte. |

Der maschinenlesbare Vertrag steht in
[workflows/contracts/nac-onprem-agent-runtime.contract.json](../../../workflows/contracts/nac-onprem-agent-runtime.contract.json).
Er wird durch
[scripts/validate_nac_onprem_agent_runtime.py](../../../scripts/validate_nac_onprem_agent_runtime.py)
geprüft.

## Zielsystem-Layout

`notoclaw01` nutzt `/home/ubuntu/nac-target-control` als NaC-spezifische
Kontrollfläche. Diese Fläche ist absichtlich getrennt von `.codex`,
`.nemoclaw` und den OpenClaw-Workspace-Pfaden.

Erwartete Artefakte:

- `blueprints/nac-onprem/agents.yaml`: Agentenmanifest für den
  NaC-On-Prem-Sandboxlauf.
- `blueprints/nac-onprem/workspace-template/`: Arbeitsbereichsvorlage mit
  `AGENTS.md`, `IDENTITY.md`, `SOUL.md`, `USER.md` und `MEMORY.md`.
- `skills/nac-agent/SKILL.md`: NaC-Agent-Skill für den Zielsystemlauf.
- `mcp/nac/README.md`: lokale MCP-Grenze für NaC-Werkzeuge.
- `connectors/xnp/README.md`, `connectors/cyberjack/README.md` und
  `connectors/register/README.md`: vorbereitete Connector-Grenzen ohne
  produktive Zugangsdaten.
- `bin/nac-target-smoke` und `bin/nac-runtime-smoke`: lokale Zielsystem-Smokes.
- `evidence/2026-06-28-nac-onprem-agent-solution.md`: Nachweis des aktuellen
  Sandboxlaufs ohne Secrets und ohne Mandatsdaten.

## Agentenrollen

Der Zielsystemlauf darf schnell und lokal prüfen, aber nicht die
Projektleitung übernehmen. Der führende Project Manager bleibt im Hauptchat auf
`brev01`.

Mindest-Agenten im Target-Control-Vertrag:

- `main`: Handoff-Routing zwischen Target Operator und Project Manager,
- `notary-flow`: notarielle Workflow-Analyse ohne fachliche Letztentscheidung,
- `evidence`: Smokes, Nachweise, Secret-Prüfung und Mandatsdatenfreiheit,
- `connector-ops`: vorbereitete XNP-, Karten- und Registergrenzen.

Subagenten auf dem Zielsystem sind nur für Target-Control-Arbeit zuständig.
GitHub-Write, PR-Erstellung, OCI-Apply, Release-Schritte, Secrets und
produktive Fachsystemschreibungen bleiben im Hauptlauf und Owner-gated.

## Connector-Grenze

Die Zielsystemstruktur darf Connectoren vorbereiten, aber noch nicht produktiv
ausführen:

| Connector | Aktueller Status | Nächster NaC-Schritt |
| --- | --- | --- |
| XNP/SNP | Pfad und Smoke vorbereitet | Nach [notarial-onprem-connector-boundaries.md](notarial-onprem-connector-boundaries.md) nur lokale Readiness und redigierte Evidence. |
| cyberJack/Kartenarbeitsplatz | Pfad und Smoke vorbereitet | Nach [notarial-onprem-connector-boundaries.md](notarial-onprem-connector-boundaries.md) Karten-, PIN- und Arbeitsplatzgrenze ohne Signaturauslösung. |
| Register | Pfad und Smoke vorbereitet | Nach [notarial-onprem-connector-boundaries.md](notarial-onprem-connector-boundaries.md) nur externe Status-/Wartegates ohne produktive Einreichung. |

Keine dieser Grenzen darf echte Zugangsdaten, PINs, Kartenmaterial,
Mandatsdaten oder produktive Rückkanal-Payloads im Produktrepo oder in
`/home/ubuntu/nac-target-control` speichern.

## Datenmodell-Bezug

Der On-Prem-Agent darf das NaC-Datenmodell nutzen, aber nicht selbst zur
Wahrheitsquelle für Mandatsdaten werden. Git bleibt die Quelle für
Quellartefakte, Regeln, BPMN, KG und Verträge. Runtime-Metadaten gehören in die
jeweils freigegebene Runtime-Schicht, zum Beispiel ATP für SaaS-Metadaten oder
ein später freigegebenes On-Prem-Store-Modell.

Für Ontologie- und Graph-Arbeit bedeutet das:

- usecase-lokale KGs bleiben unter [usecases/](../../../usecases),
- runtime-nahe Status- und Ereignisdaten werden nicht als freier Agent-Speicher
  geführt,
- Oracle Graph Studio oder andere Graph-Werkzeuge sind Analyse- und
  Modellierungswerkzeuge nach separatem Gate, nicht Voraussetzung für den
  Zielsystem-Smoke,
- echte Mandatsinhalte bleiben bis zu einer gesonderten Freigabe gesperrt.

## Done-Regel

Der Target Operator darf nur den Zielsystem-Scope als erledigt melden, wenn:

- Manifest, Skill, MCP-Grenze, Connector-Stubs und Smokes frisch geprüft sind,
- Evidence keine Secrets, Tokens, PINs oder Mandatsdaten enthält,
- keine NaC-Repo-Änderung mehr erforderlich ist.

Sobald ein Contract, eine Policy, ein Validator, eine Doku oder Code im NaC-Repo
geändert werden muss, lautet der Status `Handoff an Project Manager`. Die
Gesamtarbeit ist erst nach NaC-GitOps-Validierung, Commit, Push, PR-Checks und
gegebenenfalls Owner-Review abgeschlossen.

## Offene NaC-Arbeit

Aus dem aktuellen Zielsystemlauf folgen vier NaC-seitige Arbeitsblöcke:

1. Fachliche Notar-Workflow-Regeln in BPMN, KG und Contracts präzisieren.
2. Mandatsdaten-Klassifikation, Redaktionsregeln und Speichergrenzen für
   On-Prem- und SaaS-Runtime synchron führen.
3. XNP-, cyberJack- und Register-Connectoren auf Basis des Grenzvertrags in
   private Betriebsrahmen, Testmodus und spätere Fachsystemadapter überführen.
4. Ein dauerhaftes Manifest-Onboarding für NaC-Agenten in GitOps integrieren,
   ohne `notoclaw01` zum Entwicklungsrepo zu machen.
