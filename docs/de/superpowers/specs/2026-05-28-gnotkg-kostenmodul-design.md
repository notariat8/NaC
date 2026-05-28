# GNotKG-Kostenmodul-Design

Datum: 2026-05-28

## Entscheidung

NaC bekommt ein zentrales GNotKG-Kostenmodul. Jeder notarielle Usecase erhält
ein Kosten- und Abrechnungsgate, aber echte Geschäftswerte, Beteiligte,
Rechnungsdaten und Mandatswerte bleiben außerhalb dieses Produktrepos.

Die Berechnung wird deterministisch in Python gepflegt. Eine spätere
`xyflow`-Oberfläche rendert nur den geprüften Graph-Vertrag: Usecase,
Geschäftswert, Wertvorschrift, KV-Position, Tabelle A/B, Gebührensatz,
Auslagen, Prüfgate und Kostenentwurf.

## Quellenrahmen

Die fachliche Mindestbasis ist:

- GNotKG § 3 für Geschäftswert und Kostenverzeichnis.
- GNotKG § 34 für Wertgebühren und Rundung.
- GNotKG § 35 für allgemeine Höchstwerte.
- GNotKG Anlage 1 für KV-Positionen.
- GNotKG Anlage 2 für Tabelle A/B.

NaC rechnet nur technische Entwürfe und Reviewansichten. Die notarielle
Kostenprüfung bleibt ein Human-Gate mit dokumentierter Qualifikation.

## Architektur

1. `nac_gnotkg.costs` berechnet Wertgebühren mit `Decimal`, offizieller
   Tabellenlogik und Cent-Rundung.
2. `nac_gnotkg.views` erzeugt eine mandatsdatenfreie Kosten-Review-Ansicht
   und `xyflow`-fähige Nodes/Edges.
3. `notary_kg` macht die Ansicht über `cost-view` pro Usecase erreichbar.
4. Jeder Usecase-KG enthält `cost.business_value`,
   `decision.gnotkg_cost_path`, `gate.gnotkg_cost_review` und
   `evidence.gnotkg_cost_note`.
5. `scripts/validate_knowledge_graph.py` erzwingt diese Basisknoten für alle
   Usecases.

## Grenzen

- Kein automatischer finaler Kostenansatz ohne notarielle Prüfung.
- Keine echten Mandatswerte im Produktrepo.
- Kein zweiter fachlicher Wahrheitslayer in `xyflow`.
- Keine Portal-, Zahlungs- oder Rechnungsintegration in diesem Track.

## Akzeptanz

- Tabellenwerte für GNotKG § 34/Anlage 2 werden anhand bekannter Werte
  getestet.
- Jeder Usecase enthält das Kosten- und Abrechnungsgate.
- `nac kg cost-view <slug>` liefert eine sichere Graph-Ansicht.
- `nac gnotkg quote` liefert einen reproduzierbaren Kostenentwurf für
  eingegebene, nicht persistierte Werte.
- Strict Quality Gate bleibt grün.
