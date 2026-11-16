# Live-Werte: separat integrierter lokaler Kandidat

Stand 16.11.2026. Nicht ausgerollt, keine echten Geräte registriert, keine D1-Migration ausgeführt, keine Store-Einreichung. Laufende DEV und Store unverändert.

## Abhakliste

1. ~~Einbindung in den Skill~~ — im separaten lokalen Kandidaten umgesetzt und getestet.
2. ~~Weitere Absicherung der Zustellung~~ — im lokalen Kandidaten umgesetzt und getestet.
3. [ ] Echo-Nachweis nach bewusst freigegebener Installation: drei automatische Aktualisierungen mit wechselnden Werten, Tipp ins korrekte Vollbild, beide Seiten, Neustart und Fehlerfall. Ein Build oder Installationsauftrag ist kein Gerätenachweis.

## Enthaltene Umsetzung

- `skill/lambda_function.py`: vollständiger Hosted-Skill-Kandidat mit zusätzlichem Live-Einstieg. Bestehende DEV-Routen bleiben enthalten. Die neue Live-Route verwendet eigene Paketprüfung, Vollbild-Aufrufkennung und Versionszeile; Live-Konfiguration ist standardmäßig aus.
- `skill/skill_registration.py`: integrierter Adapter für Installation, Entfernen, Anzeige der Kachel, Kontoverknüpfung und Skill-Deaktivierung. Haushalt wird ausschließlich aus dem bestehenden OAuth-Zugang aufgelöst. Kein Übernehmen alter zwischengespeicherter Geräte-IDs. HTTP-Weiterleitungen werden abgelehnt; Antworten sind begrenzt.
- `widget-template/`: visuell unveränderte Kachelvorlage. Beim Anzeigen erfolgt eine Inline-Registrierung; bei einem Fehler wird im Minutentakt versucht, bis die Bestätigung vorliegt. Nach bestätigter Registrierung holt die kleine Kachel regulär keine Bilder und sendet keine minütlichen Abrufereignisse mehr. Sie empfängt die gemeinsam geschriebenen vier Textwerte. Bei geänderter Datenbindung wird diese über die Kontoverknüpfung neu bestätigt.
- `worker.mjs`: gemeinsamer Wertezugang und Publisher für registrierte Haushalte. Vollbild liest ausschließlich den zum OAuth-Token gehörenden Haushalt. Gruppen werden nach Haushalt und Amazon-Konto getrennt, maximal 20 Geräte pro Amazon-Aufruf. Einmaliger Amazon-Tokenabruf pro Lauf; keine unmittelbaren Retry-Schleifen.
- `schema.sql`: additive Geräte-, Instanz-, Widerrufs-, Sperr- und Fortschrittstabellen. Bestehende Haushalte und Token bleiben erhalten.
- `skill-events.merge.json`: nur die zwei zusätzlich benötigten Event-Abonnements als Merge-Vorlage. Nicht als Ersatz des bestehenden Skill-Manifests verwenden. Endpunkt des bestehenden Hosted-Skills beibehalten.
- `live-preparation.json`: bewusst abgeschaltete Vorbereitung, keine unmittelbar ausrollbare Wrangler-Konfiguration.

Die gemeinsame Formatierung wird aus dem bestätigten DEV-Modul importiert. Kleine Kachel und Vollbild verwenden direkte Werte, nicht den Bilderdienst. Die Versionszeile des Live-Kandidaten lautet `1.1.0 (Build 1611)`; DEV behält seine eigene Bezeichnung.

## Zustellung und Kontowechsel

Eine zeitlich begrenzte D1-Sperre serialisiert Registrierung, Entfernen, Kontowechsel und Zustellung je Stage. Ein gleichzeitig eintreffender Änderungsauftrag wird mit `delivery_busy` nicht fälschlich bestätigt. Lifecycle-Fehler werden im Skill weitergegeben, damit das Ereignis wiederholt werden kann; Inline-Registrierung versucht es beim nächsten Tick erneut.

Zusätzlich werden Besitzer, Haushalt, Zugangsgeneration und Sperrstatus direkt vor der Amazon-Zustellung geprüft. Bereits von Amazon angenommene Aufträge können nicht zurückgerufen werden. Deshalb enthält jeder Datensatz eine Bindung an Stage, Konto, Haushalt und Zugangsgeneration: Die Kachel übernimmt nur Daten ihrer über OAuth bestätigten Bindung und keinen älteren Zeitstempel. Ein verspäteter Datensatz des vorherigen Kontos kann so nicht als aktueller Datensatz übernommen werden. Dieser APL-Filter ist lokal strukturell geprüft; seine Ausführung muss beim Echo-Nachweis bestätigt werden.

Sperren laufen nach einem abgebrochenen Worker aus. Vor Netzwerkaufrufen werden Eigentümer und Restlaufzeit geprüft. Der Publisher begrenzt einen Lauf auf maximal 100 ausgewählte Geräte und stoppt neue Zustellungen nach ungefähr 40 Sekunden; ein gespeicherter Cursor rotiert durch weitere Geräte. Bei mehr als 100 Geräten oder langsamen Diensten ist ein 60-Sekunden-Takt für alle Geräte damit nicht garantiert. Vor einer größeren Freigabe reale Laufzeit und Quoten messen und gegebenenfalls die Verteilung skalieren. Der Entwurf ist für den begrenzten Pilot mit Marcins einem Haushalt vorgesehen.

Abruf-/Zustellfehler überschreiben keine gültigen Werte und erzeugen keinen erfundenen neuen Messzeitstempel. Bei einem tatsächlichen Wechsel der bestätigten Haushaltsbindung werden vorherige Haushaltswerte geleert, statt sie im neuen Haushalt weiter anzuzeigen.

Skill-Deaktivierung beendet die Zuordnung. Der Account-Linked-Event stellt vorhandene aktive Geräte auf den neu verknüpften Haushalt um. Sprachprofil-spezifische Account-Linked-Ereignisse werden nicht als Wechsel des gesamten Haushalts behandelt. Der nur bei Personalisierung verfügbare Account-Unlinked-Event wird nicht vorausgesetzt; Zugangssperrung/-rotation im bestehenden Kontodienst stoppt die Zustellung ebenfalls. Reale Lifecycle-Lieferung und Fehlerwiederholung gehören zum Echo-/Pilotnachweis.

## Lokale Nachweise

16 Node/SQLite-Tests plus 17 Python-Tests bestanden. Alle Daten und Amazon-Antworten sind künstlich; keine Netzwerkaufrufe an echte Haushalte.

Geprüft sind Haushaltstrennung, DEV/Live auf demselben synthetischen Gerät, Installation/Inline-Registrierung, Klick ins richtige Vollbild, ein gemeinsamer Vollbildabruf, Seitenbeibehaltung, Abruffehler ohne Überschreiben, Skill-Deaktivierung, Entfernen einzelner Instanzen, veraltete Ereignisse, Kontowechsel, gesperrte/gedrehte Zugänge, konkurrierende Zustellung, abgelaufene Sperren, Amazon-Fehler und Weiterverarbeitung sowie Gruppen 20/1 und Rotation über 101 Geräte.

Der kleine visuelle Komponentenbaum entspricht dem bestätigten DEV-Stand abgesehen von der Versionszeile. Der Vollbildvergleich verwendet identische Messwerte und identische Uhrzeit; nur Route und Versionszeile werden für den Vergleich normalisiert. Das ersetzt keinen optischen Vergleich am Echo.

Aus dem Repository:

    node --test cloudflare/echo-values/worker.test.mjs
    python -B -m unittest discover -s cloudflare/echo-values -p "test_*.py"

Die Abhängigkeiten aus `skill/requirements.txt` müssen installiert sein. Für den lokalen Python-Lauf wurde die bereits vorhandene gepinnte dateutil-Installation verwendet.

## Noch vor Aktivierung erforderlich

- Aktuellen echten Hosted-/Widget-/Konfigurationsstand und D1 privat exportieren, Prüfsummen festhalten. Die lokale Voränderungssicherung liegt unter `.private/solar-v3/live-preparation-backup-20261116`; sie ist kein aktueller Cloud-Datenbankexport.
- Neue Paketkennung mit Marcin abstimmen, erst dann registrieren. Vorlage enthält absichtlich `__LIVE_PACKAGE_ID_PENDING__` und `__LIVE_NAMESPACE_PENDING__`. Die laufende DEV-Kennung wird nicht ersetzt.
- Geplanten Worker `solaranlage-echo-werte` mit bestehender D1 `solaranlage` verbinden. Neue Tabellen erst bei freigegebener Aktivierung anlegen. REGISTRATION_SECRET, SUBJECT_HASH_KEY und Amazon-Zugang verschlüsselt hinterlegen. Keine bestehenden Haushalte manuell umstellen. Keine Kennungen oder Geheimnisse aus DEV als feste Live-Ziele übernehmen.
- Event-Abonnements zusammenführen, Hosted-Konfiguration und Datenbindung übereinstimmend setzen. Erst im begrenzten Pilot aktivieren; kein gleichzeitiges Schreiben alter und neuer Publisher auf dieselbe Bindung. Beobachtbarkeit aktivieren, nur aggregierte Resultate protokollieren.
- Verbliebene Verweise auf den gelöschten Host `solaranlage-public-beta` prüfen. Kontodienst bleibt `solaranlage-kontodienst`; bestehende OAuth-Client-ID `solaranlage-public-beta`, Client-Secret und Token unverändert übernehmen. Alte Installationen benötigen eine ausdrücklich geplante Kompatibilitätslösung. Vorhandene HACS-Hostmigration zuerst wiederverwenden.
- Echo-Nachweis und echte Cloudflare-Aufrufmessung durchführen. Cron-Läufe, Vollbild-GET, D1-Abfragen und Amazon-Unteraufrufe getrennt zählen. Der neue Kandidat hat keine internen Worker-Weiterleitungen; HACS-Uploads und Kontodienst sind zusätzliche Last. Noch keine Einsparungszahl als gemessen ausgeben.
- Danach erst Live-Freigabe und Zertifizierung. Bis dahin aktuellen Store-Stand unverändert lassen.

## Rückweg

Neuen Publisher zuerst stoppen. Gesicherte Hosted-/Widget-Fassung und alten Datenweg wieder einsetzen. Funktionierende DEV, Bilder- und Display-Dienste zunächst erhalten. Die additiven Tabellen können bleiben; keine Haushaltsdaten löschen. Der früher gelöschte Beta-Host wird durch einen Code-Rollback nicht wiederhergestellt; falls erforderlich, Weiterleitung ausdrücklich aus privater Sicherung wiederherstellen.

## Verwendete Schnittstellen

D1-Transaktionen: https://developers.cloudflare.com/d1/worker-api/d1-database/
Alexa Skill-Events: https://developer.amazon.com/en-AU/docs/alexa/smapi/add-events-to-your-skill-with-smapi.html


## Aufwachen aus dem Energiesparmodus

Build 1611.12 ist als DEV-Referenz für den Aufwach-Abruf am Küchen-Echo bestätigt. Das Store-Update übernimmt die Funktion in beiden Ansichten. Nach dem Einschalten des Displays fragt die kleine Kachel den aktuellen Datensatz über den bestehenden authentifizierten Widget-Weg ab. Das Vollbild aktualisiert einmal die gerade sichtbare Seite. Der reguläre Takt bleibt bei 60 Sekunden für Live/Heute und sechs Stunden für Monat/Jahr.

Abnahme für das Store-Update: Kleine Kachel und Vollbild jeweils nach mehreren Minuten mit ausgeschaltetem Display prüfen. Zeit bis zum neuen Messstand auf dem Echo erfassen. Die DEV-Bestätigung gilt für Build 1611.12. Der Store-Kandidat ist separat am Gerät zu prüfen.

APL-Schnittstelle: https://developer.amazon.com/en-US/docs/alexa/alexa-presentation-language/apl-document.html#ondisplaystatechange
