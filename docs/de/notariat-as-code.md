# Fachkonzept: Notariat as Code Mit NaC

## Leitprinzip

NaC behandelt notarielle Vorgangsarten als versionierte, prüfbare und
freigabepflichtige Abläufe. Die fachliche Wahrheit liegt nicht in einem
Chatverlauf oder einer Oberfläche, sondern in einem nachvollziehbaren Stand aus
Usecase, Knowledge Graph, BPMN-Modell, Policy, Review und Freigabe.

Ein Vorgang wird erst verbindlich, wenn er:

1. als strukturierter Antrag oder Usecase-Stand vorliegt,
2. die fachliche Validierung besteht,
3. die erforderlichen Notariatsfreigaben durchlaufen hat,
4. je nach Delivery Mode per Pull Request oder ausdrücklich freigegebenem
   Owner-Direct in den verbindlichen Stand übernommen wurde.

## Positionierung

- `Notariat as Code` beschreibt das Zielmodell.
- `Enterprise GitOps` beschreibt den operativen Änderungsfluss.
- `NaC` ist die konkrete Umsetzung in diesem Repository.

NaC ist ausschließlich Notariat. Nicht-notarielle Beispiele gehören nicht zum
Produkt-Scope.

Referenz: [organization-as-code-positioning.md](organization-as-code-positioning.md)

## Rollenmodell

- `requester`: startet einen Vorgang oder Änderungsvorschlag.
- `notariatsfachkraft`: pflegt Vorgangsdaten, offene Angaben und Nachweise.
- `notar_fachlich`: entscheidet fachlich-notariell.
- `kostenverantwortung`: prüft Kosten- und Gebührenfragen, soweit qualifiziert.
- `reviewer`: prüft Policy-, Datenschutz-, Technik- oder QMS-Auswirkungen.
- `auditor`: prüft Historie, Nachweise, Status und Abschlüsse.
- `automation`: GitHub Actions und lokale Python-Runtime führen deterministische
  Prüfungen aus.

Details: [role-model.md](role-model.md) und
[policies/role-model-policy.yaml](../../policies/role-model-policy.yaml)

## Kanonische Usecases

Produktbeispiele stehen ausschließlich im [Usecase-Katalog](../../usecases/README.md).
Typische Einstiege sind:

- [Immobilienkaufvertrag](../../usecases/immobilienkaufvertrag)
- [Beglaubigung von Unterschriften](../../usecases/unterschriftsbeglaubigung)
- [Online-GmbH-Gründung](../../usecases/online-gmbh-gruendung)
- [Handelsregisteranmeldung](../../usecases/handelsregisteranmeldung)
- [Testament / Erbvertrag](../../usecases/testament-erbvertrag)

Jeder Usecase besitzt eine fachliche Vorderseite, eine maschinenlesbare
`knowledge-graph.graph.json`, eine Review-Sicht als `knowledge-graph.md` und
ein BPMN-Modell, soweit der Prozessstand modelliert ist.

## Datenprinzipien

- Das LLM darf Eingaben strukturieren, aber keine notarielle Entscheidung
  ersetzen.
- Deterministische Python-Logik prüft Status, Verträge und Artefakte.
- Personenbezogene Daten, Registerauszüge, Signaturgeheimnisse, PINs und echte
  Mandatsdokumente bleiben außerhalb dieses öffentlichen Repositories.
- Jeder wirksame Vorgang braucht nachvollziehbare Freigaben und Nachweise.
- Idempotenzschlüssel verhindern doppelte Ausführung technischer Schritte.

## Git Als Steuerungsschicht

- Ein Branch oder Pull Request repräsentiert Arbeit an Vorgang, Regel oder
  Usecase.
- Reviews repräsentieren menschliche Freigabe.
- Die Übernahme nach `main` repräsentiert die verbindliche Übernahme; im
  produktiven Fork per Merge, im aktiven Referenzrepo bei ausdrücklicher
  Beauftragung auch Owner-Direct.
- Tags und Releases repräsentieren geprüfte Stände.
- Artefakte repräsentieren exportierte Nachweise.

## Notariatskern Und Usecase-Schicht

Die Prozesswelt wird in zwei Schichten organisiert:

- `notariat_core`: Regeln, Rollen, Freigaben, Datenschutz, Versionierung,
  QMS-Bezug und gemeinsame Gates.
- `usecase`: vorgangsartspezifische offene Angaben, Dokumente, Entscheidungen,
  Gates und Nachweise.

Details stehen in
[service-model/notariat-scope-blueprint.md](service-model/notariat-scope-blueprint.md)
und [service-model/notarial-usecase-starter.md](service-model/notarial-usecase-starter.md).

## Variantenfähigkeit Statt Einheitsprozess

Notariate können im privaten Fork lokal unterschiedliche Varianten führen,
solange diese versioniert, freigegeben und auditierbar bleiben:

- welche Variante gilt,
- für welchen Standort oder Usecase sie gilt,
- ab wann sie gilt,
- wer sie freigegeben hat.

Für den Mischbetrieb gilt:

- Version wird je Vorgang beim Start gebunden,
- laufende Vorgänge bleiben auf ihrer gebundenen Version,
- neue Releases gelten nur für neu gestartete Vorgänge.

Details: [operations/parallelbetrieb-version-binding.md](operations/parallelbetrieb-version-binding.md)

## Grenzen Des Modells

- NaC ersetzt kein vorgeschriebenes Fachsystem.
- NaC ersetzt keine notarielle Verantwortung und keine Rechtsprüfung.
- Git ist kein Akten- oder Dokumentensafe für echte Mandatsinhalte.
- Schreibende Fachsystem-, Portal- oder Registeradapter brauchen gesonderte
  Freigabe, Datenschutzprüfung und Betriebsnachweis.
