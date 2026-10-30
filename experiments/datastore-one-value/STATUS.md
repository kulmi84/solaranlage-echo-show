# Data-Store-Einwert-Reproducer: aktueller Stand

Der Reproducer dokumentiert einen einzelnen Wert und trennt Schreibbestätigung von tatsächlichem Leseerfolg.

## Vergleich

- Im ursprünglichen Skill blieb der Reader bei „Objekt fehlt“.
- Im separaten Labor-Skill wurden sowohl ein Authoring-Schreibvorgang als auch ein anschließender externer REST-Schreibvorgang im bereits installierten Reader sichtbar.
- Der Vergleich grenzt den Fehler ein, belegt aber keine Reparatur der ursprünglichen Skill-Zuordnung.

## Folgeentwicklung

Der separate funktionierende Data-Store-Weg ist Grundlage des kontogebundenen Bildwidgets 2.0.0. Werteanzeige und automatische Aktualisierung wurden bestätigt. Die Wiederaufnahme-Korrektur 2.0.1 ist noch nicht am Gerät abgenommen.

Alle sieben offenen Abnahme- und Veröffentlichungspunkte stehen in [Issue #10](https://github.com/kulmi84/solaranlage-echo-show/issues/10#issuecomment-6532539414).

Dieses Beispiel bleibt ein unabhängiger Reproducer. Es enthält keine Bildzugänge, keine private Konfiguration und keine Freigabe für einen allgemeinen Rollout. Frühere Dateistände bleiben in der Git-Historie erhalten.
