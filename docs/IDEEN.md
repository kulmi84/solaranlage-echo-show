# Ideen und geplante Erweiterungen

## Idee 1: Solarwerte auf weiteren Alexa-Geräten per Sprache abfragen

**Status:** aufgenommen, noch nicht umgesetzt.

Quelle: Chat „Solaranlage Echo Show Chat“, 17. Oktober 2026.

Über unseren Skill sollen sich Solarwerte auch auf Alexa-Geräten ohne Display
(zum Beispiel einem Echo) gezielt per Sprache abfragen lassen.

Gewünschte Abfragen:

- Aktuelle Produktion / PV-Gesamtleistung inklusive Balkonkraftwerk.
- Akkustand der Solaranlage in Prozent.

Beispiele für die geplante Bedienung:

- „Alexa, frage meine Solaranlage nach der aktuellen Produktion.“
- „Alexa, frage meine Solaranlage nach dem Akkustand.“

Die Antwort soll kurz gesprochen werden und den jeweiligen aktuellen Wert
mit Einheit nennen. Fehlende oder veraltete Daten müssen erkennbar bleiben.
Die vorhandene geschützte Messwertquelle soll dafür weiterverwendet werden.

Die Echo-Show-Ansicht bleibt beim normalen Öffnen eine stille Anzeige mit
automatischer Aktualisierung. Gezielte Sprachabfragen sollen zusätzlich möglich
sein und keine Spracheingabe nach jedem Anzeigeabruf auslösen.

Bereits vorhanden ist eine allgemeine gesprochene Zusammenfassung für Geräte
ohne APL-Display. Idee 1 ergänzt gezielte Abfragen einzelner Werte; eigene
Intents, Formulierungen und Tests auf einem Echo stehen dafür noch aus.
