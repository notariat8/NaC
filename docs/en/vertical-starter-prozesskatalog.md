# Vertical Starter-Prozesskatalog (v1)

## Zweck

Dieser Katalog definiert ein erstes, vergleichbares Starterset fuer sieben Verticals auf Basis desselben Core-Modells.

## Einheitliche Statuswerte

- `draft`
- `validated`
- `needs_review`
- `approved`
- `executed`
- `archived`

## Einheitliche Freigabepunkte

- `validated -> needs_review`: bei fachlicher oder regulatorischer Relevanz
- `needs_review -> approved`: fachlicher Review
- `approved -> executed`: operative Freigabe (ggf. Vier-Augen)

## Starterset: Anwaltskanzlei (`law_firm`)

1. Mandatsannahme
2. Konfliktpruefung
3. Fristensteuerung
4. Aktenfuehrung und Dokumentation
5. RVG-/Leistungsabrechnung

Core-Mapping:

- Intake/Auftragsstart
- Freigaben und Rollen
- Leistungserfassung und Abrechnung
- Nachweis/Audit

## Starterset: Notariat (`notary`)

1. Aktenanlage fuer Mandant
2. Identitaetspruefung und Unterlagencheck
3. Urkundenvorbereitung
4. Vollzug und Registerkommunikation
5. Abrechnung und Abschlussnachweis

Core-Mapping:

- Intake/Auftragsstart
- Freigaben und Rollen
- Nachweis/Audit
- Abschluss und Archivierung

## Starterset: Steuerberatung (`tax_office`)

1. Mandanten-Onboarding
2. Belegaufnahme und Strukturierung
3. Deklarationszyklus (periodisch)
4. Plausibilitaetspruefung und Rueckfrage
5. Freigabe und Uebermittlungsvorbereitung

Core-Mapping:

- Intake/Auftragsstart
- Vorgangsstatus/Freigaben
- Buchhaltung und Steuerbezug
- Audit und Nachweis

## Starterset: Softwareunternehmen (`software_company`)

1. Demand-/Ticket-Intake
2. Release-Planung und Freigabe
3. Incident-Management
4. SLA-/Service-Nachweise
5. Rechnungs- und Leistungsnachweis

Core-Mapping:

- Intake/Auftragsstart
- Incident- und Abweichungsbehandlung
- Freigaben und Rollen
- Nachweis/Audit

## Starterset: Hausverwaltung (`property_management`)

1. Objekt- und Mieteraufnahme
2. Vertrags- und Fristenanlage
3. Wartungsticket und Dienstleistersteuerung
4. Rollen- und Zugriffswechsel im Objektteam
5. Uebergabe-/Schadensdokumentation mit Abschlussnachweis

Core-Mapping:

- Intake/Auftragsstart
- Freigaben und Rollen
- Incident- und Abweichungsbehandlung
- Nachweis/Audit

## Starterset: Vermoegensverwaltung (`wealth_management`)

1. Mandatsaufnahme und KYC-Pruefung
2. Eignungs- und Risikoprofilfreigabe
3. Portfolio-Aenderung mit Rebalancing-Kontrolle
4. Rollen- und Zugriffswechsel fuer Mandatsteams
5. Mandatsreporting mit Audit-Nachweis

Core-Mapping:

- Intake/Auftragsstart
- Freigaben und Rollen
- Risiko- und Kontrollpunkte
- Nachweis/Audit

## Starterset: Schreinerei (`carpentry`)

1. Kundenanfrage und Bedarfserfassung
2. Aufmass und Angebotskalkulation
3. Auftrag und Materialplanung
4. Werkstatt-/Montagekoordination
5. Rechnungsstellung und Gewaehrleistungsnachweis

Core-Mapping:

- Intake/Auftragsstart
- Leistungserfassung und Abrechnung
- Freigaben und Rollen
- Abschluss und Archivierung

## Hinweise fuer den Pilot

- Pro Vertical zuerst nur 1-2 Prozesse produktiv pilotieren.
- Alle Prozesse laufen ueber Branch + PR + Review.
- Release-Binding je Vorgangsstart ist verpflichtend.
- Abweichungen werden als Change Request dokumentiert.
