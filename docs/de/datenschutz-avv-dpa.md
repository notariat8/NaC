# Datenschutz AVV DPA

## Zweck

Diese Sektion beschreibt, wann NoC fuer OpenAI-basierte Funktionen einen
Auftragsverarbeitungsvertrag (AVV) bzw. ein Data Processing Addendum (DPA)
braucht und welche Nachweise vor Pilot- oder Produktivbetrieb vorliegen muessen.

Hinweis: Dies ist ein operativer Governance-Leitfaden und ersetzt keine
Rechtsberatung.

## Quellenstand

Geprueft am 2026-05-15:

- OpenAI Data Processing Addendum v.010126:
  `https://cdn.openai.com/pdf/openai-data-processing-addendum.pdf`
- Offizielle OpenAI-Seite zum Zusatz zur Datenverarbeitung mit PDF-Download
  und Link zum Ausfuehren der Datenverarbeitungsvereinbarung:
  `https://openai.com/de-DE/policies/data-processing-addendum/`
- Gesellschaft fuer Datenschutz, "ChatGPT, Datenschutz und
  Auftragsverarbeitungsvertrag":
  `https://gesellschaft-datenschutz.de/chatgpt-und-auftragsverarbeitung/`

Die OpenAI-DPA beschreibt OpenAI fuer den betroffenen Leistungsrahmen als
Processor/Auftragsverarbeiter, regelt Weisungen, Unterauftragsverarbeiter,
Rueckgabe/Loeschung, internationale Transfers und die vom Kunden gesteuerten
Konfigurationen. Der deutsche Beitrag stellt heraus, dass die
datenschutzrechtliche Rolle vom Lizenzmodell abhaengt und fuer Unternehmens-
bzw. API-Nutzung eine AVV/DPA-Pruefung erforderlich ist.

Operativer Hinweis: Der Vertragsabschluss erfolgt nicht ueber die im Repo
abgelegte PDF-Referenz, sondern ueber den offiziellen OpenAI-Policy-Pfad. Der
dort am Ende verlinkte Schritt "Datenverarbeitungsvereinbarung ausfuehren" ist
der zu pruefende Abschluss-/AVV-Pfad. Ergebnisdokumente, Organisations-IDs und
Accountdaten werden nicht in diesem Repository gespeichert.

## NoC Grundsatz

- Lokale Plugins und lokale Workflows sind der Standardpfad, solange kein AVV
  bzw. keine DPA-Freigabe dokumentiert ist.
- Personenbezogene Daten, Urkundendaten, Registerinhalte, Berufsgeheimnisse,
  Kartenwerte, PINs, private Schluessel und Mandatsinhalte duerfen nicht ohne
  freigegebenen Verarbeitungspfad an externe KI-Dienste gesendet werden.
- Auch bei vorhandener DPA gilt Datensparsamkeit: IDs, Platzhalter,
  gekuerzte Sachverhalte und synthetische Testdaten haben Vorrang.
- Vertragsdokumente, Account-IDs, Organisationsdaten, Auditberichte und echte
  Kundendaten werden nicht im Git-Repo gespeichert. Im Repo liegen nur
  Metadaten, Checklisten, Hashes oder Verweise auf das freigegebene
  Dokumentenmanagement.

## Lizenz- und Kanalentscheidung

| Kanal | AVV/DPA-Regel | NoC-Freigabe |
| --- | --- | --- |
| Free oder Pro | Nicht fuer personenbezogene NoC-/Notariatsdaten verwenden. | Nicht freigegeben. |
| Team, Enterprise oder API | DPA/AVV, Konfiguration und Zweckbindung pruefen. | Nur nach documented approval. |
| Public GPT Store | Datenschutzlink, Terms, Action-Boundary und DPA-Bedarf je Action pruefen. | Separate Release-Freigabe. |
| Workspace GPT/App | Tenant, Rollen, Retention, Training/Data-Sharing und DPA pruefen. | Pilot-Freigabe erforderlich. |
| Lokales Plugin | Kein externer KI-Transfer, sofern rein lokal. | Standardpfad fuer sensible Gates. |

## Pflichtartefakte vor Verarbeitung

- unterschriebene bzw. wirksam akzeptierte DPA/AVV-Version
- Nachweis, dass der Abschluss ueber den offiziellen OpenAI-DPA-/AVV-Pfad
  angestossen oder abgeschlossen wurde
- genaue OpenAI-Produkt-/Lizenzzuordnung
- Zweck der Verarbeitung und dokumentierte Kundenweisung
- Kategorien personenbezogener Daten und betroffener Personen
- Entscheidung, ob besondere Kategorien oder Berufsgeheimnisse ausgeschlossen
  oder gesondert freigegeben sind
- Konfiguration fuer Datenverwendung, Retention, Loeschung und Zugriff
- Subprocessor-/Unterauftragsverarbeiter-Stand mit Pruefdatum
- Drittlandtransfer-/SCC-/Transfer-Impact-Bewertung, soweit erforderlich
- Incident-, Betroffenenrechte-, Rueckgabe- und Loeschprozess
- Review durch Datenschutz, fachlichen Owner und technischen Owner

## NoC PR-Gate

Ein PR, der OpenAI-gestuetzte Verarbeitung personenbezogener Daten ermoeglicht,
ist erst mergefaehig, wenn:

1. `policies/data-protection-policy.yaml` eingehalten ist.
2. Der Zielkanal in `docs/de/gpt-marketplace-operating-model.md` klassifiziert
   ist.
3. Diese AVV/DPA-Sektion als Checklistenreferenz verlinkt ist.
4. Kein echtes Vertragsdokument, keine Organisations-ID und kein Account-Secret
   im Diff liegt.
5. Ein Issue oder PR-Kommentar die Freigabeentscheidung dokumentiert.
6. `python scripts/quality_gate.py --profile strict` erfolgreich laeuft.

## Mindestentscheidung je Plugin oder Workflow

Jedes Plugin, jede Action und jeder Workflow muss vor einem Pilot mit
personenbezogenen Daten eine kurze Entscheidung enthalten:

| Frage | Entscheidung |
| --- | --- |
| Werden personenbezogene Daten extern verarbeitet? | Ja/Nein |
| Ist OpenAI nur Processor/Auftragsverarbeiter fuer diesen Kanal? | Ja/Nein/Ungeklaert |
| Liegt eine wirksame DPA/AVV-Freigabe vor? | Ja/Nein |
| Werden Berufsgeheimnisse oder besondere Kategorien ausgeschlossen? | Ja/Nein |
| Welche Datensparsamkeitsmassnahme gilt? | IDs/Platzhalter/Synthetik/Redaktion |
| Wo liegt der externe Vertragsnachweis? | Verweis, kein Dokument im Repo |

## Beziehung zu bestehenden NoC-Dokumenten

- `docs/de/security-and-dsgvo.md`: allgemeine Repo-Schutzregeln.
- `docs/de/avv-checkliste-eventlock-saas.md`: Function8/EventLock-spezifische
  AVV-Checkliste.
- `docs/de/gpt-marketplace-operating-model.md`: Kanalentscheidung fuer GPT
  Store, Actions, Workspace Apps und lokale Plugins.
- `policies/data-protection-policy.yaml`: verbindliche Datenschutz- und
  Secret-Regeln.
