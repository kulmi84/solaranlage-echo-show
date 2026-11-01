# Solaranlage – Bildwidget 2.0.1

Allgemeines Paket ohne eingebetteten privaten Bildzugang. `SolarAccountImage` ist am Echo im Skill `amzn1.ask.skill.4e153616-91b1-4eef-8ede-18cba6a17ecd` bestätigt. Der ursprüngliche öffentliche Skill wird dadurch nicht automatisch repariert oder ersetzt.

- `document.json`: tatsächlich getestete Anzeige, vollständiger Bildpuffer, Abruf beim Sichtbarwerden, alle 60 Sekunden, Erneuerung des befristeten Bildzugangs.
- `manifest.json`: öffentliche Paketbeschreibung. Paket-ID und Version bleiben gegenüber dem getesteten Stand gleich.
- `widget_account.py` und `widget_publisher.py`: holen den Zugang aus derselben Kontoverknüpfung wie Vollbild und schreiben ihn gerätebezogen in `SolarAccountImages/access`.
- `widget_runtime.py`: prüft exakt Skill und Paket. Antippen erneuert den Bildzugang anhand des jetzt verknüpften Haushalts und öffnet die Vollbildansicht.

## Kontowechsel

Nach einem Wechsel des verknüpften Haushalts die vorhandene Kachel einmal antippen. Dann übernimmt sie dessen Werte ohne Neuinstallation. Eine automatische sofortige Übernahme ohne Antippen ist nicht zugesagt. Bei normalen Bildladefehlern bleibt der letzte vollständige Bildsatz samt Zeitstand erhalten.

## Betreiber-Bereitstellung

1. `python build_skill.py` erzeugt den allgemeinen Code in `dist/lambda_function.py`. Die private Amazon-Quelle vor einer Übernahme sichern und abgleichen; den ursprünglichen öffentlichen Skill nicht ungeprüft überschreiben.
2. Die private `relay_config.json` enthält zusätzlich `widget_datastore_credentials` mit `ALEXA_CLIENT_ID` und `ALEXA_CLIENT_SECRET` aus den Data-Store-Berechtigungen genau dieses Skills. Niemals veröffentlichen.
3. Paket `SolarAccountImage` mit Dokument und Manifest übernehmen; APL, Data Store und zugehörige Extension-Einstellungen des getesteten Skills beibehalten. Modell bauen und validieren.
4. Erst nach erfolgreicher Amazon-Zertifizierung ist der Skill mit Widget allgemein verfügbar. HACS installiert das Echo-Widget nicht selbst.

Die beiden alten Dienstadressen bleiben während der Kundenmigration erhalten. Keine privaten Recovery-Pakete oder Bild-URLs in diese Quellen übernehmen.
