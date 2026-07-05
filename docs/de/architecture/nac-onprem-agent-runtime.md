# NaC-On-Prem-Agent-Runtime

Status: Vertrags- und Zielsystemgrenze
Letzte inhaltliche Anpassung: 2026-07-05

## Zweck

Diese Seite beschreibt, wie NaC seine produktive agentische Runtime von
Target-Control- und Sandbox-Evidence trennt. Für neue produktive
NaC-Agenten ist
[NVIDIA NeMo Agent Toolkit / AI-Q](nemo-agent-toolkit-aiq-m365.md) die
führende Agentic-Runtime. Der bestehende NemoClaw-/OpenClaw-Lauf auf
`notoclaw01` bleibt ein Zielsystem- und Evidence-Pfad, ohne die
GitOps-Grenzen des NaC-Repositorys aufzugeben. Diese Seite ergänzt das
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

## Agentic-Toolkit-Entscheidung: NeMo Agent Toolkit / AI-Q

Produktive agentische NaC-Workflows nutzen
[NVIDIA NeMo Agent Toolkit](https://docs.nvidia.com/nemo/agent-toolkit/latest/index.html)
als einziges führendes Agentic Toolkit. Die bevorzugte Blueprint- und
Paketierungsstrecke ist
[NVIDIA AI-Q](https://build.nvidia.com/nvidia/aiq).

Damit werden Workflow-Orchestrierung, Tool-Calling, MCP-Client-Bindung,
Agent-Runtime und lokale oder zentrale Agent-Worker auf NeMo/AI-Q ausgerichtet.
CrewAI, LangChain als primäre Runtime, OpenClaw-Runtime-Aktivierung oder
eigene Agent-Frameworks bleiben für produktive NaC-Agenten gesperrt, solange
kein bewusstes Owner-Gate mit dokumentierter Ausnahme vorliegt.

Diese Entscheidung ersetzt nicht:

- deterministische Python-Validatoren,
- `nac`-CLI- und Contract-Pruefungen,
- Office-, Word- oder Teams-Add-ins als Benutzeroberfläche,
- schlanke Python-MCP-Server,
- Runtime-Speicher, Event-Journal, WORM- oder Vault-Schichten.

Die Microsoft-365-Anbindung läuft über die in
[NeMo Agent Toolkit, AI-Q und Microsoft-365-MCP-Zielarchitektur](nemo-agent-toolkit-aiq-m365.md)
definierten MCP-Server. Outlook, Teams, OneDrive und SharePoint bleiben ihre
Quellsysteme; NeMo/AI-Q greift über MCP und Microsoft Graph akten-,
rollen- und zweckgebunden darauf zu.

## Variante C: Outbound Connector

Für das Zielbild wird die direkte Veröffentlichung der rohen
NemoClaw-/OpenClaw-Oberfläche nicht als Produktionsmuster festgelegt.
Die bevorzugte Architektur ist ein outbound Connector von `notoclaw01` nach OCI:

1. Der Browser erreicht ausschließlich die OCI-Schicht unter
   `agent.notariat8.de`.
2. OCI Identity Domain authentifiziert den Benutzer, zum Beispiel
   `user@example.com`.
3. Ein OCI API Gateway oder ein BFF prüft Session, Tenant, Rolle und Zweck.
4. ATP führt die Bindung zwischen IdP-Subjekt, Tenant, Benutzer, Agent,
   Sandbox, Lease und Audit-Metadaten.
5. `notoclaw01` baut ausgehend eine mTLS- oder WebSocket/HTTPS-Verbindung zur
   OCI-Steuerung auf und nimmt nur geprüfte Agent-Aufträge entgegen.
6. NemoClaw/OpenClaw startet, hält oder verbindet die passende Sandbox lokal.

SSH ist damit nur ein Betriebs- und Diagnoseweg, nicht der produktive
User-Traffic. Ebenso dürfen Browser nicht direkt auf Brev oder die rohe
OpenClaw-UI zeigen. Die OCI-Schicht bleibt die öffentliche Isolations-,
Identitäts- und Policy-Grenze.

## Speichergrenze für Variante C

Die dauerhafte Wahrheit liegt nicht in NemoClaw. NemoClaw ist Zielruntime.

| Ebene | Gespeichert wird | Nicht gespeichert wird |
| --- | --- | --- |
| Git / NaC | Connector-Code, Verträge, Policies, Tests, BPMN- und KG-Templates | Runtime-Sandbox-State, IdP-Tokens, Credentials, private Schlüssel, Mandatsinhalte |
| Git / OCI Landing Zone | API-Gateway-, ATP-, Vault- und Netzwerk-Absicht als IaC | Live-Secrets, TLS-Private-Key-Material, produktive Laufzeitwerte |
| ATP | Tenant-, Benutzer-, Rollen-, Agent-, Sandbox-, Lease-, Session- und Audit-Metadaten | Tokens, Claims-Rohdaten, PINs, unredigierte Mandatsinhalte |
| OCI Vault | Connector-Credentials, mTLS-Material, API-Secrets und private Schlüssel | frei lesbare Konfiguration oder fachliche Payloads |
| `notoclaw01` | laufende Sandboxes, lokaler Runtime-State, redigierte Target-Control-Evidence | NaC-GitOps-Wahrheit, produktive Mandatsdaten, globale Benutzer-/Tenant-Registry |

Für Nutzertrennung gilt: Eine produktive Sandbox darf nicht mehrere unabhängige
Benutzer teilen. Die Mindestisolierung ist `tenant + user`; bevorzugt ist
`tenant + user + vorgang + rolle`, wenn Mandats- oder Vorgangskontext geladen
wird. Wiederverwendung einer Sandbox braucht eine aktive Lease-Prüfung in ATP.

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

Der [NaC Runtime-Smoke](../operations/nac-runtime-smoke.md) ist als nächster
Zielsystem-Smoke vorbereitet, aber noch nicht ausgeführt. Er darf nur vorhandene
NemoClaw-/OpenClaw-Statussignale lesen und redigierte Evidence erzeugen; er darf
keine Installation, kein Onboarding, keinen Rebuild, keine Policy-Änderung,
keinen authentifizierten Dashboard-Link und keine Runtime-Mutation auslösen.

## Public-Origin Und Feste Domain

Die produktive On-Prem-Agent-Runtime braucht für öffentliche Erreichbarkeit eine
feste, DNS-gestützte Domain. Zufällig erzeugte Tunnel-Origins wie
provider-spezifische Tunnel-Domains sind nur für Demo- oder Diagnose-Smokes
zulässig und bestätigen nicht die Produktionsreife.

Der konkrete Hostname wird nicht im NaC-Repo hardcodiert. Er wird als
nicht-sensitive Zielsystemkonfiguration in
`/home/ubuntu/nac-target-control/config/public-origin` oder als explizites
`NAC_PUBLIC_ORIGIN` für einzelne Smokes gesetzt. Die Domain-, TLS- und
Reverse-Proxy-Einrichtung bleibt ein separater Owner-gated Betriebsschritt.

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

## Optionale Agent-Tooling-Kandidaten

Ponytail ist als optionaler Agent-Tooling-Kandidat erfasst, aber nicht
installiert und nicht aktiviert. Zulässig ist nur die dokumentierte
Over-Engineering- und Einfachheitsprüfung. Nicht zulässig sind Codex-
Lifecycle-Hooks, OpenClaw-Runtime-Aktivierung, Mandatsdatenverarbeitung,
Kürzung von Security-, Datenschutz-, Owner-Gate-, Test- oder
Validatorpflichten sowie GitHub- oder OCI-Schreibzugriff vom Zielsystem.

Der [Ponytail Skill-Only Smoke](../operations/ponytail-skill-only-smoke.md)
wurde am 2026-06-29 Owner-gated ausgeführt und bestanden. Er prüfte
ausschließlich öffentliche Metadaten, Zielpfade und nicht-sensitive
Evidence-Vorbereitung. Die
zugehörige Vorlage steht unter
[workflows/evidence-templates/ponytail-skill-only-smoke.md](../../../workflows/evidence-templates/ponytail-skill-only-smoke.md)
und darf keine Secrets, PINs, Tokens, Schlüssel, Zertifikatsmaterialien,
personenbezogenen Daten oder Mandatsdaten enthalten.

Der Zielnachweis liegt unter
`/home/ubuntu/nac-target-control/evidence/ponytail-skill-only-smoke-2026-06-29.md`.
Ponytail bleibt `candidate_not_installed`; Installation, Lifecycle-Hooks,
OpenClaw-Runtime-Aktivierung sowie GitHub- oder OCI-Write vom Zielsystem
blieben aus.

Vor jeder Installation, Hook-Aktivierung oder OpenClaw-Runtime-Aktivierung
braucht es ein eigenes Owner-Apply-Gate. Ponytail darf NaC-Governance nie
überstimmen.

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
   On-Prem- und SaaS-Runtime nach
   [matter-data-classification-redaction.md](matter-data-classification-redaction.md)
   synchron führen.
3. XNP-, cyberJack- und Register-Connectoren auf Basis des Grenzvertrags in
   private Betriebsrahmen, Testmodus und spätere Fachsystemadapter überführen.
4. Ein dauerhaftes Manifest-Onboarding für NaC-Agenten in GitOps integrieren,
   ohne `notoclaw01` zum Entwicklungsrepo zu machen.
