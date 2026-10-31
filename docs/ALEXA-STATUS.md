# Projektstatus · 31.10.2026

## Widget und HACS

- **Bildwidget 2.0.1:** gemeinsamer Kontozugang, sofortiges Nachladen beim Einblenden, automatische Zugangserneuerung, vollständiger Bildpuffer bei Fehlern und richtige Vollbild-Zuordnung am Gerät bestätigt.
- Weiße Zeile „2.0.1 · Live · alle 60 Sekunden“ unter dem Zeitstand: Amazon-Build und einmaliger Installationsauftrag bestätigt; tatsächliche Geräteansicht noch offen.
- **HACS 1.0.9 vorbereitet, nicht veröffentlicht:** automatische Adressübernahme mit erhaltenen Konten/Sensoren sowie klarere PV-/BKW-Feldnamen und Hilfen. 13 HACS- und 11 Bilddienst-Tests bestanden.
- Einladung bleibt vorerst bestehen. Vereinfachte Einrichtung und zweiter Haushalt sind noch zu testen. Keine neue öffentliche Widget-Freigabe.

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
