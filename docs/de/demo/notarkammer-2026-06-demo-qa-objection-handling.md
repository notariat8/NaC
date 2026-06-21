# Notarkammer-Demo 2026-06: Q&A und Einwandbehandlung

Status: Protected-PR-fähiges Sprecherblatt für die Live-Demo. Dieses Dokument
ergänzt das [Live-Runbook](notarkammer-2026-06-live-demo-runbook.md), den
[XNP-Demo-Kontrakt](notarkammer-xnp-demo-contract.md) und die
[Quellenmatrix zu Vollzug und Dauerlogik](../research/notarkammer-demo-vollzug.md).

Scope: Demo-Q&A, Einwandbehandlung und Sicherheitsgrenzen. Keine
Runtime-Änderung, keine Infrastrukturaktion, keine produktive Einreichung,
keine Anbieter- oder Betreiberdetails, keine Secrets und keine Mandatsdaten.
Die Aussagen sind Demo-Orientierung und keine Rechtsberatung.

## Kurzantworten

| Frage oder Einwand | Präzise Antwort |
| --- | --- |
| Was zeigt NaC live? | NaC zeigt den notariellen Ablauf als BPMN-Modell mit sichtbaren Fachsystemgrenzen, Evidence-Gates, Rücklaufstatus und kritischem Pfad. Live gezeigt werden öffentliche Prozesssicht, Demo-Modell, geschützter Einstieg oder fail-closed Workspace und die Sprecherlinie aus dem Runbook. Es werden keine echten Akten, Urkunden, Registerinhalte, Grundstücksdaten oder Zugangsdaten gezeigt. |
| Was macht XNP in der Demo? | XNP ist die lokale Fachsystemgrenze für XNP-nahe Aufgaben wie Readiness, Rolle, Amtstätigkeitskontext und UVZ-/VVZ-nahe Schritte. NaC behauptet nicht, XNP aus der Cloud zu steuern. XNP liefert keine Grundbuchdaten an NaC. |
| Wird produktiv eingereicht? | Nein. Die Demo zeigt Vorbereitung, Nachweisfrage, Gate-Status und Übergabegrenzen. Es wird keine Register- oder Grundbucheinreichung produktiv ausgelöst, kein Versand gestartet und kein externer Fachsystemprozess automatisiert. |
| Wo läuft der Kartenleser? | Der Kartenleser läuft am freigegebenen lokalen Arbeitsplatz im Benutzer- und Amtstätigkeitskontext. NaC modelliert den Kartenleserpfad als lokales Readiness-Gate und übernimmt nur redigierte Evidence wie Status, Zeitpunkt, Rolle und Prüfergebnis. PINs, Schlüssel, Tokens und Rohdaten gehören nicht in NaC. |
| Wie werden Grundbuch- und Register-Rückläufe behandelt? | Rückläufe bleiben fachliche externe Ereignisse. In NaC werden sie als BPMN-Gate, Wiedervorlage, Nachweisfrage und redigierte Evidence modelliert. Bei Zwischenverfügung, fehlender Bestätigung oder widersprüchlichem Rücklauf bleibt der nächste Schritt blockiert oder geht in manuelle Prüfung. |
| Was ist der kritische Pfad? | Der kritische Pfad ist der längste blockierende fachliche Rücklauf, nicht die Oberfläche. Beim Immobilienkaufvertrag sind das typischerweise Grundbuch-, Finanzierungs-, Gemeinde-, Steuer- oder Löschungsrückläufe. Bei Registervorgängen sind Signatur, Freigabe, Übergabe und Registerrücklauf die zentralen Gates. Dauerangaben bleiben Planwerte, keine Zusage. |
| Was ist noch nicht produktiv? | Nicht produktiv sind produktive Einreichung, produktive XNP-/XNotar-Automation, direkte Grundbuchdatenübernahme, echte Mandatsbearbeitung, echte Zugangsdaten und verbindliche Kosten- oder Rechtsauskünfte. Die Demo ist ein prüfbarer Ablauf- und Evidence-Nachweis. |
| Wie bleiben Mandatsdaten geschützt? | Die Demo verwendet synthetische oder öffentliche Modellinformationen. Mandatsdaten, Personenangaben, Urkunden, Ausweise, Grundstücksdaten, Registerinhalte, Secrets und Tokens werden nicht gezeigt und nicht in Q&A oder Screenshots übernommen. Evidence wird redigiert und auf Status, Hash, Zeitpunkt, Rolle und Prüfergebnis begrenzt. |
| Was passiert, wenn Login nicht klappt? | Nicht live debuggen. Den geschlossenen Workspace als fail-closed Sicherheitsnachweis erklären und auf das öffentliche Prozessmodell sowie das Runbook-Fallback wechseln. Ohne ausdrückliche Demo-Freigabe wird der Login-Flow nicht fortgesetzt. |
| Was passiert, wenn XNP oder Kartenleser nicht verfügbar ist? | Keine produktive XNP-Aktion starten. Das lokale Gate als `manual_review` oder `blocked` markieren und erklären, dass NaC ohne lokale Readiness keine Folgeaktion freigibt. Die Demo kann mit BPMN-Modell, Screenshots oder Sprecherlinie fortgesetzt werden. |
| Was passiert, wenn die Website nicht erreichbar ist? | Nicht live reparieren. Bereits geladene Tabs, freigegebene Screenshots oder die lokale Prozessmodell-Erklärung verwenden. Die Aussage bleibt: NaC macht Ablauf, Fachsystemgrenzen, Rückläufe und kritischen Pfad sichtbar. |

## Einwandbehandlung

### "Ist das schon ein vollständiges Notariatsprodukt?"

Nein. Die Demo zeigt einen kontrollierten Ausschnitt: BPMN, Evidence-Gates,
Fachsystemgrenzen, Fallbacks und sichere Sprecherlinien. Sie behauptet keine
vollständige Produktivfähigkeit, keine direkte Fachsystemautomation und keine
rechtliche Bewertung eines konkreten Vorgangs.

### "Warum wird XNP nicht direkt durch NaC gesteuert?"

Weil die Demo die lokale Fachsystemgrenze respektiert. XNP, Kartenleser,
Signaturpfad und Amtstätigkeitskontext gehören an den freigegebenen
Arbeitsplatz. NaC zeigt, wann diese Voraussetzung fachlich relevant ist, und
blockiert den nächsten BPMN-Schritt, wenn die redigierte Evidence fehlt.

### "Wie wird aus Rücklauf wieder Arbeit?"

Ein Rücklauf wird nicht als unsichtbare Automation behandelt, sondern als
Nachweisfrage: Was kam zurück, wer hat geprüft, welche Entscheidung folgt und
welches Gate bleibt offen oder wird freigegeben? Für Grundbuch und Register
werden Eingangsbestätigung, Zwischenverfügung, Eintragung, fehlende Anlage oder
widersprüchliche Rückmeldung als separate Gate-Zustände erklärbar.

### "Warum ist der kritische Pfad für die Kammer relevant?"

Die Demo macht sichtbar, welche Arbeit sofort vorbereitet werden kann und
welcher externe Rücklauf den nächsten Schritt tatsächlich blockiert. Damit wird
die Notariatsarbeit nicht auf eine Maske reduziert, sondern als fachlich
prüfbarer Vollzugspfad mit Verantwortlichkeiten, Nachweisen und Wartegründen
erklärbar.

### "Wo ist die Sicherheitsgrenze?"

Die Grenze liegt vor Mandatsdaten, produktiven Fachsystemhandlungen,
Zugangsdaten, lokalen Schlüsseln und Rohdokumenten. NaC darf Demo-Status und
redigierte Evidence zeigen; echte Inhalte, Secrets, Karten-PINs,
Registerdaten, Grundstücksdaten und Betreiberdetails bleiben außerhalb der
Demo.

## Sprecher-Stop-Lines

- "Wir zeigen den Ablauf und die Nachweisgrenze, keine produktive Einreichung."
- "XNP bleibt lokal; XNP liefert keine Grundbuchdaten an NaC."
- "Ohne lokale Readiness oder Evidence bleibt das Gate blockiert."
- "Wir debuggen nicht live, sondern wechseln auf den freigegebenen Fallback."
- "Die Demo nutzt keine Mandatsdaten und ist keine Rechtsberatung."

## Quellen und Anschlussdokumente

- [Live-Runbook](notarkammer-2026-06-live-demo-runbook.md)
- [Demo-Skript](notarkammer-2026-06-demo-script.md)
- [Demo-Preflight](notarkammer-2026-06-demo-preflight.md)
- [XNP-Demo-Kontrakt](notarkammer-xnp-demo-contract.md)
- [Quellenmatrix: Vollzug, Dauerlogik und kritischer Pfad](../research/notarkammer-demo-vollzug.md)
