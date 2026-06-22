# Notarkammer-Demo: XNP/SNP API- und Testzugang für ISV

Stand: 2026-06-22

Dieses Demo-Artefakt bereitet die Gesprächsfrage an BNotK und Notarkammer vor:
Welche XNP-/SNP-API- oder Testzugänge braucht NaC als ISV, damit der
Immobilienkaufvertrag sauber, prüfbar und ohne Mandatsdaten an die offiziellen
notariellen Systemgrenzen angebunden werden kann?

Die Quellenbasis bleibt die bestehende
[XNP-Quellenmatrix](notarkammer-xnp-quellenmatrix.md). Sie belegt XNP,
XNotar, Grundbuch-, Register- und Kartenleser-Bezüge als fachliche Umgebung,
aber keine produktive NaC-Kopplung. Diese Seite formuliert deshalb nur den
Klärungsbedarf für Test- und API-Zugänge.

## Primärfluss Immobilienkaufvertrag

Für die Notarkammer-Demo ist der Immobilienkaufvertrag der Hauptfluss. NaC
zeigt daran, warum ein ISV nicht nur eine schöne Oberfläche braucht, sondern
einen verlässlichen Zugang zu Testsystemen, Schnittstellenverträgen und
fachlichen Grenzdefinitionen:

1. Vorgang anlegen, Rollen und Beteiligtenkommunikation nur synthetisch
   modellieren.
2. Entwurf, Unterlagen, Genehmigungen und Finanzierung als BPMN-Gates führen.
3. Beurkundung als menschliche notarielle Freigabe markieren.
4. Vollzug parallel nachhalten: Grundbuch, Finanzierung, Gemeinde/Steuer,
   Löschungsunterlagen und Rückläufe.
5. XNP, XNotar, beN, Kartenleser und Signaturpfad nur als lokale oder externe
   Fachsystemgrenzen zeigen.

Das Demo-Ziel ist nicht produktive Automatisierung. Das Demo-Ziel ist, die
richtigen Fragen für einen späteren freigegebenen Integrationspfad zu stellen.

## Warum NaC Testzugang braucht

NaC kann die fachliche Prozessverantwortung bereits als BPMN, Evidence-Gate
und Auditstatus zeigen. Ohne offiziellen XNP-/SNP-Testzugang bleiben jedoch
entscheidende Details offen:

- Welche Vorgangs-, Status- oder Nachweisobjekte dürfen ISVs lesen oder
  schreiben?
- Welche Testdaten, Testzertifikate, Rollen und Amtstätigkeitskontexte sind
  für einen Immobilienkaufvertrag zulässig?
- Welche lokalen Arbeitsplatzprüfungen sind erlaubt, ohne PINs, Kartenwerte,
  Tokens, Registerdaten oder Grundbuchinhalte zu berühren?
- Welche Export-, Import-, Callback-, Event- oder API-Flächen sind für
  Evidence und Status gedacht?
- Welche Zertifizierung, Sicherheitsprüfung, Protokollierung und Freigabe
  verlangt die BNotK oder die zuständige Kammer vor einem Pilotbetrieb?

NaC braucht diesen Zugang als ISV, weil der Immobilienkaufvertrag mehrere
offizielle Grenzen berührt: XNP-Arbeitsplatz, XNotar-Grundbuchpfad, beN,
Signatur/Kartenleser, Rücklaufnachweise und notarielle Freigaben. Ohne
Testumgebung kann NaC nur die Grenze benennen; mit freigegebenem Testzugang
kann NaC die Grenze korrekt, datensparsam und auditierbar integrieren.

## API-Fragen an BNotK/Notarkammer

Diese Fragen sind für den Termin geeignet. Sie fragen bewusst nach Test- und
Freigabewegen, nicht nach produktiver Live-Nutzung.

| Bereich | Frage |
| --- | --- |
| ISV-Onboarding | Gibt es ein offizielles ISV- oder Herstellerprogramm für XNP/SNP-Testzugänge, inklusive technischer Ansprechpartner, Nutzungsbedingungen und Sicherheitsprüfung? |
| Testumgebung | Gibt es eine dedizierte XNP-/SNP-Testumgebung für Immobilienkaufvertrag, Grundbuchvollzug, beN-Status und Signaturpfad ohne echte Mandats- oder Registerdaten? |
| API-Umfang | Welche XNP-/SNP-APIs, lokalen Schnittstellen, Export-/Importformate oder Event-/Statusmechanismen sind für ISVs dokumentiert und freigabefähig? |
| Rollen und Rechte | Welche Testrollen, Amtstätigkeitskontexte, Organisationszuordnungen und Karten-/Zertifikatsprofile dürfen in einer ISV-Testumgebung verwendet werden? |
| Evidence | Welche Status- und Nachweisfelder dürfen in einem Drittsystem gespeichert werden, wenn keine Rohdokumente, keine Mandatsdaten und keine Zugangsdaten übernommen werden? |
| Immobilienkaufvertrag | Welche fachlichen Statuspunkte eines Immobilienkaufvertrags sind für eine API-/Evidence-Integration geeignet: Vormerkung, Löschungsunterlagen, Vorkaufsrecht, Unbedenklichkeitsbescheinigung, Umschreibung oder beN-Versandstatus? |
| Grundbuch und Register | Gibt es für Grundbuch- oder Registerpfade ausschließlich XNotar/XJustiz-/beN-Übergaben, oder existieren zusätzliche freigegebene Test-Callbacks oder Statusabfragen für ISVs? |
| Lokaler Arbeitsplatz | Darf ein lokaler Companion Readiness prüfen, zum Beispiel installierte Komponenten, Rollenstatus oder Erreichbarkeit, solange keine PINs, Tokens, Kartenwerte, Dokumentinhalte oder Mandatsdaten ausgelesen werden? |
| Protokollierung | Welche Auditfelder erwartet die BNotK/Kammer für Test- und Pilotbetrieb: Zeitpunkt, Rolle, Systemgrenze, Hash, Status, Freigabe, Fehlklasse? |
| Zertifizierung | Welche Schritte sind vor einem Pilot mit Notariat oder Kammer erforderlich: Datenschutzprüfung, AVV/DPA, Penetrationstest, Herstellerfreigabe, Kammerfreigabe, BNotK-Abnahme? |
| Betrieb | Welche Trennung ist zwischen Test-, Pilot- und Produktivzugang vorgeschrieben, und wie werden Schlüssel, Zertifikate, Client-IDs oder lokale Konfigurationen ausgegeben und widerrufen? |
| Support | Welche Fehlerklassen und Eskalationswege sollen ISVs verwenden, wenn XNP/SNP-Testzugänge, beN-Status oder lokale Komponenten nicht erreichbar sind? |

## Demo-Sprechspur

Zulässig:

> NaC zeigt den Immobilienkaufvertrag als primären BPMN-Fluss. Die Quellen
> belegen XNP, XNotar, Grundbuch, Register und Kartenleser als fachliche
> Umgebung. Für eine echte ISV-Integration brauchen wir von BNotK oder Kammer
> einen freigegebenen XNP-/SNP-Testzugang, API-Verträge und klare Grenzen,
> welche Status- und Evidence-Daten ohne Mandatsdaten verarbeitet werden
> dürfen.

Nicht zulässig:

- "NaC hat produktiven XNP/SNP-Zugriff."
- "NaC steuert XNP aus der Cloud."
- "NaC übernimmt Grundbuch- oder Registerinhalte automatisch."
- "NaC speichert Karten-, PIN-, Token-, Dokument- oder Mandatsdaten."

## Arbeitsgrenze für diesen PR

- Keine produktiven XNP-/SNP-Claims.
- Keine Mandatsdaten, keine Registerdaten, keine Grundstücksdaten.
- Keine OCI-, Runtime-, Adapter- oder App-Änderung.
- Nur Demo-Guidance, BPMN-Profil-Sprache und Quellenverweis.
