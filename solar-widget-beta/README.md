# Meine Solaranlage BETA

Eigenständiger Versuch zu Idee 1: Zahlen direkt in ein Alexa-Widget übertragen.
Stand 1. November 2026: eigener Amazon-Skill und Widget angelegt, Backend
bereitgestellt und Modell erfolgreich gebaut. Amazon bestätigt um 15:00 Uhr
(Europe/Berlin) die simulierte Installation auf Küche (Echo Show 8, 2. Generation).
Die sichtbare Ankunft am Gerät und Live-Daten sind noch nicht bestätigt.
Eine separate EU-D1-Datenbank ist angelegt; Worker-Bereitstellung und die
Home-Assistant-Anbindung stehen noch aus. Kein Zertifizierungsstand.

## Datenweg

Home Assistant → eigener HTTPS-Worker → eigene D1-Datenbank → Alexa Data Store
REST API → native Textkomponenten im neuen Widget. Keine Bildgenerierung,
Bild-URLs oder Abhängigkeiten vom bestehenden Skill. Der Worker sendet jede
Minute den aktuellen Snapshot. Die geräteseitige Data-Store-Region ist durch die
neue Skill-ID getrennt; Namespace `MeineSolaranlageBeta`, Schlüssel `live`.

Dieser erste Test gilt für einen Haushalt und einen konfigurierten BETA-Nutzer.
Keine automatische Übernahme von Nutzern oder Zugangsdaten des produktiven Skills.

## Separate Ressourcen einrichten

1. In der Alexa Developer Console einen **neuen** Alexa-hosted Python Custom
   Skill `Meine Solaranlage BETA` mit neuer Skill-ID anlegen. Bestehenden Skill
   nicht bearbeiten. Modell aus `interaction-model.de-DE.json` importieren;
   Aufrufname `meine solaranlage beta`.
2. Nur im neuen Skill APL, Widgets und Data Store aktivieren. Die Erweiterung
   `alexaext:datastore:10` anfordern (`ALEXA_EXTENSION.requestedExtensions`).
   Ein neues Widget-Paket erstellen und `widget.json` als APL-Dokument importieren.
   Für den ersten Test eine mittlere Widgetgröße wählen. Keine vorhandenen
   Widget-Pakete oder deren Versionen bearbeiten.
3. `lambda_function.py` ausschließlich in den neuen Skill übernehmen; dessen
   Umgebungsvariable `BETA_SKILL_ID` auf die neue ID setzen. Im Entwicklungsmodus
   öffnen. Die zu **diesem** Skill gehörige `context.System.user.userId` aus dem
   Testrequest als BETA-Nutzer-ID verwenden. Nicht die Nutzer-ID eines alten
   Skills übernehmen. Backend quittiert Lifecycle-Events ohne Sprachantwort;
   der nächste Minutenlauf liefert die Initialwerte.
4. Einen neuen Worker `meine-solaranlage-widget-beta` und eine **neue** D1-Datenbank
   gleichen Namens erstellen. `wrangler.example.jsonc` nach `wrangler.jsonc`
   kopieren und ausschließlich die neue Datenbank-ID eintragen. `schema.sql`
   nur in dieser neuen Datenbank ausführen. Worker aus diesem Ordner bereitstellen.
   Kein Aufruf der bisherigen Build-, Deploy- oder Migrationsskripte nötig.
5. Im neuen Worker getrennte Secrets setzen:

   | Secret | Inhalt |
   | --- | --- |
   | `BETA_WRITE_TOKEN` | Neuer zufälliger Schlüssel, mindestens 32 Zeichen |
   | `BETA_ADMIN_TOKEN` | Anderer neuer zufälliger Schlüssel, mindestens 32 Zeichen |
   | `BETA_CLIENT_ID` | Client-ID aus den Skill-Credentials des neuen Skills |
   | `BETA_CLIENT_SECRET` | Zugehöriges neues Client-Secret |
   | `BETA_USER_ID` | Nutzer-ID aus Schritt 3 |

   Der Worker holt LWA-Tokens mit Scope `alexa::datastore` und verwendet den
   europäischen Alexa-Endpunkt. Secrets nie ins Repository schreiben.
6. `home-assistant.yaml` als **zusätzliches** Package `solar_widget_beta.yaml`
   installieren. Es enthält separat benannte REST-Aktion und Automation.
   In HA `secrets.yaml` ergänzen:

   ```yaml
   solar_widget_beta_url: https://NEUER-BETA-WORKER.workers.dev/values
   solar_widget_beta_write_authorization: "Bearer NEUER-BETA-SCHREIBSCHLUESSEL"
   ```

   Vorhandenes Package und dessen Secrets unverändert lassen. Die kopierte
   Automation liest dieselben Sensoren und Recorder-Statistiken. Entitätsnamen
   prüfen und die HA-Konfiguration vor dem Laden validieren. HACS ist nicht nötig.
7. Neues BETA-Widget aus der Galerie installieren. Optional `POST /push` mit
   `Authorization: Bearer BETA_ADMIN_TOKEN` zum sofortigen Test aufrufen.
   `POST /values` bestätigt nur die Speicherung; die Zustellung erfolgt separat.

## Anzeige und Fehlerfälle

PV inklusive BKW, Hausverbrauch, Akkustand, Tagesproduktion und Tageseinspeisung
erscheinen als Text mit Einheiten. Fehlende Werte erscheinen als `—`, Null bleibt
Null. Tageswerte vom Vortag werden ausgeblendet. Nach drei Minuten ohne Upload
sendet der Worker eine Veraltet-Warnung. Der Empfangszeitpunkt bleibt sichtbar.
Wenn der Worker selbst oder die Alexa-Zustellung ausfällt, bleibt die letzte
Anzeige einschließlich ihres Zeitstempels stehen; das Widget besitzt noch keine
eigene zeitgesteuerte Veraltet-Erkennung.

HTTP 200 der Alexa API gilt erst dann als bestätigte Zustellung, wenn alle
zurückgemeldeten Geräte `SUCCESS` melden. Fehler werden ohne Schlüssel oder
Nutzer-IDs protokolliert. Der nächste Minutenlauf sendet den neuesten Snapshot;
alte Messwerte werden nicht zur späteren Zustellung eingereiht.

## Prüfung

Lokal: `node --test solar-widget-beta/worker.test.mjs` im Projektstamm.
Tests prüfen Zugangsschutz, Validierung, getrennte Speicherung, fehlende und
veraltete Werte, Datumswechsel und die Zustellbestätigung mit simulierten APIs.
Sie ersetzen keinen echten D1-/Amazon-/Gerätetest.

Abnahme auf dem Echo: zwei unterschiedliche Messwert-Snapshots senden und
prüfen, dass sich die Textwerte ohne Bildwechsel und ohne Skill-Neustart ändern.
HA-Upload mindestens vier Minuten stoppen und Veraltet-Warnung prüfen. Einen
Sensor nicht verfügbar machen und `—` prüfen. Parallel unveränderte Funktion
beider bisherigen Widgets kontrollieren. Erst danach Idee 1 als live getestet
markieren. Widget-Layout und Größen müssen im Amazon-Authoring-Tool und auf dem
Zielgerät geprüft werden.

## Referenzen

- [Amazon: Data Store REST API](https://developer.amazon.com/en-US/docs/alexa/alexa-presentation-language/data-store-rest-api-reference.html)
- [Amazon: Data Store Extension](https://developer.amazon.com/en-US/docs/alexa/alexa-presentation-language/apl-ext-data-store-extension.html)
- [Amazon: Widgets zu einem Skill hinzufügen](https://developer.amazon.com/en-US/docs/alexa/alexa-presentation-language/add-widget-to-your-skill.html)

Zum Abschalten nur die zusätzliche BETA-Automation und den BETA-Cron deaktivieren
und das neue Widget entfernen. Die bestehende Lösung ist davon unabhängig.
