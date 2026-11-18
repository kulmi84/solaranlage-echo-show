# Solaranlage auf dem Echo Show

> **Stand 18.11.2026:** Store **1.1.0 (Build 1811)** ist Live und verwendet Textwerte. Die kleine Store-Kachel bleibt ohne Messwerte; DEV 1811 und Vollbild funktionieren. [Aktueller Projektstatus](docs/ALEXA-STATUS.md) · [Fehler #20](https://github.com/kulmi84/solaranlage-echo-show/issues/20).

**HACS 1.0.15 Â· Bildwidget 2.0.1**

Solar-, Verbrauchs-, Akku- und Energiewerte aus Home Assistant auf dem Echo Show: als Vollbildansicht und Alexa+-kompatibles Widget. Sprachansagen funktionieren auch auf Alexa-GerÃ¤ten ohne Display.

- Live- und Tageswerte sowie Monats- und JahresÃ¼bersichten.
- Automatische Aktualisierung mit sichtbarem Datenstand.
- Sensorauswahl und einmalige KontoverknÃ¼pfung.
- Sprachabfragen, etwa: â€žAlexa, frage meine Solaranlage nach dem Akkustand.â€œ

## Kleines Widget

Solarleistung, Hausverbrauch und Akkustand direkt auf dem Startbildschirm. Der bisherige Bildsatz bleibt stehen, bis der neue vollstÃ¤ndig geladen ist.

![Solaranlage-Widget auf dem Echo Show](docs/screenshots/echo-show-widget-2.0.1.png)

## Vollbildansicht

PV und BKW, Hausverbrauch, Netz und Akku sowie Tageswerte im Ãœberblick.

![Vollbildansicht mit Live- und Tageswerten](docs/screenshots/v1-live-heute.webp)

### Livewerte

Die aktuellen Leistungswerte und der Akkustand auf einen Blick.

![Livewerte fÃ¼r PV, Hausverbrauch, Netz und Akku](docs/screenshots/02-livewerte.png)

### Tageswerte

Erzeugung, Verbrauch sowie Netz- und Akkuenergie seit Mitternacht.

![Tageswerte seit Mitternacht](docs/screenshots/03-tageswerte.png)

### Monat und Jahr

EnergieÃ¼bersichten fÃ¼r den laufenden Monat und das Jahr auf der zweiten Seite.

![JahresÃ¼bersicht der Energiewerte](docs/screenshots/05-jahreswerte.png)

Die Abbildungen zeigen Momentaufnahmen. Das kleine Widget ist ein GerÃ¤tefoto; die Vollbildansichten sind Bildschirmaufnahmen.

## Einrichtung und Informationen

[In HACS hinzufÃ¼gen](https://my.home-assistant.io/redirect/hacs_repository/?owner=kulmi84&repository=solaranlage-echo-show&category=integration) Â· [Einrichtung](docs/HACS.md) Â· [Bebilderte Anleitung](docs/ANLEITUNG.md)

HACS installiert die Home-Assistant-Integration. Alexa-Skill und Widget werden separat bereitgestellt. Den aktuellen Stand und die noch offenen Schritte findest du im [Projektstatus](docs/ALEXA-STATUS.md).

[AusfÃ¼hrlicher Ã„nderungsverlauf](CHANGELOG.md) Â· [Eigene Infrastruktur](docs/EINFACH-EINRICHTEN.md) Â· [Datenschutz](https://solaranlage-kontodienst.kulmi84.workers.dev/privacy) Â· [Lizenz](LICENSE)

## Aktueller Development-Test

[DEV 1.1.0: native Textwerte und Vollbild per Tipp](docs/DEV-TEXTWERTE-1.1.0.md). Separater Teststand; keine Änderung der Store-Veröffentlichung.
