# Positionierung: Notariat as Code und Enterprise GitOps

## Ziel

Dieses Dokument schaerft den Begriffsrahmen:

- `NoC` ist die konkrete Produkt- und Betriebsauspraegung in diesem Repository.
- Das uebergeordnete Architekturmodell ist `Notariat as Code (NoC)`.
- Das operative Steuerungsprinzip ist `Enterprise GitOps`.

## Begriffsrahmen

### Notariat as Code (NoC)

Unternehmen wird deklarativ und versioniert beschrieben:

- Policies
- Rollen und Rechte
- Prozessmodelle
- Kontrollpunkte
- Nachweise

### Enterprise GitOps

Aenderungen an Organisationslogik laufen kontrolliert ueber:

- Branch
- Pull Request
- Review/Freigabe
- automatisierte Policy- und Compliance-Checks

### NoC

`NoC` ist die konkrete Umsetzung von Notariat as Code + Enterprise GitOps in diesem Repo.

## Warum diese Trennung wichtig ist

- reduziert Missverstaendnisse zwischen Tooling und Zielmodell,
- macht das Konzept anschlussfaehig fuer Fachseite, Audit und Betriebsverantwortung,
- erlaubt Drittbetrieb und Ersetzbarkeit ohne Begriffskonflikte.

## Architekturzuordnung

- `Intent Layer`: Policies, Rollen, Prozessdefinitionen
- `Control Layer`: PR, Review, Approval, Rulesets
- `Execution Layer`: Runtime, Automationen, Prozessausfuehrung
- `Evidence Layer`: revisionssicheres Event-Journal

## Projektentscheidung

Dieses Repository fuehrt die Positionierung als aktive Projektentscheidung. Die
folgenden Begriffe sind der verbindliche Begriffsrahmen fuer NoC.

Begriff:

- `Notariat as Code`

Plattformname:

- `Enterprise Control Plane`

Erstes Produktversprechen:

- "Notarielle Vorgangsarten, Plugins, Workflows, Rollen, Freigaben und
  Nachweise laufen deklarativ, auditierbar und automatisiert ueber Git."

Der aktuelle Entwicklungsstand wird in `roadmap/BUILD_NOW.md` gepflegt.

## Der Ein-Satz-Pitch

Notariat as Code ist ein Betriebsmodell, in dem notarielle Vorgangsarten,
Plugins, Workflows, Policies und operative Aenderungen deklarativ in Git
beschrieben und ueber eine Enterprise Control Plane in pruefbare Ausfuehrung
ueberfuehrt werden.
