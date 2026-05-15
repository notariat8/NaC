# Konto- und Freigabeanforderungen fuer NoC-Plugins

Diese Datei ist das Day0-Anforderungsregister fuer produktive Plugin-Nutzung in
regulierten Branchen. Sie enthaelt bewusst keine echten Kontonamen, Secrets,
Mailbox-IDs, Steuer-IDs, Zertifikatsmaterialien oder Mandatsinhalte.

## Globale Kontrollen

| Bereich | Anforderung | Noetig vor | Owner | Hinweise |
| --- | --- | --- | --- | --- |
| GitHub | Repository-Schreibzugriff, Branchschutz, Required Checks und CODEOWNER-Review | produktive Plugin-Releases | Platform Owner | Private Repo-Zugriffe muessen explizit sein. |
| Evidence | Entscheidung zu DMS oder Audit-Store, Retention-Klasse, Hash-Policy und Loeschsperre | jedem Evidence-Import | Compliance Owner | Standardmaessig nur Metadaten. |
| Security | Secret-Store-Entscheidung fuer kuenftige Connectoren | jedem Schreibadapter | Security Owner | Lokalen OS-Store oder Tenant Vault nutzen, nicht Git. |
| Review | Zwei-Personen-Freigabematrix fuer regulierte Aktionen | Day1 regulierte Workflows | Managing Partner oder Notar | Pflicht vor Card/PIN-Prompts, Einreichungen, Registeranmeldungen, XNP/XNotar-Uebergaben oder notariellen Aktionen. |

## Plugin-spezifische Anforderungen

| Plugin | Zu beantragende Konten/Freigaben | Blockiert fuer |
| --- | --- | --- |
| `noc-regulated-core` | GitHub-Schreibzugriff; freigegebene Reviewer-Liste; Evidence-Storage-Entscheidung | Day1 produktive Nutzung |
| `noc-handelsregister` | Modusentscheidung: Buerger-Preflight oder notariatsseitiger Workflow; abgeschlossene `noc-cyberjack-rfid`- und `noc-bnotk-xnp`-Readiness fuer Notariatsworkflows; Notartermin oder Notariatsworkflow; Bundesnotarkammer-App fuer Online-Verfahren; eID-faehiger amtlicher Ausweis und PIN; Antragsteller- und Reviewer-Freigabe fuer das Registeranmeldungspaket | Day1 produktive Nutzung |
| `noc-bnotk-xnp` | Abgeschlossene `noc-cyberjack-rfid` Card/SAK-Readiness; BNotK/XNP-Zugang fuer das Notariat; lokale XNP-Anmeldung und aktiver Amtstaetigkeitskontext; XNotar-/Registermodul oder Austauschordnerroute; Freigabe der Schnittstelle durch Notariatssoftwarehersteller; lokale Arbeitsplatz-Adminfreigabe | Day1 produktive Nutzung |
| `noc-bea-portal` | beA-Postfachzugriff; beA-Karte oder freigegebene Authentifizierungsmethode; beA Client Security am lokalen Arbeitsplatz; Kanzleipolicy fuer eEB und Exporte | Day1 produktive Nutzung |
| `noc-elster-eric` | ELSTER-Organisations- oder Nutzerzugang; lokales Zertifikat oder freigegebene Authentifizierungsmethode; ERiC-Herstellerregistrierung bei serverseitiger Integration; Freigabe zur steuerlichen Vertretung | Day1 produktive Nutzung |
| `noc-cyberjack-rfid` | BNotK-Chip-/Signaturkarte oder lokale Schneider/SCP-Karte; Kartenleser Sicherheitsklasse 3; BNotK SAK lite oder XNP-Kartenpfad; secureFramework-Kommunikationspfad; freigegebene Hardwarebeschaffung; lokale Arbeitsplatz-Adminfreigabe; Treiber-/Hersteller-Supportkanal | Day1 produktive Nutzung |
| `noc-grundbuch-portal` | Bundeslandspezifischer Grundbuchportalzugang; Bestaetigung der berechtigten Berufsrolle; Kostenstellenfreigabe; Retention-/DMS-Entscheidung | Day1 produktive Nutzung |
| `noc-oci-evidence` | OCI-Tenancy-Zugriff; Compartment-Admin oder delegierte Policy; Vault-/Key-Management-Freigabe; Budget-Owner; Audit-Retention-Owner | Day1 produktive Nutzung |

## Haltepunkte fuer externe Schreibadapter

Direkte externe Schreibadapter duerfen nicht implementiert oder aktiviert
werden, bis diese Punkte schriftlich freigegeben sind:

- beA-Sende-/Empfangs-/eEB-Automationspfad und Client-Security-Grenze.
- Card/SAK-Gate fuer BNotK-Chip-/Signaturkarte oder lokale Schneider/SCP-Karte,
  Kartenleser Sicherheitsklasse 3, secureFramework und keine PIN-Erfassung.
- Offizieller XNP-/Notariatssoftware-Schnittstellenvertrag, abgeschlossenes
  Card/SAK-Gate, lokales Authentifizierungsgate, Amtstaetigkeitskontext und
  Credential-Grenze.
- ELSTER/ERiC-Hersteller- oder Portalbetreiber-Onboarding, falls serverseitige
  Integration verfolgt wird.
- Autorisierter Grundbuchportal-Direktadapter, landesspezifische Bedingungen
  und Nachweis des berechtigten Interesses.
- Online-Handelsregisteranmeldungsroute, Modusentscheidung, abgeschlossene
  Card/SAK- und XNP-Gates fuer notariatsseitige Workflows, Antragstellerbefugnis
  und eID-/App-Readiness.
- OCI Resource Manager Apply-Rechte, Vault-Policy und Audit-Retention.

## Day2-Rezertifizierung

- Konto-Ownership und Rollennotwendigkeit mindestens quartalsweise fuer Piloten
  und vor produktivem Release erneut bestaetigen.
- Lokale Arbeitsplatzvoraussetzungen nach OS-, XNP-, beA-Client-Security-,
  ERiC-, Browser-, Treiber- oder Kartenleser-Updates erneut bestaetigen.
- Nach jeder Plugin-Manifest-Aenderung
  `python3 scripts/validate_plugins.py` erneut ausfuehren.
