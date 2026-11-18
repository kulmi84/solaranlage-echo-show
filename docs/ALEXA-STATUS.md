# Projektstatus · 18.11.2026

- **Store: 1.1.0 (Build 1811), von Amazon als Live bestätigt.** Kleine Kachel und Vollbild verwenden direkte Textwerte statt Zahlenbildern.
- **DEV 1811 bleibt separat erhalten.** Werteanzeige, automatische Aktualisierung, Einblendabruf und Vollbild per Tipp sind am Echo bestätigt.
- **Store-Fehler offen:** Beschriftungen sichtbar, Messwerte fehlen. Vollbild per Tipp funktioniert. Der Neustart beseitigt den Fehler nicht.
- **Amazon-Fall 96266698 aktualisiert:** neue Gerätebeobachtungen, Konfiguration und UTC-Logzeiten übermittelt; zehn Nachträge bestätigt. Exakte historische Alexa-Request-IDs und Präsentations-URIs fehlen und sind als offen benannt.
- **Cloudflare:** Werte-Worker `solaranlage-echo-werte`; bestehende Kontoverknüpfung und Haushalte bleiben erhalten. Bilddienste bleiben bis zum belegten Ende ihrer Nutzung aktiv.

## Offen

1. Store-Werteanzeige und automatische Aktualisierung am Echo nachweisen – [Issue #20](https://github.com/kulmi84/solaranlage-echo-show/issues/20).
2. Amazons Rückmeldung und erforderliche Zustellprüfung auswerten.
3. Danach verbleibende Bildabrufe prüfen und beide alten Bilddienste gesichert stilllegen.

Quellenstand und lokale Prüfungen ersetzen keinen Nachweis am Store-Widget. Drei ununterbrochene Minutenrunden der DEV 1811 sind wegen automatischen Ausblendens nicht vollständig protokolliert; wiederholte Aktualisierung ist nutzerbestätigt.
