# Solaranlage Echo Werte · Build 1811

Aktueller öffentlicher Quellstand von Werte-Worker, Hosted-Handler und Store-Widget. Kleine Kachel und Vollbild verwenden Textwerte. Store-Version 1.1.0 (Build 1811) ist Live; die Messwerte der kleinen Store-Kachel fehlen weiterhin. DEV 1811 bleibt separat und funktioniert am Echo.

`skill/relay_config.example.json` ist eine deaktivierte Vorlage ohne Zugangsdaten, keine laufende Konfiguration. Bestehende Kontoverknüpfungen und Haushaltsbindungen werden weiterverwendet. Der geschützte `/internal/refresh`-Weg liest nur eine vorhandene aktive Bindung und registriert oder reaktiviert keinen Haushalt ohne OAuth.

`widget-template/` entspricht dem exportierten Store-Paket `SolarAccountImageBuild1211`, Namespace `SolarAccountImagesV3`, Schlüssel `snapshot`. Die ältere Bildfassung verwendete `access`. Der Paketname bleibt für bestehende Installationen erhalten.

Private Konfigurationen, Supportprotokolle und Gerätefotos werden nicht veröffentlicht. Das Aktualisieren dieser Quellen führt kein Deployment aus. Bilddienste bleiben bis zur abgeschlossenen Nutzungsprüfung aktiv.

[Projektstatus](../../docs/ALEXA-STATUS.md) · [Store-Fehler #20](https://github.com/kulmi84/solaranlage-echo-show/issues/20)
