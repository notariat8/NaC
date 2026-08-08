# pi-Projektpfad

Status: verbindliche Plattformspur neben [Codex](../.codex)

English summary: This directory makes [pi](https://pi.dev) the second official
agent platform for NaC, as a Markdown mirror of the Codex review profiles. It
is maintained synchronously with [.codex/](../.codex); see
[Platform Synchronisation](../AGENTS.md#plattform-synchronität).

Dieses Verzeichnis macht [pi](https://pi.dev) zur zweiten offiziellen
Agentenplattform für NaC. Es ist das plattformübergreifende Spiegelstück zu
[.codex/agents/](../.codex/agents) und wird bei Regel- oder Konzeptänderungen
synchron gepflegt, siehe [Plattform-Synchronität](../AGENTS.md#plattform-synchronität).

## Inhalt

| Pfad | Zweck |
| --- | --- |
| [agents/](agents) | Repo-lokale pi-Subagenten als Markdown mit Frontmatter (`name`, `description`, `tools`). Read-only-Spiegel der Codex-Review-Profile. |
| [settings.json](settings.json) | Project-lokale pi-Einstellungen. Bindet repo-lokale Skills ein. Installiert keine Extensions automatisch. |

## Subagenten

pi-subagents lädt projekt-lokale Agenten aus [agents/](agents) nach
Projektfreigabe. Alle Profile sind read-only (`tools: [read, grep, find, ls]`)
und entsprechen den Codex-Profilen unter [.codex/agents/](../.codex/agents):

| Agent | Aufgabe |
| --- | --- |
| `nac_scope_mapper` | ordnet Auftrag, Artefakte, Risiken und Validierungspfade. |
| `nac_kg_reviewer` | prüft usecase-lokale Knowledge-Graphen, stabile IDs, Privacy-Klassen. |
| `nac_bpmn_reviewer` | prüft BPMN-Modelle, NaC-Properties und KG-Verweise. |
| `nac_policy_reviewer` | prüft Datenschutz, Rollen, Lizenz, AI-SBOM und Providergrenzen. |
| `nac_docs_parity_reviewer` | prüft Deutsch/Englisch-Parität, Links und Terminologie. |
| `nac_validation_reviewer` | prüft Validierungs-Evidenz und Quality-Gate-Abdeckung. |

## Empfohlene Extensions

Extensions werden bewusst **nicht** über `settings.json` auto-installiert, weil
pi-Extensions mit vollen Systemrechten laufen. Neue Mitwirkende installieren
die empfohlenen Erweiterungen selbst und prüfen sie vor der Installation:

```bash
pi install npm:@narumitw/pi-plan-mode
pi install npm:@narumitw/pi-subagents
pi install npm:@narumitw/pi-github-pr
pi install npm:@narumitw/pi-goal
pi install npm:@narumitw/pi-caffeinate
pi install npm:@narumitw/pi-statusline
```

Diese Erweiterungen ersetzen für den pi-Pfad die Codex-Fähigkeiten
(Plan-Modus, Parallel Review, PR-Status, autonomer Abschluss, Sleep-Schutz,
Statusleiste). Die Subagenten unter [agents/](agents) werden von
`pi-subagents` geladen.

## Sicherheitsgrenze

pi-Extensions und -Skills können beliebige Aktionen ausführen. Vor der
Installation aus Drittsources den Code prüfen. Project-lokale
[settings.json](settings.json) installiert keine Packages automatisch; sie
bindet nur repo-lokale Skills ein, die der Repo-Owner bereits freigegeben hat.
