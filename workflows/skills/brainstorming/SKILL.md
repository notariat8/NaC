---
name: brainstorming
description: Nutzen, vor jeder kreativen oder nichttrivialen Arbeit. Erforscht Nutzerintention, Anforderungen und Design vor der Implementierung. Erzwingt Design-Freigabe vor Code.
---

# Brainstorming: Von Ideen zu Designs

Deutsch ist die führende fachliche Skill-Sprache. Technische Namen,
Variablennamen, Commands und IDs bleiben englisch/ASCII.

## Englische Kurzfassung

English summary: Structured brainstorming skill that enforces design-before-
implementation. Explores user intent, asks clarifying questions one at a time,
proposes 2-3 approaches with trade-offs, presents design for approval, and
writes a design spec before any code is written.

## Harte Grenze

<HARD-GATE>
Keine Implementierung, kein Code, kein Scaffolding, kein Projekt-Setup bevor
ein Design präsentiert UND vom Nutzer freigegeben wurde. Das gilt für JEDE
Änderung, unabhängig von ihrer scheinbaren Einfachheit.
</HARD-GATE>

## Einsatzgrenze

Laufzeitmodus: `brainstorming-gate`.

Dieser Skill ist ein Design-Gate vor jeder nichttrivialen Änderung. Er ersetzt keine
Owner-Freigabe und startet keine Schreiboperation. Er führt den Agenten durch
einen strukturierten Design-Prozess mit Nutzer-Freigabe vor Code.

## Anti-Pattern: „Das ist zu einfach für ein Design"

Jede nichttriviale Änderung durchläuft diesen Prozess. Eine Checkliste, ein
einzelner Config-Wert, ein kleiner Fix – alle. Bei „einfachen" Änderungen
verursachen ungeprüfte Annahmen die meiste verschwendete Arbeit. Das Design
kann kurz sein (ein paar Sätze), aber es MUSS präsentiert und freigegeben
werden.

## Checkliste

Für jedes Brainstorming sind diese Schritte in Reihenfolge abzuarbeiten:

1. **Projektkontext erkunden** – Dateien, Docs, letzte Commits prüfen
2. **Klärende Fragen stellen** – eine nach der anderen, Zweck/Randbedingungen/Erfolgskriterien verstehen
3. **2-3 Lösungsansätze vorschlagen** – mit Trade-offs und Empfehlung
4. **Design präsentieren** – in Abschnitten, skaliert nach Komplexität, Nutzer-Freigabe nach jedem Abschnitt
5. **Design-Dokument schreiben** – speichern unter `docs/de/superpowers/specs/YYYY-MM-DD-<topic>-design.md` UND `docs/en/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
6. **Spec-Selbstreview** – kurze inline-Prüfung auf Platzhalter, Widersprüche, Mehrdeutigkeiten, Scope
7. **Nutzer reviewt geschriebene Spec** – Nutzer muss die Spec-Datei vor dem Fortschreiten prüfen
8. **Übergang zur Implementierung** – erst nach Nutzer-Freigabe der Spec

## Prozessablauf

```
Kontext erkunden → Fragen stellen → Ansätze vorschlagen → Design präsentieren
→ Nutzer gibt Design frei? (nein: überarbeiten)
→ Design-Doc schreiben (de+en) → Spec-Selbstreview
→ Nutzer gibt Spec frei? (nein: überarbeiten)
→ Implementierung starten
```

## Den Prozess verstehen

**Idee verstehen:**

- Aktuellen Projektstand prüfen (Dateien, Docs, Commits)
- Vor Detailfragen den Scope abschätzen: wenn der Request mehrere unabhängige
  Subsysteme beschreibt, das sofort benennen. Keine Fragen zu Details eines
  Projekts verschwenden, das erst dekomponiert werden muss.
- Wenn das Projekt zu groß für eine einzelne Spec ist, bei der Dekomposition
  helfen: Was sind die unabhängigen Teile? Wie hängen sie zusammen? In welcher
  Reihenfolge bauen? Dann das erste Teilprojekt durch den normalen
  Design-Fluss brainstormen. Jedes Teilprojekt bekommt seinen eigenen
  Spec → Plan → Implementierungszyklus.
- Für angemessen gescopete Projekte: Fragen eine nach der anderen stellen
- Multiple-Choice-Fragen bevorzugen, offene Fragen sind auch ok
- Nur eine Frage pro Nachricht
- Fokus auf Verständnis: Zweck, Randbedingungen, Erfolgskriterien

**Ansätze erkunden:**

- 2-3 verschiedene Ansätze mit Trade-offs vorschlagen
- Optionen mit Empfehlung und Begründung präsentieren
- Mit dem empfohlenen Ansatz führen und erklären warum
- YAGNI konsequent anwenden – unnötige Features aus jedem Ansatz und Design entfernen

**Design präsentieren:**

- In Abschnitte gliedern, die zur Komplexität passen
- Nutzer-Freigabe nach jedem Abschnitt einholen
- Kein Abschnitt wird implementiert, bevor alle Abschnitte freigegeben sind

**Design-Dokument:**

- Pflichtstruktur: Zweck, Scope, Randbedingungen, Design-Entscheidungen,
  Risiken, Akzeptanzkriterien, Nicht-Ziele
- Speichern unter `docs/de/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
- Englische Übersetzung unter `docs/en/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
- Dateiname im Format `YYYY-MM-DD-<slug>-design.md` (z.B. `2026-08-09-brainstorming-skill-design.md`)
- Commit mit Begründung

**Spec-Selbstreview (vor Nutzer-Review):**

- Gibt es Platzhalter wie TODO, XXX, ??? → entfernen oder konkretisieren
- Gibt es interne Widersprüche → auflösen
- Sind Akzeptanzkriterien testbar → wenn nicht, konkretisieren
- Ist der Scope klar abgegrenzt → Scope Creep benennen und ausschließen
- Sind alle NaC-Policies eingehalten → Sprache, Lizenz, Secrets, SBOM

**Übergang zur Implementierung:**

- Erst wenn der Nutzer die geschriebene Spec-Datei freigegeben hat
- Dann Implementierungsplan erstellen (plan → review → fix)
- Dann implementieren (implement → review → fix)

## NaC-Kontext

Dieser Skill operationalisiert die AGENTS.md-Regel:

> „Nichttriviale agentische Arbeit folgt `plan -> review -> fix` vor der
> Umsetzung und `implement -> review -> fix` vor der Abnahme."

Er ersetzt NICHT:
- Owner-Gates für Apply/Release/Secret/destruktiv
- Vier-Augen-Freigabe für sensible Schritte
- Spec-Traceability (AC-IDs, Validierungsbefehle)
- Parallel Review Workflow für schichtübergreifende Änderungen

Er ergänzt:
- Strukturiertes Design vor jedem nichttrivialen Change
- Nachvollziehbare Spec-Artefakte unter `docs/*/superpowers/specs/`
- Explizite Nutzer-Freigabe vor Code