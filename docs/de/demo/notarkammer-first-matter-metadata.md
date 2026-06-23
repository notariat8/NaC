# Notarkammer-Demo: erster Vorgang als metadata-only Fixture

Die Fixture `tests/fixtures/demo/notarkammer-first-immobilienkaufvertrag.metadata.json`
beschreibt den ersten vorführbaren Immobilienkaufvertrag nur als
metadata-only Startpunkt. Sie ist kein Akteninhalt, keine produktive
Einreichung und kein Ersatz für fachliche Prüfung.

Sie enthält nur sichere Demo-Metadaten:

- Demo-IDs für Notariat und Vorgang
- Immobilienkaufvertrag als primären Vorgang
- XNP/SNP als Zielsysteme nur als metadata-only Ausrichtung
- Referenzen auf BPMN, Knowledge-Graph und Kostenprüfungsmodul
- Rollenklassen statt Namen
- Dokumentklassen statt Dokumentinhalte
- Dauerbänder, Parallelgruppen und kritische-Pfad-Marker
- Guardrails für no mandate data, keine produktive Einreichung und keine
  Zugangsdaten
- Guardrails für no OCI Apply, no secret material und keine echten
  Registerdaten

Wenn Design-, Release-, Apply- oder Secret-Arbeit aus dieser Demo abgeleitet
wird, bleibt sie außerhalb dieses Contract-Scopes. Der vorgeschlagene Gate-Satz
dafür lautet: Design-Review, Release-Review, Apply-Freigabe,
Secret-Freigabe und fachliche notarielle Prüfung.

Ziel für die Vorführung: notariat8 kann den ersten Vorgang erklären, ohne
Mandatsdaten, Ausweise, Urkunden, Kaufpreise, Grundbuchdaten oder interne
Betriebsdetails zu zeigen.
