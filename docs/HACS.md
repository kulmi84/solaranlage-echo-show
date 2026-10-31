# Solaranlage Echo Show über HACS

Aktuell veröffentlicht: **1.0.11**. Bestehende Einrichtungen und Alexa-Verknüpfungen bleiben erhalten.

## Einrichten

1. [Direkt in HACS öffnen](https://my.home-assistant.io/redirect/hacs_repository/?owner=kulmi84&repository=solaranlage-echo-show&category=integration), herunterladen und Home Assistant neu starten. Das Projekt ist noch nicht im HACS-Standardkatalog.
2. Einstellungen → Geräte & Dienste → Integration hinzufügen → **Solaranlage Echo Show**. Den Standarddienst beibehalten; die Option für einen eigenen Dienst ausgeschaltet lassen. Kein eigenes Cloudflare-Konto erforderlich.
3. **Live-Sensoren:** Gesamte Solarleistung in W/kW ist Pflicht. Hausverbrauch, Netz, Akkustand (%) und getrennte PV-/BKW-Werte sind optional. Ohne BKW genügt beim Gesamtwert die PV-Leistung; Einzelwerte werden nicht automatisch addiert.
4. **Energiezähler:** separate Seite für kumulierte Zähler in Wh/kWh/MWh mit `total` oder `total_increasing`. Keine Leistungssensoren in W eintragen. Diese Felder dürfen leer bleiben; fehlende Energieangaben bleiben unbekannt.
5. Speicherhinweis lesen und **Verbinden und übertragen** wählen. Keine zusätzliche Zustimmungscheckbox. Am gemeinsamen Dienst ist keine Einladung erforderlich; Kapazitäts- und IP-Grenzen gelten.
6. In den Integrationsoptionen **Alexa verbinden** wählen. Den einmaligen Code in der Alexa-Kontoverknüpfung einfügen; er gilt zehn Minuten.

Aufruf: **„Alexa, öffne meine Solaranlage.“** Sprachfragen funktionieren auch ohne Display.

HACS installiert die HA-Integration. Das Bildwidget 2.0.1 ist am Gerät im separaten Skill bestätigt; seine allgemeine Amazon-Auslieferung bleibt offen. [Aktueller Status](ALEXA-STATUS.md).

## Speicherung und Updates

Live-/Tageswerte ersetzen beim erfolgreichen Upload den bisherigen Stand, normalerweise alle 60 Sekunden. Monats-/Jahressummen aus HA ersetzen etwa alle sechs Stunden ihren vorherigen Stand. Der Dienst baut keine Messwert-Zeitreihe auf. Bei einem ausgefallenen Upload bleibt der letzte empfangene Stand gespeichert.

Ein HACS-Update erfordert einen HA-Neustart, aber keine neue Kontoanlage oder Alexa-Verknüpfung. Die neue Dienstadresse wird bei bestehenden Einträgen erst nach erfolgreicher Prüfung übernommen. Eigene Server werden nicht umgestellt.

## Löschen und neu einrichten

In den Optionen **Relay-Daten und Verknüpfung löschen** entfernt nach Bestätigung die Messwerte und Zugangsberechtigungen des Haushalts. Die eigentlichen HA-Sensoren bleiben erhalten. Danach die Integration entfernen. Eine bewusste Neueinrichtung am gemeinsamen Dienst erzeugt einen neuen Haushalt ohne Einladung. Das bloße Entfernen der Integration löscht die Daten beim Dienst nicht.

## Eigener Solaranlage-Dienst

Die Expertenoption ist für einen selbst betriebenen kompatiblen Kontodienst mit eigener Adresse. [Anleitung für eigene Infrastruktur](EINFACH-EINRICHTEN.md) · [Betreiberhinweise](PUBLIC-ENROLLMENT.md).

[Bedienung](ANLEITUNG.md) · [Datenschutz](https://solaranlage-kontodienst.kulmi84.workers.dev/privacy) · [Kontakt](https://solaranlage-kontodienst.kulmi84.workers.dev/contact)
