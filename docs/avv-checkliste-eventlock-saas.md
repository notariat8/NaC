# AVV-Checkliste fuer EventLock-SaaS (Function8 als Auftragsverarbeiter)

## Zweck

Diese Checkliste hilft, den AVV (Art. 28 DSGVO) fuer das EventLock-as-a-Service-Modell strukturiert und nachweisbar vorzubereiten.
Sie gilt analog fuer alle weiteren Function8-Leistungen, die als Auftragsverarbeitung eingestuft werden.

Hinweis: Dies ist ein operativer Leitfaden und ersetzt keine Rechtsberatung.

## Wann ist ein AVV erforderlich?

Ein AVV ist in der Regel erforderlich, wenn:

- Function8 Eventstreaming-/Journal-Daten fuer den Kunden verarbeitet,
- der Kunde Zweck und Mittel der Verarbeitung vorgibt,
- personenbezogene Daten oder personenbezogene Metadaten betroffen sein koennen.

## Vertragskern (Pflichtinhalte)

- Gegenstand und Dauer der Verarbeitung
- Art und Zweck der Verarbeitung
- Kategorien personenbezogener Daten
- Kategorien betroffener Personen
- Rechte und Pflichten des Verantwortlichen
- dokumentierte Weisungsgebundenheit

## Technische und organisatorische Massnahmen (TOM)

- tenant-separierte Subinstanz pro Kunde
- dedizierter Schluessel pro Kunde
- immutable Retention (WORM) pro Kunde
- rollenbasierter Zugriff (Need-to-know)
- Protokollierung und revisionssichere Ereigniskette
- Schluesselrotation und Incident-Prozess
- Vier-Augen-Freigabe fuer kritische Aenderungen (Retention, Legal Hold)

## Unterauftragsverarbeiter und Cloud-Standorte

- eingesetzte Cloud-Plattform(en) benennen (AWS, Azure, GCP, OCI)
- konkrete Dienste benennen (z. B. Broker, WORM-Store, KMS)
- Standorte/Regionen dokumentieren
- Wechselverfahren fuer Subprozessoren vertraglich regeln

## Drittlandtransfer

- pruefen, ob Daten ausserhalb EU/EWR verarbeitet werden
- falls ja: geeignete Garantien dokumentieren (z. B. SCC)
- Transfer-Impact-Bewertung dokumentieren

## Betroffenenrechte und Support-Prozesse

- Auskunft, Berichtigung, Loeschung, Einschraenkung: Prozess und SLA
- eindeutiger Ansprechpartner auf Provider- und Kundenseite
- Nachweis, wie Weisungen umgesetzt werden

## Incident und Meldepflichten

- Frist fuer Erstmeldung an Kunden vertraglich fixieren
- Meldeinhalt standardisieren (Umfang, Wirkung, Gegenmassnahmen)
- gemeinsame Eskalationskette dokumentieren

## Audit und Nachweise

- Auditrecht des Kunden klar regeln (remote/on-site, Vorankuendigung)
- Nachweispaket definieren:
  - Architektur
  - TOM-Nachweise
  - Zugriffsprotokolle
  - Restore-/Integritaetstests
- Frequenz fuer Regel-Audits festlegen

## Beendigung und Datenrueckgabe

- Rueckgabeformat und Fristen definieren
- Loeschprozess nach Vertragsende definieren
- Umgang mit gesetzlichen Aufbewahrungspflichten festlegen
- Legal-Hold-Faelle gesondert behandeln

## Rollenmodell Function8 vs Kunde

- Function8:
  - Plattformbetrieb, Security-Baseline, SLA-Betrieb
- Kunde:
  - Datenklassifikation, Legal-Hold-Entscheidungen, Freigabe des Audit-Scopes

Referenz: `docs/tenant-ownership-and-eventlock-service.md`

## Operative Freigabe vor Go-Live

- [ ] AVV unterschrieben
- [ ] Subprozessorliste vollstaendig und bestaetigt
- [ ] TOM-Anlage freigegeben
- [ ] Regionen und Transferregeln freigegeben
- [ ] Incident-Meldeprozess getestet
- [ ] Auditprozess und Ansprechpartner dokumentiert
- [ ] Retention/Legal-Hold-Owner benannt
