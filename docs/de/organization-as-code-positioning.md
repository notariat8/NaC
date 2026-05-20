# Positionierung: Notariat as Code und Enterprise GitOps

## Ziel

Dieses Dokument schärft den Begriffsrahmen:

- `NaC` ist die konkrete Produkt- und Betriebsausprägung in diesem Repository.
- Das übergeordnete Architekturmodell ist `Notariat as Code (NaC)`.
- Das operative Steuerungsprinzip ist `Enterprise GitOps`.

## Begriffsrahmen

### Notariat as Code (NaC)

Unternehmen wird deklarativ und versioniert beschrieben:

- Policies
- Rollen und Rechte
- Prozessmodelle
- Kontrollpunkte
- Nachweise

### Enterprise GitOps

Änderungen an Organisationslogik laufen kontrolliert über:

- Branch
- Pull Request
- Review/Freigabe
- automatisierte Policy- und Compliance-Checks

### NaC

`NaC` ist die konkrete Umsetzung von Notariat as Code + Enterprise GitOps in diesem Repo.

## Warum diese Trennung wichtig ist

- reduziert Missverständnisse zwischen Tooling und Zielmodell,
- macht das Konzept anschlussfähig für Fachseite, Audit und Betriebsverantwortung,
- erlaubt Drittbetrieb und Ersetzbarkeit ohne Begriffskonflikte.

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
