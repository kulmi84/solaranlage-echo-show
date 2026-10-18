# Ideen und geplante Erweiterungen

## Idee 1: Solarwerte auf weiteren Alexa-Geräten per Sprache abfragen

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
