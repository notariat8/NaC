# Codex Parallel Review Workflow

Dieser Workflow ist die NaC-nahe Umsetzung dessen, was bei anderen
Coding-Agenten als dynamische oder agentische Workflows sichtbar wird. NaC
wartet dafür nicht auf eine Produktfunktion. Wir nutzen heute die vorhandenen
Codex-Bausteine: explizite Subagents, repo-lokale Agentprofile, `codex exec`,
Codex SDK, Codex als MCP-Server und die bestehenden NaC-Validatoren.

Der Workflow ist bewusst kein autonomer Produktivpfad. Er ist eine
Review-Harness für nichttriviale Änderungen an KG, BPMN, Verträgen, Policies,
Doku und Validatoren.

## Wann Nutzen?

Standardmäßig nutzen, wenn die schnelle Abschätzung einen Netto-Nutzen gegenüber der Koordination zeigt. Der führende Lauf bleibt verantwortlich und entscheidet vorab, welche Subagents wirklich unabhängig prüfen können.

Nutzen, wenn eine Aufgabe mindestens eine dieser Eigenschaften hat:

- mehrere fachliche Schichten sind betroffen, zum Beispiel KG und BPMN;
- der Review braucht verschiedene Perspektiven, etwa Datenschutz, Rollen,
  Doku-Parität und Tests;
- ein Issue oder ein Pull Request soll vor der Umsetzung oder vor der Abnahme
  stressgetestet werden;
- die Änderung könnte echte Mandatsdaten, externe Dienste, Lizenzgrenzen oder
  notarielle Freigaben berühren;
- viele ähnliche Artefakte sollen wiederholt geprüft werden.

Nicht nutzen für kleine Tippfehler, reine Linkkorrekturen oder klar begrenzte
Ein-Datei-Änderungen ohne Governance-Risiko. Nicht an Subagents delegieren:
Secrets, OCI-Schreibaktionen, Apply-, Release- oder destruktive Gates.

## Agentprofile

Die repo-lokalen Profile liegen unter [`.codex/agents/`](../../.codex/agents):

| Agent | Aufgabe |
| --- | --- |
| `nac_scope_mapper` | ordnet Auftrag, Artefakte, Risiken und passende Review-Agenten. |
| `nac_kg_reviewer` | prüft usecase-lokale JSON-KGs, stabile IDs, Aliase, Herkunft und Privacy-Klassen. |
| `nac_bpmn_reviewer` | prüft BPMN-Modelle, NaC-Properties und KG-Verweise. |
| `nac_policy_reviewer` | prüft Datenschutz, Rollen, Lizenz, AI-SBOM und Providergrenzen. |
| `nac_docs_parity_reviewer` | prüft Deutsch/Englisch-Parität, Links und agentische Regelspiegel. |
| `nac_validation_reviewer` | prüft, welche Validatoren und Tests den Auftrag wirklich abdecken. |

Alle Profile sind zunächst `read-only`. Änderungen bleiben beim führenden
Codex-Lauf oder bei einem ausdrücklich freigegebenen Implementierungsschritt.

## Ablauf

1. Der führende Codex-Lauf beschreibt Auftrag, Scope, Risiko und gewünschtes
   Ergebnis.
2. `nac_scope_mapper` erstellt eine Review-Matrix mit Artefakten,
   Spezialagenten und Validierungsbefehlen.
3. Die passenden Spezialagenten prüfen unabhängig und liefern konkrete
   Findings mit Dateipfaden, IDs und Prüfbefehlen.
4. Der führende Lauf fasst Findings zusammen, trennt Blocker von Hinweisen und
   entscheidet, welche Änderungen umgesetzt werden.
5. Umsetzung erfolgt klein und nachvollziehbar im normalen NaC-Arbeitsfluss.
6. `nac_validation_reviewer` oder der führende Lauf prüft die frischen
   Validator-Ausgaben.
7. Abschluss bleibt nur mit menschlicher Review, Git-Diff und passenden
   NaC-Gates möglich.

## Beispielprompt

```text
Nutze den NaC Parallel Review Workflow.
Lass nac_scope_mapper zuerst Scope, betroffene Artefakte, Risiken und Validatoren
für diese Änderung mappen. Danach prüfe parallel mit nac_kg_reviewer,
nac_bpmn_reviewer, nac_policy_reviewer, nac_docs_parity_reviewer und
nac_validation_reviewer, soweit sie für den Scope passen. Fasse Blocker,
Review-Hinweise und konkrete nächste Änderungen zusammen. Keine produktiven
Schreibaktionen ohne meine Freigabe.
```

## Vertrag Und Validierung

Der maschinenlesbare Vertrag steht in
[workflows/contracts/codex-parallel-review.contract.json](../../workflows/contracts/codex-parallel-review.contract.json).
Er legt Agentprofile, Guardrails, Eingaben, verbotene Datenklassen,
Review-Gates, Nachweisfelder und Validierungsbefehle fest.

Prüfung:

```bash
python scripts/validate_codex_parallel_review.py
```

Für breitere Änderungen bleiben zusätzlich relevant:

```bash
python scripts/validate_language_parity.py
python scripts/validate_governance_sync.py
python scripts/validate_knowledge_graph.py
python scripts/validate_bpmn_models.py
python scripts/quality_gate.py --profile strict
```

## Grenze

Der Workflow darf Findings vorbereiten und Änderungen beschleunigen. Er darf
aber keine notarielle Wahrheit feststellen, keine KG-Knoten automatisch mergen,
keine echten Mandatsdaten verarbeiten, keine externen Dienste ohne AVV-/DPA-
und AI-SBOM-Gate nutzen und keine produktive Freigabe ersetzen.
