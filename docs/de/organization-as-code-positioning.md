# Positionierung: Notariat as Code und Enterprise GitOps

## Ziel

Dieses Dokument schärft den Begriffsrahmen:

- `NaC` ist die konkrete Produkt- und Betriebsausprägung in diesem Repository.
- Das übergeordnete Architekturmodell ist `Notariat as Code (NaC)`.
- Das operative Steuerungsprinzip ist `Enterprise GitOps`.

## Begriffsrahmen

### Notariat as Code (NaC)

Notariatsbetrieb wird deklarativ und versioniert beschrieben:

- Policies
- Rollen und Rechte
- Prozessmodelle
- Kontrollpunkte
- Nachweise

### Enterprise GitOps

Änderungen an Organisations- und Notariatsprozesslogik laufen kontrolliert über:

- Branch
- Pull Request
- Review/Freigabe
- automatisierte Policy- und Compliance-Checks

### NaC

`NaC` ist die konkrete Umsetzung von Notariat as Code + Enterprise GitOps in diesem Repo.

## Warum diese Trennung wichtig ist

- reduziert Missverständnisse zwischen Tooling und Zielmodell,
- macht das Konzept anschlussfähig für Notariat, Audit und Betriebsverantwortung,
- erlaubt Drittbetrieb und Ersetzbarkeit ohne Begriffskonflikte.

## AI-native Einordnung

NaC ist nicht "AI-assisted Notariat", bei dem ein Chatbot einzelne
Arbeitsschritte beschleunigt. NaC ist ein AI-native Betriebsmodell für regulierte
notarielle Arbeit: Vorgangsarten, Rollen, Freigaben, Kontrollpunkte und
Nachweise werden so strukturiert, dass Agenten unterstützen können, ohne
fachliche Wahrheit oder notarielle Verantwortung zu ersetzen.

Die Disziplin liegt nicht im Modell allein, sondern in der NaC-Harness aus
versioniertem Wissen, Vorgaben und Sensoren. Vorgaben begrenzen Daten, Rollen,
Tools und erlaubte Aktionen. Sensoren prüfen Schema, Policy, Datenschutz,
fachliche Konsistenz, Reviewstatus und Nachweisfähigkeit. Agentenwissen lebt
daher nicht im Chatverlauf, sondern in prüfbaren Dateien: Policies, Rollen,
Skills, Prozessmodellen, Knowledge Graphs, Verträgen, Validatoren und
Freigaben.

Die menschliche Rolle verschiebt sich dadurch nicht zur blinden Delegation,
sondern zur qualifizierten Steuerung: Auftrag klären, Grenzen setzen, Ergebnisse
prüfen, Abweichungen zurückführen und Freigaben verantworten.

Diese Einordnung nutzt aktuelle AI-native Betriebssprache als NaC-spezifische,
regulierte Formulierung. Sie ist keine Delegation fachlicher oder notarieller
Verantwortung an ein Modell.

## Architekturzuordnung

- `Intent Layer`: Policies, Rollen, Prozessdefinitionen
- `Control Layer`: PR, Review, Approval, Rulesets
- `Execution Layer`: Runtime, Automationen, Prozessausführung
- `Evidence Layer`: revisionssicheres Event-Journal

## Projektentscheidung

Dieses Repository führt die Positionierung als aktive Projektentscheidung. Die
folgenden Begriffe sind der verbindliche Begriffsrahmen für NaC.

Begriff:

- `Notariat as Code`

Plattformname:

- `Enterprise Control Plane`

Erstes Produktversprechen:

- "Notarielle Vorgangsarten, Plugins, Workflows, Rollen, Freigaben und
  Nachweise laufen deklarativ, auditierbar und automatisiert über Git."

Der aktuelle Entwicklungsstand wird in `roadmap/BUILD_NOW.md` gepflegt.

## Der Ein-Satz-Pitch

Notariat as Code ist ein Betriebsmodell, in dem notarielle Vorgangsarten,
Plugins, Workflows, Policies und operative Änderungen deklarativ in Git
beschrieben und über eine Enterprise Control Plane in prüfbare Ausführung
überführt werden.
