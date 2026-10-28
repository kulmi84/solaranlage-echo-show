# Alexa-Skill: Verfügbarkeit und Einrichtung

## Stand vom 28. Oktober 2026

Der normale Skill **Solaranlage** wird in der Amazon-Konsole als **Live** geführt.
[Öffentlicher Skill im Alexa Store](https://www.amazon.de/dp/B0HN5CSTW6/).
Daneben gibt es einen getrennten **In Dev**-Stand. Das ist keine zweite öffentliche Installation.

Das neu bestätigte Bild-Widget ist derzeit privat eingerichtet. Für seine allgemeine Store-Auslieferung fehlt noch die automatische individuelle Bildzugangsbereitstellung pro Konto. Es wurde mit dieser GitHub-/HACS-Version nicht als gemeinsames Paket eingereicht. Private Bildadressen einer Anlage dürfen nicht an alle Nutzer verteilt werden. Diese datierte Statusseite ist keine automatische Live-Abfrage.

## Was andere Nutzer benötigen

- Home Assistant mit HACS und der Integration **Solaranlage Echo Show**.
- Eigene Leistungs- und Energiezähler; optionale Akku- und Netzsensoren.
- Eine persönliche Relay-Einladung: support@dorisundmarcin.de.
  Der gemeinsame Dienst ist zunächst auf **20 Haushalte** begrenzt.
- Den gemeinsamen Alexa-Skill nach dessen Store-Freigabe. Für die Anzeige einen
  Echo Show; Sprachabfragen funktionieren auch auf Geräten ohne Bildschirm.

**HACS installiert die Home-Assistant-Integration, nicht den Alexa-Skill.**
Die öffentliche GitHub-Verfügbarkeit bedeutet daher noch nicht, dass beliebige
Amazon-Konten den eingereichten Skill bereits aktivieren können.

Nach der Freigabe: Einladung anfragen → HACS-Integration installieren → Sensoren
auswählen → Alexa-Skill aktivieren → in HA **Alexa verbinden** öffnen → den
einmaligen Code in die Kontoverknüpfung der Alexa-App kopieren.

Für diesen gemeinsamen Dienst brauchen Nutzer weder einen eigenen Alexa-
Entwickler-Skill noch ein eigenes Cloudflare-Konto. Bis zur Freigabe bleibt
die dokumentierte [eigene Infrastruktur](EINFACH-EINRICHTEN.md) eine Alternative;
ein Amazon-Beta-Test wäre nur eine zeitlich begrenzte Testmöglichkeit.

## Bereits verbundene Nutzer

Aufruf: **„Alexa, öffne meine Solaranlage.“** Bestehende Kontoverknüpfungen und
Sensoren bleiben erhalten. **Solaranlage Archiv** ist die ältere unabhängige
Einzelanlagen-Version und wird für den aktuellen Skill nicht benötigt.

## Datenschutz und Kontakt

- [Datenschutzhinweise](https://solaranlage-public-beta.kulmi84.workers.dev/privacy)
- [Kontakt und Einladungen](https://solaranlage-public-beta.kulmi84.workers.dev/contact)
- [Bebilderte HACS-Anleitung](HACS.md)
- [Sprachbefehle und Bedienung](ANLEITUNG.md)

Die öffentlichen Projektseiten nennen Marcin Kulmaczewski und
support@dorisundmarcin.de. Eine Privatanschrift wird dort nicht veröffentlicht.
