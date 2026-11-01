# Ideen und geplante Erweiterungen

Die Nummern bleiben dauerhaft bestehen; neue Ideen erhalten die nächste freie
Nummer. Bestehende Einträge werden beim Erledigen nicht neu nummeriert.

## 1. Test Widget Data Store

**Status:** separate BETA implementiert; Amazon bestätigt am 1. November 2026
um 15:00 Uhr die Testinstallation auf dem Küchen-Echo. Home Assistant überträgt
minütlich echte Werte in die eigene BETA-Datenbank (zuletzt geprüft 15:14 Uhr:
651,9 W PV, 59,2 % Akku). Die Zustellung ans Widget ist noch nicht bestätigt:
Amazon antwortet mit HTTP 500 `DATASTORE_UNAVAILABLE`.

Mit „kleines Widget“ ist die Kachel auf dem Echo-Startbildschirm gemeint.
Die BETA enthält derzeit eine solche Kachel (technisch `WIDGET_M`), keine
Vollbildansicht. Zuerst die zuverlässige Anzeige echter Werte erreichen;
Vollbild und weitere Funktionen erst danach ergänzen. Der Funktionsumfang der
normalen Version ist noch nicht erreicht. Eine spätere Übernahme erfolgt erst
nach erfolgreichem Test und gegebenenfalls erneuter Zertifizierung.

Mit einer separaten Datenbank testen, ob sich Messwerte direkt an ein neues
Widget übertragen lassen – ohne den Umweg über Bilder.

- Eigenständiger Alexa-Skill **Meine Solaranlage BETA**.
- Neues Widget-Paket, eigener Worker, eigene D1-Datenbank und eigene Schlüssel.
- Bestehende kleine und große Widgets und der zur Zertifizierung eingereichte
  Skill bleiben unverändert.
- Home-Assistant-Entitäten dürfen lesend weiterverwendet werden.
- Keine Änderung am vorhandenen HACS-Eintrag. Für diesen Test ist keine
  HACS-Erweiterung nötig; eine spätere Integration erhält einen separaten Eintrag.

Implementierung, Einrichtung und Abnahmekriterien:
[Meine Solaranlage BETA](../solar-widget-beta/README.md).

## 2. Solarwerte auf weiteren Alexa-Geräten per Sprache abfragen

**Status:** umgesetzt am 17. Oktober 2026.

Quelle: Chat „Solaranlage Echo Show Chat“, 17. Oktober 2026.

Über unseren Skill sollen sich Solarwerte auch auf Alexa-Geräten ohne Display
(zum Beispiel einem Echo) gezielt per Sprache abfragen lassen.

Gewünschte Abfragen:

- Aktuelle Produktion / PV-Gesamtleistung inklusive Balkonkraftwerk.
- Akkustand der Solaranlage in Prozent.
- Aktueller Hausverbrauch in Watt bzw. Kilowatt.
- Heutige Gesamtproduktion inklusive BKW seit Mitternacht in Kilowattstunden.
- Heutige Einspeisung seit Mitternacht in Kilowattstunden.

Bedienung:

- „Alexa, frage meine Solaranlage nach der aktuellen Leistung.“
- „Alexa, frage meine Solaranlage nach dem Akkustand.“
- „Alexa, frage meine Solaranlage nach dem aktuellen Verbrauch.“
- „Alexa, frage meine Solaranlage nach der heutigen Gesamtproduktion.“
- „Alexa, frage meine Solaranlage nach der heutigen Einspeisung.“

Die Antwort soll kurz gesprochen werden und den jeweiligen aktuellen Wert
mit Einheit nennen. Fehlende oder veraltete Daten müssen erkennbar bleiben.
Die vorhandene geschützte Messwertquelle soll dafür weiterverwendet werden.

Die Echo-Show-Ansicht bleibt beim normalen Öffnen eine stille Anzeige mit
automatischer Aktualisierung. Gezielte Sprachabfragen sollen zusätzlich möglich
sein und keine Spracheingabe nach jedem Anzeigeabruf auslösen.

`ProductionIntent`, `BatteryIntent`, `ConsumptionIntent`,
`TodayProductionIntent` und `TodayExportIntent` beantworten gezielte Abfragen mit
gesprochenen Einheiten. Ohne Display endet die Sitzung nach der Antwort.
Auf einem Echo Show werden bei einer gezielten Frage die Antwort gesprochen
und die Anzeige geöffnet bzw. aktualisiert, ohne anschließend eine weitere
Spracheingabe anzufordern. Normales Öffnen und automatische Abrufe bleiben still.

Fehlende Werte werden als nicht verfügbar angesagt. Bei veralteten Daten
wird vor dem letzten bekannten Wert ausdrücklich gewarnt. Backend- und
Interaktionsmodell-Tests decken beide Abfragen sowie diese Fehlerfälle ab.

## 3. Einstellungen in der Alexa-App

Geprüft: Die nativen Skill-Einstellungen der Alexa-App lassen sich für einen
Custom Skill nicht um eigene Felder wie Anzeigedauer ergänzen. Keine Umsetzung.

## 4. Zweiter Bildschirm mit Monats- und Jahreswerten

Umgesetzt: Rechts wischen öffnet Monat/Jahr, links wischen führt zurück.
Die Seite zeigt Energiewerte für PV/BKW, Haus, Netz und Akku. Neue Ermittlung
alle sechs Stunden; Live-/Tageswerte bleiben auf der ersten Seite im Minutentakt.
Datenquellen, Zeiträume und Rückkehr stehen in [MONAT-JAHR.md](MONAT-JAHR.md).
