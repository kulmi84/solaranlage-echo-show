# Projektstatus · 31.10.2026

## Widget und HACS

- **Bildwidget 2.0.1:** gemeinsamer Kontozugang, sofortiges Nachladen beim Einblenden, automatische Zugangserneuerung, vollständiger Bildpuffer bei Fehlern und richtige Vollbild-Zuordnung am Gerät bestätigt.
- Weiße Zeile „2.0.1 · Live · alle 60 Sekunden“ unter dem Zeitstand: Amazon-Build und einmaliger Installationsauftrag bestätigt; tatsächliche Geräteansicht noch offen.
- **HACS 1.0.9:** automatische Kontoanlage nach Zustimmung ohne Einladung, IP-/Kapazitätsschutz, sichere Wiederholungen und verständliche Fehler. Bestehende Konten/Sensoren bleiben bei der Adressübernahme erhalten; klarere PV-/BKW-Hilfen.
- Kontodienst am 31.10.2026 freigeschaltet. Zwei neue Testhaushalte über den tatsächlichen HACS-Code angemeldet, getrennte Werte hochgeladen und über bestehendes OAuth abgerufen; danach Testhaushalte gelöscht. Die vier bisherigen Haushalte und ihre Tokenanzahlen blieben erhalten. 28 Python- und 24 Backendtests bestanden.
- Noch offen: echte HA-Oberflächenabnahme einer Neueinrichtung und Updates der externen Bestandsinstallationen. Keine neue öffentliche Amazon-Widget-Freigabe.

## Erhaltene Skills

| Skill | Aufgabe |
|---|---|
| Data Store Labor | Enthält das funktionierende Bildwidget SolarAccountImage; der historische Skillname bleibt vorerst. |
| Solaranlage | Öffentlicher Skill mit zugehörigem Development-Stand für bestehende Nutzer. |
| Mein Zuhause | Separates Projekt, unverändert. |

## Aufgeräumt

Alte Test-Widgetpakete, das einzelne Labor-Testwidget und der Skill „Meine Solaranlage Test“ sind privat archiviert und gelöscht. Der alte Zahlenversuch und seine Worker `solaranlage-datastore-beta` / `solaranlage-widget` sind stillgelegt; er ist keine aktive Beta mehr. Der ursprüngliche Data-Store-Fehler ist dadurch nicht als behoben ausgewiesen.

Cloudflare: **6 Worker, 2 Datenbanken**. Kontodienst, Bilder und Mein Zuhause bleiben erhalten, ebenso der separate Tageslimit-Warn-Worker. `solaranlage-public-beta` und `solaranlage-display` leiten noch intern auf die neuen Namen weiter. Erst nach Umstellung aller HA-/Alexa-/Bildadressen und Prüfung der bestehenden Haushalte entfernen; danach bleiben vier Worker inklusive Warn-Worker. Keine erneute Kontoverknüpfung ist vorgesehen.

[Offene Abnahme #10](https://github.com/kulmi84/solaranlage-echo-show/issues/10) · [Entwurf PR #9](https://github.com/kulmi84/solaranlage-echo-show/pull/9)
