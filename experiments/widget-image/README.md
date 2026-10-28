# Solaranlage: kontogebundenes Bild-Widget

Das Widget zeigt die Werte derselben verknüpften Anlage wie die normale Vollbildansicht. Es benötigt keine zweite Einrichtung, keine weitere Einladung und keinen persönlichen Widget-Schlüssel. Die bestehende Kontoverknüpfung des normalen Skills reicht aus.

![Freigegebenes Layout mit großer Schrift und Empfangszeit](assets/layout-status-preview.png)

## Ablauf

1. Beim Anzeigen fordert das Widget mit `solar.widget.images.v1` im INLINE-Modus still einen Bildzugang an.
2. Der normale Skill prüft Skill-ID und Widget-Paket und verwendet denselben Account-Link-Token und dieselbe Funktion `create_image_session` wie Vollbild.
3. Die Antwort setzt die geschützten Bildadressen ausschließlich in dieser Widget-Instanz. Sie öffnet kein Vollbild und spricht nichts.
4. Die drei transparenten Wertebilder und die scharfe Stand-Zeile werden alle 60 Sekunden neu geladen, solange Alexa den Widget-Timer ausführt.
5. Der zeitlich begrenzte Zugang wird vor Ablauf still erneuert. Nach einem Neustart beginnt die Anmeldung erneut. Bei vorübergehenden Fehlern bleiben die bisherigen Bildadressen erhalten, statt sie aktiv zu leeren.
6. Antippen öffnet die vorhandene normale Vollbildansicht.

## Dieselben Daten und Berechtigungen

`/widget/value.png` und `/widget/status.png` gehören zum bestehenden Display-Worker. Sie verwenden dieselbe verschlüsselte Freigabe, dieselbe Datenbank und dieselbe exakte Haushaltszuordnung wie Vollbild. Die Freigabe wird vor jedem Datenbankabruf geprüft. Deaktivierte Haushalte und geänderte Widerrufskennungen werden abgewiesen. Keine weitere Datenbank, kein zusätzlicher Data Store und keine Schreiboperationen sind dafür nötig.

Das gemeinsame Amazon-Paket enthält **keine privaten Bildadressen oder Zugangsschlüssel**. Erst die vorhandene Kontoverknüpfung liefert zur Laufzeit einen eigenen Zugang je Konto. Ohne Kontoverknüpfung erscheint ein entsprechender Hinweis. Private Konfigurationen und die von Amazon gesicherten Lambda-Dateien gehören niemals ins Repository.

## Stand am 28. Oktober 2026

Kandidat mit Paket `SolarImageStatus102` **1.1.0** und unverändertem freigegebenem Layout. Development-Code erfolgreich bereitgestellt, Amazon-Build erfolgreich, Testinstallation auf Echo Küche bestätigt. Der Betreiber bestätigt aktuelle Werte auf dem Gerät nach der automatischen Anmeldung. Die neue Erneuerung ist lokal getestet, aber noch nicht durch einen mehrtägigen Gerätetest bestätigt. Diese Angaben bedeuten keine allgemeine Store-Freigabe. HACS installiert die HA-Integration; die zentrale Skill-/Widget-Bereitstellung erfolgt separat über Amazon.

Der vorher bestätigte private Bild-Prototyp aus v1.0.8 bleibt als Rücksprungstand erhalten. Der frühere Data-Store-Fehler wird mit diesem Bildweg umgangen; seine Amazon-Ursache ist weiterhin ungeklärt. Weitere Data-Store-Versuche gehören ausschließlich in die separate Beta.

## Build und Tests

```powershell
python build_skill.py
python experiments/widget-image/build_widget.py --output dist/widget
python -m unittest test_widget_account test_image_display test_status_speech test_beta_live
node cloudflare/display/widget-images.test.mjs
```

Der Widget-Builder benötigt keine private Bildkonfiguration. Die Lambda-Laufzeit verwendet die bereits für Vollbild vorhandene private `relay_config.json`. Die zusätzlichen Worker-Routen benötigen die bestehenden Bindungen `DISPLAY_KEY` und `DISPLAY_DB`; keine neuen Secrets.

Geprüft: zwei getrennte Beispielkonten, abgelaufene/manipulierte Freigaben, Widerruf, eingeschränkte Spalten, Statuszeit, stille Antworten, fehlende Verknüpfung und Durchleitung der bisherigen Sprach-/Vollbild-Anfragen. Bestehende Vollbild-HTTP-Antworten bleiben im Vergleich unverändert. Reale HTTPS-Abrufe der zusätzlichen Bildrouten waren erfolgreich.

## Nachlade-Korrektur 1.1.1 (Development)

Unten beim Stand steht der Link „Aktualisieren“. Er lädt die Bilder manuell nach, ohne Vollbild zu öffnen. Ein zweiter, unsichtbarer Bildsatz wird geladen; erst nach erfolgreichem Laden aller drei Werte und der Stand-Zeile wird vollständig umgeschaltet. Bei Fehler oder Zeitüberschreitung bleibt der letzte erfolgreiche Bildsatz einschließlich seines alten Zeitstempels sichtbar. Automatischer Wiederholungsversuch nach 10 Sekunden; normale Aktualisierung alle 60 Sekunden. Der neue Code ist getrennt von der bereits eingereichten Version 1.1.0. Die laufende Amazon-Prüfung wird nicht zurückgezogen.

### Gerätekorrektur1.1.2

Der1.1.1-Gerätetest zeigte einen sichtbaren, aber wirkungslosen Link und keine Werte. Deshalb keineEinreichung.1.1.2 trennt den Aktualisieren-Touchbereich vom Vollbild-Touchbereich und verwendet flache Bildadress-/Nonce-Bindungen mit direkt eingebetteten Standardkommandos. Das vermeidet verschachtelte Objekt-/Custom-Command-Auswertung.51lokaleTests bestanden;Geräteergebnis noch offen.
