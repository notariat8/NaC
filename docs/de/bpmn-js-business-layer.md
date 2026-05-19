# BPMN-js Business Layer

Status: Usecase-BPMN und lokale Speicherfläche ergänzt am 2026-05-19

## Entscheidung

NaC soll den Business Layer nicht als Python-Code-first modellieren. Die
fachliche Prozessquelle wird BPMN 2.0. `bpmn-js` ist dafür die geplante
visuelle Bearbeitungsschicht, weil Fachnutzer Prozesse sehen und ändern können,
ohne XML oder Python zu schreiben.

Python bleibt trotzdem wichtig: Es prüft, ob das visuell bearbeitete Modell
zulässig, vollständig, datenschutzkonform und ausführbar anschließbar ist.

## Zielbild Für Fachnutzer

1. Ein Notariat öffnet einen Vorgang oder Prozess im BPMN-Editor.
2. Der Editor zeigt nur erlaubte Bausteine: Aufgabe, Entscheidung, Freigabe,
   Nachweis, lokaler Plugin-Schritt.
3. Ein Eigenschaftenbereich zeigt verständliche NaC-Felder: Rolle,
   Ausführungskanal, Datenklasse, Freigabe, Nachweis, Plugin und KG-Referenz.
4. Nach dem Speichern prüft Python das BPMN-Modell.
5. Änderungen laufen als Pull Request mit Diff, Quality Gate und Freigabe.

## Warum Nicht Alles In bpmn-js

`bpmn-js` ist der Editor, nicht die Governance-Schicht. Es soll Prozesse
bearbeitbar machen, aber nicht allein entscheiden, ob ein Prozess zulässig ist.
Diese Entscheidung bleibt bei Git, Python-Validatoren, Datenschutzregeln,
Review und menschlicher Freigabe.

## Aktueller Repo-Stand

- Das NaC-Modellprofil liegt in [bpmn/nac-moddle.json](../../bpmn/nac-moddle.json).
- Die fachliche Beschreibung liegt in [bpmn/nac-bpmn-profile.md](../../bpmn/nac-bpmn-profile.md).
- Für jeden Usecase unter [usecases/](../../usecases) liegt ein
  bpmn-js-taugliches BPMN-Modell vor. Der kanonische Immobilienkaufvertrag
  bleibt unter [bpmn/immobilienkaufvertrag.bpmn](../../bpmn/immobilienkaufvertrag.bpmn);
  die weiteren Usecase-Modelle liegen unter [bpmn/usecases/](../../bpmn/usecases).
- `nac:channel` dokumentiert, in welcher Form ein Schritt ausgeführt wird,
  etwa persönlich, per E-Mail, per Post/Fax, digital signiert, über XNP lokal
  oder über ein Register-/Grundbuchportal.
- Die deterministische Prüfung liegt in
  [scripts/validate_bpmn_models.py](../../scripts/validate_bpmn_models.py).
- Die Generierung liegt in
  [scripts/generate_usecase_bpmn.py](../../scripts/generate_usecase_bpmn.py).
- Der Workflow-Vertrag liegt in
  [workflows/contracts/bpmn-js-editor.contract.json](../../workflows/contracts/bpmn-js-editor.contract.json).
- Die lokale Browserfläche für grafische Ausgaben liegt in
  [docs/de/lokaler-webserver.md](lokaler-webserver.md).

## Fachliche Quellen

Die Usecase-BPMN-Modelle sind bewusst ein prüfbarer Arbeitsstand. Sie verbinden
die usecase-lokalen KGs mit zwei externen BNotK-Ankern:

- Die BNotK beschreibt die XNP-Integration als lokale REST-Schnittstelle auf
  `localhost`, die Login-Informationen, Amtstätigkeit und bei Login-Funktionen
  einen pro Installation konfigurierten API-Key betrifft.
- Die BNotK beschreibt Online-Verfahren im Gesellschaftsrecht mit
  Vorgangseingang, E-Mail-Benachrichtigung, Sachbearbeiter/Aktenzeichen,
  Bearbeiten/Exportieren/Anlegen sowie Videokonferenz-bezogenen Schritten.

Deshalb modelliert NaC XNP-nahe Schritte als lokalen, nachweispflichtigen
Service Task und Online-GmbH-Schritte mit `notary_app`, `video` und
`qualified_e_signature`. Das ersetzt keine notarielle Rechtsprüfung und
speichert keine Mandatswerte.

## Zusammenspiel Mit KG

BPMN und KG haben verschiedene Aufgaben:

| Ebene | Frage | Quelle |
| --- | --- | --- |
| BPMN | Was passiert wann? | [bpmn/](../../bpmn) |
| KG | Welche Angaben, Dokumente, Entscheidungen und Nachweise sind offen? | [usecases/](../../usecases) |
| Python | Ist das Modell zulässig und prüfbar? | [scripts/](../../scripts), [src/](../../src) |

Ein BPMN-Schritt kann über `nac:kgRef` auf einen usecase-lokalen Knowledge
Graph verweisen. So bleibt der Ablauf visuell editierbar, während fachliche
Detailfragen im KG kontrolliert bleiben.

## Nächste Schritte

1. bpmn-js-Palette und NaC-Properties-Panel weiter einschränken.
2. BPMN-Diff und Validierungsbericht in Pull Requests sichtbar machen.
3. Fachliche Reviewrunden je Usecase gegen echte Kanzleipraxis durchführen.
4. Aus BPMN und KG gemeinsam sichere Formular- und Checklisten-Sichten erzeugen.
