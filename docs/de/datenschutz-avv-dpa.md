# Datenschutz AVV DPA

## Zweck

Diese Sektion beschreibt, wann NaC für OpenAI-basierte Funktionen einen
Auftragsverarbeitungsvertrag (AVV) bzw. ein Data Processing Addendum (DPA)
braucht und welche Nachweise vor Pilot- oder Produktivbetrieb vorliegen müssen.

Hinweis: Dies ist ein operativer Governance-Leitfaden und ersetzt keine
Rechtsberatung.

## Quellenstand

Geprüft am 2026-05-15:

- OpenAI Data Processing Addendum v.010126:
  `https://cdn.openai.com/pdf/openai-data-processing-addendum.pdf`
- Offizielle OpenAI-Seite zum Zusatz zur Datenverarbeitung mit PDF-Download
  und Link zum Ausführen der Datenverarbeitungsvereinbarung:
  `https://openai.com/de-DE/policies/data-processing-addendum/`
- Gesellschaft für Datenschutz, "ChatGPT, Datenschutz und
  Auftragsverarbeitungsvertrag":
  `https://gesellschaft-datenschutz.de/chatgpt-und-auftragsverarbeitung/`

Die OpenAI-DPA beschreibt OpenAI für den betroffenen Leistungsrahmen als
Processor/Auftragsverarbeiter, regelt Weisungen, Unterauftragsverarbeiter,
Rückgabe/Löschung, internationale Transfers und die vom Kunden gesteuerten
Konfigurationen. Der deutsche Beitrag stellt heraus, dass die
datenschutzrechtliche Rolle vom Lizenzmodell abhängt und für Unternehmens-
bzw. API-Nutzung eine AVV/DPA-Prüfung erforderlich ist.

Operativer Hinweis: Der Vertragsabschluss erfolgt nicht über die im Repo
abgelegte PDF-Referenz, sondern über den offiziellen OpenAI-Policy-Pfad. Der
dort am Ende verlinkte Schritt "Datenverarbeitungsvereinbarung ausführen" ist
der zu prüfende Abschluss-/AVV-Pfad. Ergebnisdokumente, Organisations-IDs und
Accountdaten werden nicht in diesem Repository gespeichert.

## NaC Grundsatz

- Lokale Plugins und lokale Workflows sind der Standardpfad, solange kein AVV
  bzw. keine DPA-Freigabe dokumentiert ist.
- Personenbezogene Daten, Urkundendaten, Registerinhalte, Berufsgeheimnisse,
  Kartenwerte, PINs, private Schlüssel und Mandatsinhalte dürfen nicht ohne
  freigegebenen Verarbeitungspfad an externe KI-Dienste gesendet werden.
- Auch bei vorhandener DPA gilt Datensparsamkeit: IDs, Platzhalter,
  gekürzte Sachverhalte und synthetische Testdaten haben Vorrang.
- Vertragsdokumente, Account-IDs, Organisationsdaten, Auditberichte und echte
  Kundendaten werden nicht im Git-Repo gespeichert. Im Repo liegen nur
  Metadaten, Checklisten, Hashes oder Verweise auf das freigegebene
  Dokumentenmanagement.

## Lizenz- und Kanalentscheidung

| Kanal | AVV/DPA-Regel | NaC-Freigabe |
| --- | --- | --- |
| Free oder Pro | Nicht für personenbezogene NaC-/Notariatsdaten verwenden. | Nicht freigegeben. |
| Team, Enterprise oder API | DPA/AVV, Konfiguration und Zweckbindung prüfen. | Nur nach documented approval. |
| Public GPT Store | Datenschutzlink, Terms, Action-Boundary und DPA-Bedarf je Action prüfen. | Separate Release-Freigabe. |
| Workspace GPT/App | Tenant, Rollen, Retention, Training/Data-Sharing und DPA prüfen. | Pilot-Freigabe erforderlich. |
| Lokales Plugin | Kein externer KI-Transfer, sofern rein lokal. | Standardpfad für sensible Gates. |

## Pflichtartefakte vor Verarbeitung

- unterschriebene bzw. wirksam akzeptierte DPA/AVV-Version
- Nachweis, dass der Abschluss über den offiziellen OpenAI-DPA-/AVV-Pfad
  angestossen oder abgeschlossen wurde
- genaue OpenAI-Produkt-/Lizenzzuordnung
- Zweck der Verarbeitung und dokumentierte Kundenweisung
- Kategorien personenbezogener Daten und betroffener Personen
- Entscheidung, ob besondere Kategorien oder Berufsgeheimnisse ausgeschlossen
  oder gesondert freigegeben sind
- Konfiguration für Datenverwendung, Retention, Löschung und Zugriff
- Subprocessor-/Unterauftragsverarbeiter-Stand mit Prüfdatum
- Drittlandtransfer-/SCC-/Transfer-Impact-Bewertung, soweit erforderlich
- Incident-, Betroffenenrechte-, Rückgabe- und Löschprozess
- Review durch Datenschutz, fachlichen Owner und technischen Owner

## NaC PR-Gate

Ein PR, der OpenAI-gestützte Verarbeitung personenbezogener Daten ermöglicht,
ist erst mergefähig, wenn:

1. `policies/data-protection-policy.yaml` eingehalten ist.
2. Der Zielkanal in `docs/de/gpt-marketplace-operating-model.md` klassifiziert
   ist.
3. Diese AVV/DPA-Sektion als Checklistenreferenz verlinkt ist.
4. Kein echtes Vertragsdokument, keine Organisations-ID und kein Account-Secret
   im Diff liegt.
5. Ein Issue oder PR-Kommentar die Freigabeentscheidung dokumentiert.
6. `python scripts/nac.py doctor --profile strict` erfolgreich läuft.

## Mindestentscheidung je Plugin oder Workflow

Jedes Plugin, jede Action und jeder Workflow muss vor einem Pilot mit
personenbezogenen Daten eine kurze Entscheidung enthalten:

| Frage | Entscheidung |
| --- | --- |
| Werden personenbezogene Daten extern verarbeitet? | Ja/Nein |
| Ist OpenAI nur Processor/Auftragsverarbeiter für diesen Kanal? | Ja/Nein/Ungeklärt |
| Liegt eine wirksame DPA/AVV-Freigabe vor? | Ja/Nein |
| Werden Berufsgeheimnisse oder besondere Kategorien ausgeschlossen? | Ja/Nein |
| Welche Datensparsamkeitsmaßnahme gilt? | IDs/Platzhalter/Synthetik/Redaktion |
| Wo liegt der externe Vertragsnachweis? | Verweis, kein Dokument im Repo |

## Beziehung zu bestehenden NaC-Dokumenten

- `docs/de/security-and-dsgvo.md`: allgemeine Repo-Schutzregeln.
- `docs/de/avv-checkliste-eventlock-saas.md`: Function8/EventLock-spezifische
  AVV-Checkliste.
- `docs/de/gpt-marketplace-operating-model.md`: Kanalentscheidung für GPT
  Store, Actions, Workspace Apps und lokale Plugins.
- `policies/data-protection-policy.yaml`: verbindliche Datenschutz- und
  Secret-Regeln.
