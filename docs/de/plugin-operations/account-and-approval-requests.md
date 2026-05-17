# Konto- und Freigabeanforderungen fuer NoC-Plugins

Diese Datei ist das Day0-Anforderungsregister fuer produktive Plugin-Nutzung in
regulierten Branchen. Sie enthaelt bewusst keine echten Kontonamen, Geheimnisse,
Mailbox-IDs, Steuer-IDs, Zertifikatsmaterialien oder Mandatsinhalte.

## Globale Kontrollen

| Bereich | Anforderung | Noetig vor | Owner | Hinweise |
| --- | --- | --- | --- | --- |
| GitHub | Repository-Schreibzugriff, Branchschutz, Required Checks und CODEOWNER-Review | produktive Plugin-Releases | Platform Owner | Private Repo-Zugriffe muessen explizit sein. |
| Nachweis | Entscheidung zu DMS oder Audit-Store, Retention-Klasse, Hash-Policy und Loeschsperre | jedem Nachweisimport | Compliance Owner | Standardmaessig nur Metadaten. |
| Security | Secret-Store-Entscheidung fuer kuenftige Connectoren | jedem Schreibadapter | Security Owner | Lokalen OS-Store oder Tenant Vault nutzen, nicht Git. |
| Review | Zwei-Personen-Freigabematrix fuer regulierte Aktionen | Day1 regulierte Arbeitsablaeufe | Managing Partner oder Notar | Pflicht vor Karten-/PIN-Abfragen, Einreichungen, Registeranmeldungen, XNP/XNotar-Uebergaben oder notariellen Aktionen. |

## Plugin-spezifische Anforderungen

| Plugin | Zu beantragende Konten/Freigaben | Blockiert fuer |
| --- | --- | --- |
| `noc-regulated-core` | GitHub-Schreibzugriff; freigegebene Reviewer-Liste; Nachweisablage-Entscheidung | Day1 produktive Nutzung |
| `noc-handelsregister` | Modusentscheidung: Buerger-Vorpruefung oder notariatsseitiger Arbeitsablauf; abgeschlossene `noc-cyberjack-rfid`- und `noc-bnotk-xnp`-Bereitschaft fuer Notariatsablaeufe; Notartermin oder Notariatsablauf; Bundesnotarkammer-App fuer Online-Verfahren; eID-faehiger amtlicher Ausweis und PIN; Antragsteller- und Reviewer-Freigabe fuer das Registeranmeldungspaket | Day1 produktive Nutzung |
| `noc-bnotk-xnp` | Abgeschlossene `NoC Karten- und SAK-Pruefung`; BNotK/XNP-Zugang fuer das Notariat; lokale XNP-Anmeldung und aktiver Amtstaetigkeitskontext; XNotar-/Registermodul oder Austauschordnerroute; Freigabe der Schnittstelle durch Notariatssoftwarehersteller; lokale Arbeitsplatz-Adminfreigabe | Day1 produktive Nutzung |
| `noc-bea-portal` | beA-Postfachzugriff; beA-Karte oder freigegebene Authentifizierungsmethode; beA Client Security am lokalen Arbeitsplatz; Kanzleipolicy fuer eEB und Exporte | Day1 produktive Nutzung |
| `noc-elster-eric` | ELSTER-Organisations- oder Nutzerzugang; lokales Zertifikat oder freigegebene Authentifizierungsmethode; ERiC-Herstellerregistrierung bei serverseitiger Integration; Freigabe zur steuerlichen Vertretung | Day1 produktive Nutzung |
| `noc-cyberjack-rfid` | BNotK-Chip-/Signaturkarte oder lokale Schneider/SCP-Karte; Kartenleser Sicherheitsklasse 3; BNotK SAK lite oder XNP-Kartenpfad; secureFramework-Kommunikationspfad; freigegebene Hardwarebeschaffung; lokale Arbeitsplatz-Adminfreigabe; Treiber-/Hersteller-Supportkanal | Day1 produktive Nutzung |
| `noc-grundbuch-portal` | Bundeslandspezifischer Grundbuchportalzugang; Bestaetigung der berechtigten Berufsrolle; Kostenstellenfreigabe; Retention-/DMS-Entscheidung | Day1 produktive Nutzung |
| `noc-oci-evidence` | OCI-Tenancy-Zugriff; Compartment-Admin oder delegierte Policy; Vault-/Key-Management-Freigabe; Budget-Owner; Audit-Retention-Owner | Day1 produktive Nutzung |

## Haltepunkte fuer externe Schreibadapter

Direkte externe Schreibadapter duerfen nicht implementiert oder aktiviert
werden, bis diese Punkte schriftlich freigegeben sind:

- beA-Sende-/Empfangs-/eEB-Automationspfad und Client-Security-Grenze.
- `NoC Karten- und SAK-Pruefung` fuer BNotK-Chip-/Signaturkarte oder lokale Schneider/SCP-Karte,
  Kartenleser Sicherheitsklasse 3, secureFramework und keine PIN-Erfassung.
- Offizieller XNP-/Notariatssoftware-Schnittstellenvertrag, abgeschlossenes
  `NoC Karten- und SAK-Pruefung`, lokale Authentifizierungspruefung,
  Amtstaetigkeitskontext und Zugangsdaten-Grenze.
- ELSTER/ERiC-Hersteller- oder Portalbetreiber-Onboarding, falls serverseitige
  Integration verfolgt wird.
- Autorisierter Grundbuchportal-Direktadapter, landesspezifische Bedingungen
  und Nachweis des berechtigten Interesses.
- Online-Handelsregisteranmeldungsroute, Modusentscheidung, abgeschlossene
  Karten-/SAK- und XNP-Pruefungen fuer notariatsseitige Arbeitsablaeufe,
  Antragstellerbefugnis und eID-/App-Bereitschaft.
- OCI Resource Manager Apply-Rechte, Vault-Policy und Audit-Retention.

## Day2-Rezertifizierung

- Konto-Ownership und Rollennotwendigkeit mindestens quartalsweise fuer Piloten
  und vor produktivem Release erneut bestaetigen.
- Lokale Arbeitsplatzvoraussetzungen nach OS-, XNP-, beA-Client-Security-,
  ERiC-, Browser-, Treiber- oder Kartenleser-Updates erneut bestaetigen.
- Nach jeder Plugin-Manifest-Aenderung
  `python3 scripts/validate_plugins.py` erneut ausfuehren.
