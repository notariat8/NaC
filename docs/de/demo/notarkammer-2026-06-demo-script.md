# Notarkammer-Demo 2026-06: Skript und Fallbacks

Dieses Skript ist für eine etwa 60-minütige Vorstellung von notariat8 und NaC
bei der Notarkammer vorbereitet. Es zeigt nur öffentliche Referenzen,
Test-/Statusseiten und mandatsdatenfreie Prozessmodelle.

## Demo-Ziel

Die Demo zeigt, dass notarielle Vorgänge nicht als lineare Vier-Schritte-Liste
gedacht werden. notariat8 zeigt stattdessen einen kontrollierten,
editierbaren und prüfbaren Ablauf mit Rollen, Nachweisen, parallelen
Arbeitsanteilen, kritischer Pfad und geschütztem App-Einstieg.

Zentraler fachlicher Punkt für diese Demo: NaC zeigt, wann XNP,
Kartenleser, XNotar, XJustiz, Grundbuch- und Registerpfade im Vorgang
relevant werden. NaC ersetzt diese Systeme nicht. XNP liefert keine
Grundbuchdaten an NaC; Grundbuch- und Registerschritte werden als lokale
XNotar-/XJustiz-Übergaben, Nachweise und menschlich freigegebene Gates
modelliert.

Demo-Gate: Der Login-Flow wird nur fortgesetzt, wenn die Freigabe für diese
Demo-Sitzung vorliegt. Ohne Freigabe wird der Workspace bewusst fail-closed
gezeigt; das ist ein Sicherheitsnachweis, kein Fehlerpfad.

## Vorabprüfung

Vor der Demo diese URLs in einem frischen Browserfenster öffnen:

1. `https://notariat8.de`
2. `https://notariat8.de/prozessmodell.html`
3. `https://app.notariat8.de/healthz`
4. `https://app.notariat8.de/login`
5. `https://app.notariat8.de/workspace`

Erwartung:

- Die öffentliche Seite lädt.
- Das Prozessmodell zeigt den Immobilienkaufvertrag.
- Die App-Health-Seite meldet `ok`.
- Die Login-Seite öffnet eine notariat8-Anmeldung; der Flow wird nur mit
  Freigabe fortgesetzt.
- Der geschützte Arbeitsbereich bleibt ohne freigegebene Sitzung geschlossen.

## 60-Minuten-Ablauf

### 0-5 Minuten: Einstieg auf der öffentlichen Seite

Öffnen: `https://notariat8.de`

Sagen:

- "notariat8 zeigt hier keine Mandatsdaten, sondern freigegebene
  Prozessreferenzen."
- "Die öffentliche Sicht erklärt, was strukturiert und geprüft wird."
- "Der konkrete Arbeitsbereich bleibt geschützt."

Klickfolge:

1. Startseite öffnen.
2. Zum Abschnitt "Vorgänge" gehen.
3. `Immobilienkaufvertrag` auswählen.
4. `Prozessmodell ansehen` öffnen.

### 5-20 Minuten: Immobilienkaufvertrag als Fachprozess

Öffnen: `https://notariat8.de/prozessmodell.html`

Sagen:

- "Der Immobilienkaufvertrag ist kein kurzer Statusflow."
- "Vor und nach der Beurkundung laufen fachliche Prüfungen,
  Behördenrückläufe und Nachweise zusammen."
- "Dauerwerte sind Planwerte, keine amtlichen Durchschnittswerte."

Zeigen:

- `Immobilienkaufvertrag`
- `Dauer und kritischer Pfad`
- `Parallel möglich`
- `Blockiert den kritischen Pfad`

### 20-30 Minuten: Kritischer Pfad und parallele Arbeit

Sagen:

- "Nach der Beurkundung können mehrere Stränge parallel laufen:
  Grundbuch, Finanzierung, Gemeinde, Steuer und Nachweise."
- "Der kritische Pfad bleibt dort blockiert, wo ein Rücklauf für den
  nächsten rechtlichen Schritt gebraucht wird."
- "Wenn ein externer Fachsystemschritt nötig ist, zeigt BPMN die Grenze:
  lokale XNP-/Kartenleser-Readiness, XNotar/XJustiz-Paket oder
  Grundbuch-/Registerportal."
- "Das Ziel ist nicht Automatisierung um jeden Preis, sondern klare
  Sichtbarkeit und Nachvollziehbarkeit."

Zeigen:

- Planwert "Stunden bis Tage" für interne Prüfung.
- Planwert "Wochen" für externe Rückläufe.
- Planwert "Wochen bis Monate" für komplexeren Vollzug.
- Einzelne externe Gates: Eigentumsvormerkung, Löschungsunterlagen,
  gemeindliches Vorkaufsrecht, Unbedenklichkeitsbescheinigung und
  Eigentumsumschreibung.
- Lokales Gate "Karte, XNP und Signaturpfad prüfen".
- XNotar/XJustiz-Schritt als Paket- oder Austauschordner-Nachweis.

Sicherheitslinie sagen:

- "Die Cloud greift XNP nicht direkt an. Der lokale Arbeitsplatz prüft nur
  readiness- und nachweisfähige Statuswerte. Produktive XNP-, Register- oder
  Grundbuchhandlungen bleiben außerhalb dieser Demo."

### 30-40 Minuten: Editierbarer Prozess und XNP/XNotar-Grenze

Öffnen, falls lokal verfügbar:

```text
python scripts/nac.py web
http://127.0.0.1:8766/bpmn/immobilienkaufvertrag/edit
```

Sagen:

- "BPMN ist die Quelle für das Fachmodell."
- "Der Editor ist für Modellpflege vorgesehen, nicht für echte
  Mandatsdokumente."
- "Änderungen laufen über GitHub Pull Requests und Validierung."
- "XNP-nahe Schritte bleiben lokale Arbeitsplatz-Gates. XNotar/XJustiz ist
  die Dateibrücke für Register- und Grundbuchkommunikation, nicht eine
  versteckte Cloud-Automation."

Falls der lokale Editor nicht verfügbar ist, Fallback nutzen:

- `https://notariat8.de/prozessmodell.html`
- GitHub-Referenz nur als technischer Nachweis, nicht als Nutzeransicht.
- Die Aussage bleibt trotzdem gleich: XNP liefert keine Grundbuchdaten an NaC.

### 40-50 Minuten: App-Einstieg und geschützter Arbeitsbereich

Öffnen: `https://app.notariat8.de/login`

Sagen:

- "Die App öffnet den Arbeitsbereich nicht direkt."
- "Vor dem Arbeitsbereich werden Sitzung und Rolle geprüft."
- "Ohne gültige Sitzung bleibt `https://app.notariat8.de/workspace`
  geschlossen."
- "Wir führen den Login nur weiter, wenn das für diese Demo freigegeben ist;
  sonst ist fail-closed das gewollte Ergebnis."

Zeigen:

1. Login-Seite.
2. Nur bei Freigabe: geschützter Startstatus oder Anmeldeschritt.
3. `https://app.notariat8.de/workspace` ohne Sitzung als geschlossene Sicht.

### 50-55 Minuten: Kurzer Vergleichsprozess

Zeigen:

- `Unterschriftsbeglaubigung`

Sagen:

- "Der kurze Vorgang hat andere Risiken und andere Dauerlogik."
- "Das Modell muss pro Usecase passen, nicht pauschal für alle
  notariellen Tätigkeiten gleich aussehen."

### 55-60 Minuten: Abschluss

Sagen:

- "Das ist bewusst noch kein vollständiges Notariatsprodukt."
- "Vorzeigbar ist heute der kontrollierte Pfad: öffentliche Referenz,
  Fachmodell, Prozesssicht, geschützter Einstieg und GitHub-Governance."
- "Der nächste Schritt ist mehr fachliche Tiefe im Prozessmodell und eine
  bessere visuelle Editor-/Kritischer-Pfad-Sicht."

## 5-Minuten-Kurzversion

1. `https://notariat8.de` öffnen.
2. Zum Immobilienkaufvertrag gehen.
3. `https://notariat8.de/prozessmodell.html` zeigen.
4. Dauer, Parallelität und kritischer Pfad erklären.
5. XNP/Kartenleser als lokales Gate und XNotar/XJustiz als Übergabepfad
   erklären.
6. `https://app.notariat8.de/login` öffnen.
7. `https://app.notariat8.de/workspace` ohne Sitzung als geschlossene Sicht zeigen.
8. Abschluss: "Keine Mandatsdaten, kontrollierte Modellpflege, geschützter
   Arbeitsbereich."

## 20-Minuten-Fallback

1. 0-3 Minuten: `https://notariat8.de` öffnen.

   Sagen: "Wir zeigen nur öffentliche Prozessreferenzen. Keine Mandatsdaten,
   keine echten Ausweise, keine echten Urkunden."

2. 3-9 Minuten: `https://notariat8.de/prozessmodell.html` zeigen.

   Sagen: "Der Immobilienkaufvertrag braucht Dauerlogik, Parallelität,
   kritischen Pfad und fachliche Gates."

3. 9-13 Minuten: XNP lokal als Systemgrenze erklären.

   Sagen: "XNP, Kartenleser, SAK lite, secureFramework, Rolle und
   Amtstätigkeitskontext werden am lokalen Arbeitsplatz geprüft. NaC startet
   hier keine produktive XNP-Handlung."

4. 13-16 Minuten: XNotar/XJustiz als Übergabegrenze erklären.

   Sagen: "Register- und Grundbuchkommunikation bleibt Paket-,
   Austauschordner- oder Portalgrenze. Wir öffnen keine echten Pakete,
   Registerdaten oder Grundstücksdaten."

5. 16-18 Minuten: `https://app.notariat8.de/login` zeigen.

   Sagen: "Login nur bei Demo-Freigabe. Ohne Freigabe wechseln wir direkt zu
   `https://app.notariat8.de/workspace` und zeigen fail-closed."

6. 18-20 Minuten: Abschluss.

   Sagen: "NaC zeigt BPMN, Evidence und Gate. Die Fachsysteme bleiben
   sichtbar begrenzt; es gibt keine produktive Register-, Grundbuch- oder
   XNP-Behauptung."

## Fallbacks

| Risiko | Fallback |
| --- | --- |
| Öffentliche Seite lädt langsam | Lokale Kopie oder bereits geöffneter Browser-Tab mit `https://notariat8.de/prozessmodell.html`. |
| App-Login ist langsam | Direkt `https://app.notariat8.de/workspace` zeigen und Fail-Closed erklären. |
| Identitätsanbieter braucht zu lange | Stop-Line verwenden: "Die externe Anmeldung ist nicht Teil der fachlichen Prozessdemo; der geschlossene Arbeitsbereich ist hier der relevante Sicherheitsnachweis." |
| Login-Flow ist nicht freigegeben | Keinen Login versuchen; direkt `https://app.notariat8.de/workspace` fail-closed zeigen. |
| Lokaler BPMN-Editor ist nicht verfügbar | Öffentliche Prozessmodellseite zeigen und GitHub-PR/Validatoren nur kurz als Governance-Nachweis erklären. |
| XNP oder Kartenleser ist lokal nicht verfügbar | Keine Live-XNP-Aktion zeigen; den BPMN-Gate und den XNP/XNotar-Demo-Kontrakt erklären. |
| Live-DNS oder Netzwerk instabil | Keine Live-Neukundenanlage zeigen; nur bestehende Readiness-/DNS-Statusseite verwenden. |

## Stop-Lines

- Wenn Login oder Identitätsprüfung länger als zwei Minuten dauert, nicht
  debuggen. Auf den geschützten Workspace und den Prozessviewer wechseln.
- Wenn keine Login-Freigabe vorliegt, den Login-Flow nicht fortsetzen; der
  geschlossene Workspace ist dann die Demo-Aussage.
- Wenn ein Link JSON statt HTML zeigt, abbrechen und über den vorgesehenen
  Button-Pfad starten.
- Wenn eine Seite interne technische Begriffe zeigt, nicht weiter erklären,
  sondern auf die öffentliche Prozessmodellseite zurückgehen.
- Keine echten Mandatsdaten, keine echten Ausweise, keine echten Urkunden und
  keine produktiven Register- oder Grundbuchhandlungen zeigen.
- Keine Behauptung, dass NaC Grundbuchdaten direkt aus XNP erhält.
- Keine produktive Behauptung zu XNP-, XNotar-, XJustiz-, Register- oder
  Grundbuchautomation.

## Vorführbare Kernaussagen

- notariat8 ist notariatszentriert.
- Der Immobilienkaufvertrag braucht parallele Arbeit und kritischer Pfad.
- Die Dauerangaben sind editierbare Planwerte.
- Die öffentliche Sicht enthält keine Mandatsdaten.
- XNP, Kartenleser, XNotar und XJustiz werden als sichtbare Fachsystemgrenzen
  im Prozess gezeigt.
- Die App öffnet den Arbeitsbereich erst nach Sicherheitsprüfung.
- GitHub Protected PRs sichern Modelländerungen nachvollziehbar ab.
