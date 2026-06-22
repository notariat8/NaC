# Notarkammer-Demo: 1-Seiten-Handout und Talktrack

Stand: 2026-06-22

## Ziel

Der Termin soll NaC als 100% notariat-fähigen ISV-Kandidaten positionieren.
Das konkrete Ziel ist XNP/SNP-Testzugang, klärbare Pilotrollen und der
nächste Schritt zur ISV-Listung. Die Demo verkauft keinen Produktivzugang,
sondern zeigt einen sicheren Gesprächsrahmen für Freigabe, Testdaten,
Evidence-Felder, Status-Callbacks und Zertifizierungsanforderungen.

## Primärvorgang

Primärvorgang ist der Immobilienkaufvertrag. Er ist fachlich stark genug,
um Entwurf, Beurkundung, Auflassungsvormerkung, Vorkaufsrecht,
Unbedenklichkeitsbescheinigung, Löschungsunterlagen, Kaufpreisfälligkeit
und Vollzug in einem BPMN-Bild zu zeigen.

## BPMN-Talktrack

- NaC zeigt den Immobilienkaufvertrag als BPMN-Vorgang mit parallelen
  Vollzugspfaden, Dauerbändern, kritischem Pfad und Evidence-Gates.
- XNP bleibt die lokale notarielle Arbeitsumgebung; XNotar steht für
  Grundbuch- und Registervorbereitung, Validierung, Signatur und beN-Versand.
- Kartenleser, SAK/KMC und Signatur werden nur als lokale Readiness-Grenze
  gezeigt; NaC speichert keine PINs, Kartenwerte oder Tokens.
- Register und Grundbuch erscheinen als externe Warte-, Nachweis- und
  Rücklaufpunkte, nicht als direkte NaC-Datenquellen.
- Vollzug wird als fachliche Gate-Kette erklärt: erst wenn externe
  Nachweise vorliegen, kann der nächste BPMN-Schritt freigegeben werden.

## Klare Nicht-Claims

- keine produktive XNP-Aktion,
- keine Mandatsdaten,
- keine echten Register-/Grundbuchabfragen,
- keine OCI-Aktionen,
- keine Secrets,
- keine Live-Calls,
- keine Aussage, dass NaC XNP, XNotar, Register oder Grundbuch produktiv
  steuert.

## Abschlussfrage

Welche XNP/SNP-Testumgebung, ISV-Rolle, Evidence-Felder, Status-Callbacks,
Fehlerklassen und Zertifizierungsschritte braucht NaC, damit der
Immobilienkaufvertrag als offizieller ISV-Pilot vorbereitet werden kann?
