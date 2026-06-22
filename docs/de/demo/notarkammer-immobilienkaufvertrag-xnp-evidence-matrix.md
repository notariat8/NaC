# Notarkammer-Demo: XNP/SNP-Evidence-Matrix zum Immobilienkaufvertrag

Stand: 2026-06-22

Dieses Dokument ist ein Demo-/Modellierungsartefakt für den
Immobilienkaufvertrag. Es beschreibt, welche BPMN-Gates in der Vorführung
wiederholt mit XNP/SNP, XNotar, Kartenleser, Signatur, Register, Grundbuch und
Vollzug verbunden werden. Es behauptet keine produktive XNP-Aktion, nutzt keine
Mandatsdaten, keine Secrets und keine API-Credentials.

## Matrix

| BPMN-Gate | externe Umgebung | erwarteter Nachweis | Parallelität | kritischer-Pfad-Relevanz | Demo-Aussage |
| --- | --- | --- | --- | --- | --- |
| Vorgang synthetisch anlegen | NaC-Demo ohne Fachsystemgrenze | Audit-Metadaten: Demo-ID, Rollenklasse, Zeitstempel, kein Personenbezug | nicht parallel; Startpunkt | nicht kritisch | Immobilienkaufvertrag startet als synthetischer Modellfall, keine Mandatsdaten. |
| Grundbuchstand und Registerbezug vorprüfen | Grundbuch, Register, manuelle Evidence | Rücklaufnachweis oder Platzhalter: Status vorhanden, fehlt, blockierend | parallel in `pre_notarization_due_diligence` mit Entwurf und Readiness | kritisch, wenn Grundbuch- oder Registerstatus den Vollzug blockiert | NaC zeigt die Evidence-Lücke und behauptet keinen produktiven Abruf. |
| XNP/SNP-, XNotar- und Kartenleser-Readiness prüfen | lokale XNP/SNP-Umgebung, XNotar, Kartenleser | Readiness-Nachweis: Komponente erreichbar, Signaturpfad modelliert, keine PINs oder Kartenwerte | parallel in `pre_notarization_due_diligence` | meist nicht kritisch; kritisch nur bei fehlender Signaturbereitschaft vor Beurkundung | Die Demo zeigt Systemgrenzen, keine produktive XNP-Aktion. |
| Entwurf und Beteiligtenstatus abstimmen | XNP/SNP-Testzugang als offene ISV-Frage | Audit-Metadaten: Entwurfsstatus, Freigabestatus, Evidence-Klasse | parallel in `pre_notarization_due_diligence` | kritisch, wenn Freigabe oder Unterlage fehlt | XNP/SNP bleibt Testzugangsfrage, nicht produktive Integration. |
| Beurkundung und Signaturkontext bestätigen | Kartenleser, Signatur, beN, XNotar | Readiness-Nachweis und Signatur-Evidence: Rolle, Zeit, Hash-/Statusklasse, Fehlerklasse | Sequenzpunkt nach Vorprüfung | kritisch | Die Demo erklärt, welche Nachweise erwartet werden, ohne Kartenwerte, Secrets oder Urkundeninhalte zu zeigen. |
| Auflassungsvormerkung vorbereiten | XNotar/beN, Grundbuch | Versandnachweis und Rücklaufnachweis: Antrag vorbereitet, Versandstatus, Grundbuchrücklaufklasse | parallel in `post_notarization_completion` | kritisch, wenn Rücklauf blockierend ist | Vollzug hängt am externen Rücklauf, nicht an einer NaC-Bedienzeit. |
| Vorkaufsrecht und Behördenrücklauf überwachen | Gemeinde, Register-/Behördenkontext | Rücklaufnachweis: Frist, Antwortklasse, blockierend oder erledigt | parallel in `post_notarization_completion` | kritisch, wenn Frist oder Antwort den Vollzug blockiert | Parallelität und kritischer Pfad werden als BPMN-Evidence sichtbar. |
| Unbedenklichkeit und Löschungsunterlagen nachhalten | Finanzverwaltung, Banken, Grundbuch | Rücklaufnachweis: Steuerstatus, Löschungsstatus, fehlend oder erledigt | parallel in `post_notarization_completion` | kritisch, wenn Nachweis blockierend bleibt | Die Demo trennt Nachweisstatus von echten Steuer-, Bank- oder Grundbuchdaten. |
| Kaufpreisfälligkeit prüfen | notarielle Entscheidung, Finanzierungsbezug | Audit-Metadaten: Gate-Kombination erfüllt, blockierend, manuell geprüft | Übergang zu `ownership_transfer` | kritisch | NaC modelliert die Freigabelogik als Evidence-Matrix, nicht als Rechtsberatung. |
| Eigentumsumschreibung und Abschluss | XNotar/beN, Grundbuch, Vollzug | Versandnachweis, Rücklaufnachweis, Abschluss-Audit | parallel in `ownership_transfer`, Abschluss nach letztem Rücklauf | kritisch bis Abschluss; danach nicht kritisch | Der kritischer Pfad endet beim letzten blockierenden Vollzugsnachweis. |

## Demo-Grenzen

- keine produktive XNP-Aktion,
- keine produktive XNotar-, beN-, Register- oder Grundbucheinreichung,
- keine Mandatsdaten, Grundbuchdaten, Registerdaten, Steuerdaten, Bankdaten
  oder Personendaten,
- keine Secrets, keine API-Credentials, keine PINs, Tokens oder Kartenwerte,
- nur Demo-/Modellierungsartefakt für BPMN, Evidence, Parallelität und
  kritischer Pfad.
