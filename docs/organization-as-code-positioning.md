# Positionierung: Organization as Code und Enterprise GitOps

## Ziel

Dieses Dokument schaerft den Begriffsrahmen:

- `GIT OS` ist der konkrete Produkt- und Betriebsansatz in diesem Repository.
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

### GIT OS

`GIT OS` ist die konkrete Umsetzung von OaC + Enterprise GitOps in diesem Repo.

## Warum diese Trennung wichtig ist

- reduziert Missverstaendnisse zwischen Tooling und Zielmodell,
- macht das Konzept anschlussfaehig fuer Fachseite, Audit und Betriebsverantwortung,
- erlaubt Drittbetrieb und Ersetzbarkeit ohne Begriffskonflikte.

## Architekturzuordnung

- `Intent Layer`: Policies, Rollen, Prozessdefinitionen
- `Control Layer`: PR, Review, Approval, Rulesets
- `Execution Layer`: Runtime, Automationen, Prozessausfuehrung
- `Evidence Layer`: revisionssicheres Event-Journal
