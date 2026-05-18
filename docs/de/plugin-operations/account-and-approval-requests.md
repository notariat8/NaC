# Konto- und Freigabeanforderungen für NaC-Plugins

Diese Datei ist das Day0-Anforderungsregister für produktive Plugin-Nutzung in
regulierten Branchen. Sie enthält bewusst keine echten Kontonamen, Geheimnisse,
Mailbox-IDs, Steuer-IDs, Zertifikatsmaterialien oder Mandatsinhalte.

## Globale Kontrollen

| Bereich | Anforderung | Nötig vor | Owner | Hinweise |
| --- | --- | --- | --- | --- |
| GitHub | Repository-Schreibzugriff, Branchschutz, Required Checks und CODEOWNER-Review | produktive Plugin-Releases | Platform Owner | Private Repo-Zugriffe müssen explizit sein. |
| Nachweis | Entscheidung zu DMS oder Audit-Store, Retention-Klasse, Hash-Policy und Löschsperre | jedem Nachweisimport | Compliance Owner | Standardmäßig nur Metadaten. |
| Security | Secret-Store-Entscheidung für künftige Connectoren | jedem Schreibadapter | Security Owner | Lokalen OS-Store oder Tenant Vault nutzen, nicht Git. |
| Review | Zwei-Personen-Freigabematrix für regulierte Aktionen | Day1 regulierte Arbeitsabläufe | Managing Partner oder Notar | Pflicht vor Karten-/PIN-Abfragen, Einreichungen, Registeranmeldungen, XNP/XNotar-Übergaben oder notariellen Aktionen. |

## Plugin-spezifische Anforderungen

| Plugin | Zu beantragende Konten/Freigaben | Blockiert für |
| --- | --- | --- |
| `nac-regulated-core` | GitHub-Schreibzugriff; freigegebene Reviewer-Liste; Nachweisablage-Entscheidung | Day1 produktive Nutzung |
| `nac-handelsregister` | Modusentscheidung: Bürger-Vorprüfung oder notariatsseitiger Arbeitsablauf; abgeschlossene `nac-cyberjack-rfid`- und `nac-bnotk-xnp`-Bereitschaft für Notariatsabläufe; Notartermin oder Notariatsablauf; Bundesnotarkammer-App für Online-Verfahren; eID-fähiger amtlicher Ausweis und PIN; Antragsteller- und Reviewer-Freigabe für das Registeranmeldungspaket | Day1 produktive Nutzung |
| `nac-bnotk-xnp` | Abgeschlossene `Karte/SAK`; BNotK/XNP-Zugang für das Notariat; lokale XNP-Anmeldung und aktiver Amtstätigkeitskontext; XNotar-/Registermodul oder Austauschordnerroute; Freigabe der Schnittstelle durch Notariatssoftwarehersteller; lokale Arbeitsplatz-Adminfreigabe | Day1 produktive Nutzung |
| `nac-bea-portal` | beA-Postfachzugriff; beA-Karte oder freigegebene Authentifizierungsmethode; beA Client Security am lokalen Arbeitsplatz; Kanzleipolicy für eEB und Exporte | Day1 produktive Nutzung |
| `nac-elster-eric` | ELSTER-Organisations- oder Nutzerzugang; lokales Zertifikat oder freigegebene Authentifizierungsmethode; ERiC-Herstellerregistrierung bei serverseitiger Integration; Freigabe zur steuerlichen Vertretung | Day1 produktive Nutzung |
| `nac-cyberjack-rfid` | BNotK-Chip-/Signaturkarte oder lokale Schneider/SCP-Karte; Kartenleser Sicherheitsklasse 3; BNotK SAK lite oder XNP-Kartenpfad; secureFramework-Kommunikationspfad; freigegebene Hardwarebeschaffung; lokale Arbeitsplatz-Adminfreigabe; Treiber-/Hersteller-Supportkanal | Day1 produktive Nutzung |
| `nac-grundbuch-portal` | Bundeslandspezifischer Grundbuchportalzugang; Bestätigung der berechtigten Berufsrolle; Kostenstellenfreigabe; Retention-/DMS-Entscheidung | Day1 produktive Nutzung |
| `nac-oci-evidence` | OCI-Tenancy-Zugriff; Compartment-Admin oder delegierte Policy; Vault-/Key-Management-Freigabe; Budget-Owner; Audit-Retention-Owner | Day1 produktive Nutzung |

## Haltepunkte für externe Schreibadapter

Direkte externe Schreibadapter dürfen nicht implementiert oder aktiviert
werden, bis diese Punkte schriftlich freigegeben sind:

- beA-Sende-/Empfangs-/eEB-Automationspfad und Client-Security-Grenze.
- `Karte/SAK` für BNotK-Chip-/Signaturkarte oder lokale Schneider/SCP-Karte,
  Kartenleser Sicherheitsklasse 3, secureFramework und keine PIN-Erfassung.
- Offizieller XNP-/Notariatssoftware-Schnittstellenvertrag, abgeschlossenes
  `Karte/SAK`, lokale Authentifizierungsprüfung,
  Amtstätigkeitskontext und Zugangsdaten-Grenze.
- ELSTER/ERiC-Hersteller- oder Portalbetreiber-Onboarding, falls serverseitige
  Integration verfolgt wird.
- Autorisierter Grundbuchportal-Direktadapter, landesspezifische Bedingungen
  und Nachweis des berechtigten Interesses.
- Online-Handelsregisteranmeldungsroute, Modusentscheidung, abgeschlossene
  Karten-/SAK- und XNP-Prüfungen für notariatsseitige Arbeitsabläufe,
  Antragstellerbefugnis und eID-/App-Bereitschaft.
- OCI Resource Manager Apply-Rechte, Vault-Policy und Audit-Retention.

## Day2-Rezertifizierung

- Konto-Ownership und Rollennotwendigkeit mindestens quartalsweise für Piloten
  und vor produktivem Release erneut bestätigen.
- Lokale Arbeitsplatzvoraussetzungen nach OS-, XNP-, beA-Client-Security-,
  ERiC-, Browser-, Treiber- oder Kartenleser-Updates erneut bestätigen.
- Nach jeder Plugin-Manifest-Änderung
  `python3 scripts/validate_plugins.py` erneut ausführen.
