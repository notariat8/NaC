# NaC Skill Canvas

Der NaC Skill Canvas ist die kanonische Vorlage, um wiederkehrende oder
fachlich riskante LLM-geführte Arbeitsschritte als Workflow-Skill zu
spezifizieren. Er hilft dabei, Fachwissen nicht als flüchtigen Prompt, sondern
als prüfbares, versioniertes Arbeitsartefakt zu erfassen.

Ein Skill Canvas ersetzt keine notarielle Prüfung, keine fachliche Freigabe und
keine technische Validierung. Er beschreibt, wann ein Skill helfen darf, welche
Daten er berühren darf, wo er stoppen muss und welche Nachweise entstehen.

## Wann Einen Canvas Nutzen

Nutze einen Skill Canvas, wenn mindestens eine Bedingung erfüllt ist:

- der Auftrag kommt regelmäßig wieder,
- der Auftrag berührt Freigaben, Datenschutz, Rollen oder Evidenz,
- mehrere Usecases, Plugins, Workflows oder Policies hängen zusammen,
- ein Fachanwender soll die Regeln später prüfen oder ändern können,
- der Auftrag darf nicht allein über ein freies Chat-Prompt gesteuert werden.

Für einmalige, eng begrenzte Arbeit reicht das
[NaC-Auftragsbriefing](../../prompts/de/onboarding/nac-task-briefing.md).

## Canvas-Vorlage

```markdown
# [Skill-Name]

## Zweck

Beschreibe den notariellen Arbeitsschritt, den der Skill unterstützt.
Nenne ausdrücklich, dass der Skill keine finale rechtliche oder notarielle
Autorität ist.

## Auslöser

- Usecases:
- Rollen:
- Situationen:
- Nicht auslösen bei:

## Inputs Und Kontext

- Erlaubte Repo-Pfade:
- Erlaubte Datenklassen:
- Erforderliche Vorbedingungen:
- Verbotene Eingaben:

## Entscheidungsregeln

- Fachliche Kriterien:
- Governance-Regeln:
- Datenschutzregeln:
- Offene Fragen, die der Skill stellen muss:
- Konflikte, bei denen der Skill stoppen muss:

## Grenzen Und Verbotene Aktionen

- Der Skill darf nicht:
- Der Skill muss stoppen, wenn:
- Der Skill darf nur vorschlagen, aber nicht ausführen:

## Menschliche Freigaben

- Einfache Prüfung erforderlich bei:
- Vier-Augen-Freigabe erforderlich bei:
- Notarielle oder fachliche Freigabe erforderlich bei:
- Freigabe wird dokumentiert in:

## Outputs

- Erzeugte Artefakte:
- Geänderte Dateien:
- Nicht gespeicherte Inhalte:
- Übergabe an nächsten Schritt:

## Evidence-Metadaten

- Nachweistyp:
- Verantwortliche Rolle:
- Zeitpunkt oder Ereignis:
- Validierungsbefehl:
- Review- oder Freigabereferenz:

## Validierung

- Pflichtprüfung:
- Gezielte Zusatzprüfung:
- Manuelle Review-Fragen:
- Abnahmekriterium:

## Semantische Anker

- [Anker]: [Was dieser Anker steuern soll]
- [Anker]: [Was dieser Anker steuern soll]
- [Anker]: [Was dieser Anker steuern soll]

Nutze drei bis sieben präzise Anker. Repo-Regeln, Policies und konkrete Dateien
gehen immer vor.

## Beispiele

### Guter Beispielauftrag

Beschreibe einen Auftrag, den der Skill bearbeiten darf.

### Grenzfall

Beschreibe einen Fall, in dem der Skill Rückfragen stellen oder Alignment
einholen muss.

### Verbotener Fall

Beschreibe einen Fall, in dem der Skill stoppen muss.

## Englische Kurzfassung

Summarize purpose, trigger, allowed data, required approvals and validation in
English for technical integration.
```

## Prüffragen Vor Der Umsetzung

- Ist der Skill auf notarielle Vorgangsarten beschränkt?
- Sind echte Mandatsdaten, personenbezogene Daten, PINs und Secrets
  ausgeschlossen?
- Sind Datenklassen, verbotene Aktionen und menschliche Freigaben konkret
  benannt?
- Sind Evidence-Metadaten und Validierung prüfbar?
- Gibt es mindestens einen guten Beispielauftrag, einen Grenzfall und einen
  verbotenen Fall?
- Ist Deutsch fachlich führend und die englische Kurzfassung nur Orientierung?

## English Summary

The NaC Skill Canvas is the canonical template for specifying recurring or
risk-sensitive LLM-guided work as a workflow skill. It captures purpose,
triggers, allowed inputs, decision rules, boundaries, approvals, outputs,
evidence metadata, validation, semantic anchors and examples. It does not
replace notarial review, subject-matter approval or technical validation.
