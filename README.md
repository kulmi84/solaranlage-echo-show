# Solaranlage auf dem Echo Show

**HACS 1.0.13 · Bildwidget 2.0.1**

Solar-, Verbrauchs-, Akku- und Energiewerte aus Home Assistant auf dem Echo Show: als Vollbildansicht und Alexa+-kompatibles Widget. Sprachansagen funktionieren auch auf Alexa-Geräten ohne Display.

- Live- und Tageswerte sowie Monats- und Jahresübersichten.
- Automatische Aktualisierung mit sichtbarem Datenstand.
- Sensorauswahl und einmalige Kontoverknüpfung.
- Sprachabfragen, etwa: „Alexa, frage meine Solaranlage nach dem Akkustand.“

## Kleines Widget

Solarleistung, Hausverbrauch und Akkustand direkt auf dem Startbildschirm. Der bisherige Bildsatz bleibt stehen, bis der neue vollständig geladen ist.

![Solaranlage-Widget auf dem Echo Show](docs/screenshots/echo-show-widget-2.0.1.png)

## Vollbildansicht

PV und BKW, Hausverbrauch, Netz und Akku sowie Tageswerte im Überblick.

![Vollbildansicht mit Live- und Tageswerten](docs/screenshots/v1-live-heute.webp)

### Livewerte

Die aktuellen Leistungswerte und der Akkustand auf einen Blick.

![Livewerte für PV, Hausverbrauch, Netz und Akku](docs/screenshots/02-livewerte.png)

### Tageswerte

Erzeugung, Verbrauch sowie Netz- und Akkuenergie seit Mitternacht.

![Tageswerte seit Mitternacht](docs/screenshots/03-tageswerte.png)

### Monat und Jahr

Energieübersichten für den laufenden Monat und das Jahr auf der zweiten Seite.

![Jahresübersicht der Energiewerte](docs/screenshots/05-jahreswerte.png)

Die Abbildungen zeigen Momentaufnahmen. Das kleine Widget ist ein Gerätefoto; die Vollbildansichten sind Bildschirmaufnahmen.

## Einrichtung und Informationen

[In HACS hinzufügen](https://my.home-assistant.io/redirect/hacs_repository/?owner=kulmi84&repository=solaranlage-echo-show&category=integration) · [Einrichtung](docs/HACS.md) · [Bebilderte Anleitung](docs/ANLEITUNG.md)

HACS installiert die Home-Assistant-Integration. Alexa-Skill und Widget werden separat bereitgestellt. Den aktuellen Stand und die noch offenen Schritte findest du im [Projektstatus](docs/ALEXA-STATUS.md).

[Ausführlicher Änderungsverlauf](CHANGELOG.md) · [Eigene Infrastruktur](docs/EINFACH-EINRICHTEN.md) · [Datenschutz](https://solaranlage-kontodienst.kulmi84.workers.dev/privacy) · [Lizenz](LICENSE)
