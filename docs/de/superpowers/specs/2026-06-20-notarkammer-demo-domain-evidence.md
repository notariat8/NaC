# Notarkammer Demo: Fachliche Evidenz Für Immobilienvollzug

Status: Arbeitsstand für Demo-Readiness
Datum: 20. Juni 2026
Scope: Immobilienkaufvertrag und öffentlicher, mandatsdatenfreier Demo-Kontext

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: notarkammer-demo-domain-evidence
leading_issue: thread:2026-06-20-notarkammer-demo-readiness
risk_gate: Notarkammer Demo Readiness
delivery_mode: Protected PR
acceptance_ids:
  - AC-001
  - AC-002
  - AC-003
validation_commands:
  - /home/ubuntu/.venvs/nac/bin/python scripts/validate_language_parity.py
  - /home/ubuntu/.venvs/nac/bin/python scripts/validate_spec_traceability.py
  - /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
```

## Zweck

Diese Evidenz stützt die Notarkammer-Demo fachlich ab. Sie beschreibt typische
Vollzugsprobleme, Abhängigkeiten, Parallelität, kritischen Pfad und
Dauerklassen. Dauerwerte sind Planungsparameter und keine amtlichen
Durchschnittswerte, solange keine zitierfähige amtliche Statistik hinterlegt
ist.

## Rechtliche Und Fachliche Anker

- Grundstückskaufverträge brauchen notarielle Beurkundung; fachlicher Anker:
  BGB § 311b.
- Eigentumsänderungen an Grundstücken brauchen Einigung und Eintragung;
  fachlicher Anker: BGB § 873.
- Die Vormerkung sichert den Anspruch auf dingliche Rechtsänderung;
  fachlicher Anker: BGB § 883.
- Die Auflassung ist die Einigung über Eigentumsübertragung;
  fachlicher Anker: BGB § 925.
- Grundbuchanträge, Rang, Zwischenverfügung, Bewilligung und Auflassungsnachweis
  sind über die GBO fachlich relevant; insbesondere GBO §§ 13, 17, 18, 19, 20.
- Grunderwerbsteuerliche Anzeige und steuerliche Unbedenklichkeit sind
  Vollzugsgates; fachliche Anker: GrEStG §§ 18, 22.
- Kommunales Vorkaufsrecht und Negativzeugnis können den Vollzug prägen;
  fachliche Anker: BauGB §§ 24, 28.
- Beurkundung, Identitätsprüfung, Belehrung und Urkundsablauf laufen im Rahmen
  des BeurkG; fachlicher Anker: BeurkG § 17.

## Typische Vollzugsblocker

- Beteiligtenidentität, Vertretungsmacht, Vollmacht, Gesellschafts- oder
  Erbnachweise sind unklar.
- Verbraucherbezogene Entwurfs- und Prüfpflichten sind nicht sauber
  dokumentiert.
- Grundbuchstand passt nicht zur Angabe im Vorgang.
- Vormerkung, Rang oder laufende Anträge blockieren die nächste Stufe.
- Nicht übernommene Belastungen brauchen Löschungsunterlagen,
  Treuhandauflagen oder Ablösebeträge.
- Finanzierung/Grundschuld ist nicht rechtzeitig oder nicht rangrichtig
  vorbereitet.
- Gemeinde, Behörde oder sonstige Stelle liefert Genehmigung oder
  Negativzeugnis nicht rechtzeitig.
- Grunderwerbsteuer ist nicht festgesetzt, nicht bezahlt oder die
  Unbedenklichkeitsbescheinigung liegt nicht vor.
- Kaufpreiszahlung oder Zahlungsnachweis fehlt.

## Parallelität

Nach Beurkundung können mehrere Arbeitsstränge parallel beginnen:

- Anzeige an das Finanzamt.
- Anfrage an Gemeinde oder Behörde.
- Antrag auf Auflassungsvormerkung.
- Koordination der Löschungsunterlagen.
- Finanzierungsgrundschuld und Bankauflagen.
- Nachhalten von Genehmigungen.

Diese Stränge konvergieren bei der Kaufpreisfälligkeit. Die Fälligkeitsmitteilung
darf in der Demo erst als möglich erscheinen, wenn alle relevanten
Fälligkeitsvoraussetzungen erfüllt sind.

## Kritischer Pfad

Der kritische Pfad ist fallabhängig. Für die Demo ist folgender Pfad plausibel:

1. Entwurfsreife und etwaige Verbraucherfrist.
2. Beurkundung.
3. Nachbeurkundungsversand und Anträge.
4. Eintragung der Vormerkung.
5. Genehmigungen, Negativzeugnis und Löschungsunterlagen.
6. Finanzierungs-/Grundschuldreife, falls finanziert.
7. Fälligkeitsmitteilung.
8. Kaufpreiszahlung.
9. Steuerliche Unbedenklichkeitsbescheinigung.
10. Eigentumsumschreibung.

Der längste externe Rücklauf dominiert häufig die Gesamtdauer. Das kann
Grundbuchamt, Gemeinde, Finanzamt, Bank oder abzulösende Gläubigerin sein.

## Demo-Sichere Dauerklassen

Diese Klassen sind bewusst Planungswerte:

| Klasse | Zeitraum | Verwendung |
| --- | --- | --- |
| `same_day_or_internal` | 0-1 Arbeitstag | interne Prüfung, Versand, Statuspflege |
| `short_party_turnaround` | 1-5 Arbeitstage | fehlende Angaben, Bankformulare, einfache Nachweise |
| `standard_external` | 1-3 Wochen | übliche externe Rückläufe in der Demo |
| `extended_external` | 3-8 Wochen | Grundbuch/Behörde/Bank/Gläubiger mit längerer Bearbeitung |
| `statutory_or_exceptional` | bis 2 Monate oder mehr | gesetzliche Fristen, Sondergenehmigungen, komplexe Fälle |

## Empfohlenes Prozessskelett Für Den Immobilienkauf

1. Anfrage und Beteiligte aufnehmen.
2. Identität, Vertretung und Register-/Erbnachweise prüfen.
3. Grundstücks- oder Wohnungseigentumsdaten erfassen.
4. Aktuellen Grundbuchstand prüfen.
5. Eigentum, Belastungen und laufende Anträge prüfen.
6. Finanzierung, Grundschuld und Bankauflagen klären.
7. Nicht übernommene Belastungen und Löschungsbedarf klären.
8. Öffentlich-rechtliche Genehmigungen und Vorkaufsrechte prüfen.
9. Kaufpreis, Fälligkeit, Besitz, Nutzen und Lasten klären.
10. GNotKG-Geschäftswert und Kostenpfad prüfen.
11. Urkundenentwurf erstellen.
12. Verbraucherfrist prüfen und dokumentieren, falls einschlägig.
13. Entwurf versenden.
14. Rückfragen und Freigaben der Beteiligten dokumentieren.
15. Beurkundung vorbereiten.
16. Beurkundung durchführen.
17. Ausfertigungen und Abschriften erzeugen.
18. Finanzamt informieren.
19. Gemeinde/Behörde anschreiben.
20. Auflassungsvormerkung beantragen.
21. Löschungsunterlagen und Ablösebeträge koordinieren.
22. Grundschuld vorbereiten und einreichen, falls finanziert.
23. Genehmigungen und Negativzeugnisse nachhalten.
24. Vormerkung und Rang prüfen.
25. Fälligkeitsvoraussetzungen prüfen.
26. Fälligkeitsmitteilung versenden.
27. Kaufpreiszahlung oder Zahlungsnachweis erfassen.
28. Besitz-/Nutzen-/Lastenübergang dokumentieren.
29. Unbedenklichkeitsbescheinigung nachhalten.
30. Eigentumsumschreibung beantragen.
31. Grundbuchvollzug prüfen.
32. GNotKG-Abrechnung prüfen.
33. Abschlussnachweise und Aktenabschluss dokumentieren.

## Modellierungsregel Für Die Demo

Jeder Schritt darf Dauer, Parallelgruppe und Kritischer-Pfad-Hinweis nur als
Metadaten führen. Echte Werte aus einem Mandat, Personen, Grundstücke,
Aktenzeichen, Konten, Beträge oder Portalzugänge bleiben außerhalb des
Repository.

## Akzeptanzkriterien

- AC-001: Die Evidenz nennt die rechtlichen Anker für Beurkundung, Vormerkung,
  Grundbuchvollzug, Grunderwerbsteuer und Vorkaufsrecht ohne Mandatsdaten.
- AC-002: Die Dauerklassen sind ausdrücklich als Planungsparameter beschrieben
  und nicht als amtliche Durchschnittswerte.
- AC-003: Die Prozessstruktur zeigt Parallelität und kritischen Pfad, ohne
  echte Personen-, Grundstücks-, Konto-, Akten- oder Portalwerte aufzunehmen.
