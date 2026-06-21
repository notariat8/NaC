# Notarkammer-Demo: XNP-Quellenmatrix

Stand: 2026-06-21

Diese Matrix ist ein PR-only Demo-Artefakt. Sie übersetzt öffentlich
belegbare Aussagen zu XNP, XNotar, Grundbuch, Register und Kartenlesern in
Demo-Sätze für NaC. Sie ist keine technische Kopplungszusage und kein
Produktivkonzept.

Die Demo-Regel bleibt bewusst eng: NaC zeigt externe Zugriffspunkte in BPMN,
prüft nur redigierte Nachweise und arbeitet ohne Mandatsinhalte. Für den
Vortrag gilt: keine Mandatsdaten, keine produktive XNP-Anbindung, keine direkte XNP-zu-NaC-Kopplung.
Jeder XNP-/XNotar-/Register-/Grundbuch-/Kartenleser-Schritt ist nur ein
externer Zugriffspunkt im Prozessbild.

## Demo-Aussagen-Matrix

| ID | Aussage | Quelle | Was NaC in der Demo zeigen darf | Was NaC nicht behaupten darf |
| --- | --- | --- | --- | --- |
| SRC-XNP-001 | XNP ist die Basisanwendung der Bundesnotarkammer und enthält Module wie UVZ, VVZ, notarielle Onlineverfahren, beN, Dokumente mit PDF-Viewer und Signaturmappe, Benutzerverwaltung und Kartenverwaltung. | NotarNet XNP: https://notarnet.de/produkte/xnp | NaC darf XNP als externen Zugriffspunkt und lokale notarielle Arbeitsumgebung im BPMN markieren, etwa als Gate für Dokument-, Signatur-, beN- oder Kartenverwaltungsnähe. | NaC darf nicht behaupten, dass XNP ein NaC-Backend ist, dass NaC XNP fernsteuert oder dass eine produktive direkte Verbindung besteht. |
| SRC-XNOTAR-001 | XNotar unterstützt den elektronischen Rechtsverkehr in Register- und Grundbuchangelegenheiten sowie weitere Fachmodule. | NotarNet XNotar: https://notarnet.de/produkte/xnotar | NaC darf XNotar als fachlichen externen Zugriffspunkt für Grundbuch- und Registerpfade in BPMN zeigen und den Status als redigierte Nutzerbestätigung erfassen. | NaC darf nicht behaupten, dass XNotar-Daten automatisch in NaC einlaufen oder dass NaC Grundbuch- oder Registervorgänge selbst an die Stelle der Fachanwendung tritt. |
| SRC-XNP-BNOTK-001 | Die BNotK-Onlinehilfe beschreibt XNP als Basisanwendung, über deren Module Anwendungen der Bundesnotarkammer und elektronischer Rechtsverkehr zugänglich werden; XNP-XNotar umfasst Grundbuch und Handelsregister. | BNotK Onlinehilfe XNP Basisanwendung: https://onlinehilfe.bnotk.de/technischer-bereich/systembetreuer/xnp-die-basisanwendung-der-bnotk.html | NaC darf in der Demo erklären, dass XNP/XNotar zur fachlichen Umgebung gehört und NaC nur BPMN-Orchestrierung, Auditstatus und Nachweispunkte zeigt. | NaC darf nicht behaupten, dass die öffentliche Hilfe eine direkte NaC-Schnittstelle, Freigabe für Live-Betrieb oder produktive XNP-Anbindung belegt. |
| SRC-GRUNDBUCH-001 | Die BNotK-Onlinehilfe zeigt für Grundbuchanträge Schritte wie Grunddaten, Grundstücke, Anträge, Beteiligte, Dokumente, Validieren, Vorbereitung, Signieren, Versand vorbereiten und Versenden via beN. | BNotK Schritte Grundbuchantrag: https://onlinehilfe.bnotk.de/einrichtungen/notarnet/xnotar/einstiegshilfen/alle-schritte-eines-grundbuchantrags-auf-einen-blick.html | NaC darf diese Schritte als externen Grundbuch-Zugriffspunkt, Wartepunkt und Evidence-Gate im BPMN sichtbar machen. | NaC darf nicht behaupten, dass Grundbuchinhalte direkt aus XNP an NaC geliefert werden oder dass NaC den Versand selbst ausführt. |
| SRC-REGISTER-001 | Die BNotK-Onlinehilfe zeigt für Registeranmeldungen Schritte wie Grunddaten, Rechtsträger, Anmeldefälle, Beteiligte, Dokumente, Validieren, Vorbereitung abschließen, Signieren, Versand vorbereiten und Versenden. | BNotK Schritte Registeranmeldung: https://onlinehilfe.bnotk.de/einrichtungen/notarnet/xnotar/einstiegshilfen/alle-schritte-einer-registeranmeldung-auf-einen-blick.html | NaC darf Registeranmeldungen als externen Register-Zugriffspunkt im BPMN modellieren und lokale Statusbestätigung als Nachweis führen. | NaC darf nicht behaupten, dass NaC Registerdaten automatisiert bezieht, Registeranmeldungen produktiv absendet oder die fachliche Prüfung ersetzt. |
| SRC-CARDREADER-001 | Die BNotK nennt getestete REINER SCT-Kartenleser und weist bei anderen Geräten mindestens auf Sicherheitsklasse 3, Display und eigene PIN-Tastatur hin. | BNotK Kartenlesegeräte: https://onlinehilfe.bnotk.de/einrichtungen/zertifizierungsstelle/hinweis-zu-kartenlesegeraeten.html | NaC darf Kartenleserbereitschaft als lokalen BPMN-Vorbehalt oder Nachweispunkt zeigen, ohne PIN, Kartendaten oder Mandatsinhalte zu speichern. | NaC darf nicht behaupten, Kartenleser, Signaturkarten oder PIN-Eingaben aus NaC heraus zu steuern oder auszulesen. |

## Guardrails für Demo-Sprache

- Zulässig: "NaC zeigt in BPMN, an welcher Stelle XNP, XNotar, Grundbuch,
  Register oder Kartenleser fachlich relevant werden."
- Zulässig: "Der Nachweis wird redigiert erfasst; NaC speichert keine
  Mandatsdaten, keine PINs, keine Signaturkartendaten und keine Rohdokumente."
- Zulässig: "Der eigentliche Fachsystemschritt bleibt in der dafür
  vorgesehenen notariellen Arbeitsumgebung."
- Nicht zulässig: eine direkte technische Produktivkopplung, eine
  automatisierte Datenübernahme aus XNP/XNotar oder ein NaC-gesteuerter
  Versand an Grundbuchamt oder Registergericht.
- Nicht zulässig: echte Vorgangsdaten, Namen, Aktenbezüge, PINs, Tokens,
  lokale Pfade oder Betriebsdetails in Demo-Unterlagen.

## Kurzform für den Termin

NaC ist in dieser Demo der BPMN- und Audit-Rahmen. XNP, XNotar, Grundbuch,
Register und Kartenleser erscheinen als fachliche externe Zugriffspunkte. Die
öffentlichen Quellen belegen, welche Fachschritte es gibt; sie belegen keine
produktive NaC-Kopplung.
