# Positionierung: Organization as Code und Enterprise GitOps

## Ziel

Dieses Dokument schaerft den Begriffsrahmen:

- `OaC8` ist die konkrete Produkt- und Betriebsauspraegung in diesem Repository.
- Das uebergeordnete Architekturmodell ist `Organization as Code (OaC)`.
- Das operative Steuerungsprinzip ist `Enterprise GitOps`.

## Begriffsrahmen

### Organization as Code (OaC)

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

### OaC8

`OaC8` ist die konkrete Umsetzung von OaC + Enterprise GitOps in diesem Repo.

## Warum diese Trennung wichtig ist

- reduziert Missverstaendnisse zwischen Tooling und Zielmodell,
- macht das Konzept anschlussfaehig fuer Fachseite, Audit und Betriebsverantwortung,
- erlaubt Drittbetrieb und Ersetzbarkeit ohne Begriffskonflikte.

## Architekturzuordnung

- `Intent Layer`: Policies, Rollen, Prozessdefinitionen
- `Control Layer`: PR, Review, Approval, Rulesets
- `Execution Layer`: Runtime, Automationen, Prozessausfuehrung
- `Evidence Layer`: revisionssicheres Event-Journal

## Meine konkrete Empfehlung

Wenn du das ernsthaft als Produkt, Plattform oder internes Transformationsmodell aufziehen willst, sollte es so geframed werden.

Begriff:

- `Organization as Code`

Plattformname:

- `Enterprise Control Plane`

Erstes Produktversprechen:

- "Team-, Rollen- und Zugriffsaenderungen laufen deklarativ, auditierbar und automatisiert ueber Git."

Das ist konkret, glaubwuerdig und gross genug, um das Paradigma zu zeigen.

## Der Ein-Satz-Pitch

Organization as Code ist ein Betriebsmodell, in dem Unternehmensstruktur, Policies und operative Aenderungen deklarativ in Git beschrieben und ueber eine Enterprise Control Plane in reale Systeme reconciled werden.
