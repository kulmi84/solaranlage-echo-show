# Solaranlage auf dem Echo Show

![Solaranlage](https://raw.githubusercontent.com/kulmi84/solaranlage-echo-show/main/assets/branding/solaranlage-icon-108.png)

**Version 1.0.8:** Bestätigter Bild-Widget-Weg mit großen transparenten Werten, scharfer Empfangszeit und 60-Sekunden-Aktualisierung. Der private Bildzugang läuft ohne täglichen Ablauf. Die allgemeine Amazon-Widget-Auslieferung wartet noch auf die individuelle Kontozuordnung; HACS allein installiert kein Echo-Widget. HA-Funktionen und normale Vollbildansicht bleiben unverändert. [Details](https://github.com/kulmi84/solaranlage-echo-show/blob/main/docs/V1.0.8.md).

**Version 1.0.7:** Zusätzliche Statusansage mit Datenalter: „Alexa, frage meine Solaranlage nach dem Status.“ Zentraler Alexa-Code und Sprachmodell müssen dafür freigegeben sein; HACS allein aktiviert sie nicht. Rücksprungstand ist v1.0.6.

**Anzeige seit Version 1.0.6:** Anzeige bleibt sichtbar, Alexa kann wieder normale Befehle entgegennehmen. Live-Aktualisierung alle 60 Sekunden mit eigenem Anzeigezugang für bis zu 24 Stunden. Wetter und andere Alexa-Karten können die Ansicht ersetzen.

Native Kacheln für PV und BKW, Hausverbrauch, Netz und Akku.

**Starten: „Alexa, öffne meine Solaranlage.“**

## Live und Heute

![Live- und Tageswerte](https://raw.githubusercontent.com/kulmi84/solaranlage-echo-show/main/docs/screenshots/v1-live-heute.webp)

## Monat und Jahr

![Monats- und Jahreswerte](https://raw.githubusercontent.com/kulmi84/solaranlage-echo-show/main/docs/screenshots/v1-monat-jahr.webp)

## Installation

**Stand 28. Oktober 2026:** Der normale [Alexa-Skill Solaranlage](https://www.amazon.de/dp/B0HN5CSTW6/) ist Live. Das neue Bild-Widget ist separat vorbereitet und noch nicht allgemein im Store veröffentlicht. HACS allein installiert weder Skill noch Widget.

1. Solaranlage Echo Show über HACS herunterladen und HA neu starten.
2. Unter Geräte & Dienste die Integration hinzufügen, Relay-Einladung eingeben und Sensoren auswählen.
3. In den Optionen **Alexa verbinden** öffnen und den einmaligen Code in der Alexa-App beim Skill **Solaranlage** einfügen.
4. **„Alexa, öffne meine Solaranlage.“**

[Ausführliche HACS-Anleitung](https://github.com/kulmi84/solaranlage-echo-show/blob/main/docs/HACS.md)

Das gemeinsame Relay benötigt eine persönliche Einladung und ist zunächst auf
20 Haushalte begrenzt. Bitte vor der Einrichtung unter support@dorisundmarcin.de
nach einer freien Einladung fragen. Die bestehende Kontoverknüpfung bleibt bei
Updates erhalten. Interne Dateinamen mit „beta“ sind aus Kompatibilitätsgründen unverändert.

[Alexa-Veröffentlichungsstatus](https://github.com/kulmi84/solaranlage-echo-show/blob/main/docs/ALEXA-STATUS.md) ·
[Datenschutz](https://solaranlage-public-beta.kulmi84.workers.dev/privacy) ·
[Kontakt](https://solaranlage-public-beta.kulmi84.workers.dev/contact)
