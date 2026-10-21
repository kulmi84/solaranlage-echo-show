# Archiv: v1.0.5 – native APL-Anzeige mit Live-Werten

Dieser Zweig bewahrt den Produktions-Code vor der Umstellung auf bildbasierte Wertebereiche. Die Sicherung wurde am 21. Oktober 2026 angelegt. Die laufende Produktion wurde dabei nicht geändert.

- Unveränderter Code-Ausgangspunkt: `18116ecf13288180a4efda0365a268daf994a49c`
- Bestehender Tag und Release: [v1.0.5](https://github.com/kulmi84/solaranlage-echo-show/releases/tag/v1.0.5)
- Darstellung: native APL-Texte und Kacheln mit echten Messwerten, keine PNG-Wertebilder und kein zusätzlicher Bild-Testworker.
- Diese Archivkennzeichnung ergänzt nur Dokumentation; der Anwendungscode bleibt auf dem Ausgangsstand.
- v1.0.4 bleibt ebenfalls erhalten.

## Bekannte Grenze dieses Standes

Die Sprachsitzung wird beim Öffnen beendet, während das APL-Dashboard sichtbar bleibt. Nach geschlossener Sitzung funktionierte die bisherige SendEvent-basierte Bildschirmaktualisierung auf dem Echo Show nicht zuverlässig. Diese Einschränkung wird mit archiviert; das Archiv ist keine neue Fehlerbehebung.

## Rückkehr zu diesem Stand

Den Alexa-Code und die zugehörigen Dateien aus Tag v1.0.5 bzw. dem oben genannten Commit bauen und im gewünschten Alexa-Endpunkt bereitstellen. Ein HACS-Downgrade allein setzt den zentral bereitgestellten Alexa-Code nicht zurück. Private Kontoverknüpfungs- und Relay-Konfigurationen müssen aus der vorhandenen privaten Sicherung übernommen werden; sie gehören nicht ins öffentliche Repository.

Die lokale private Komplettsicherung von v1.0.5 bleibt zusätzlich bestehen. Sie enthält die privaten Konfigurationen und ist absichtlich nicht auf GitHub veröffentlicht.

## Rolle eines Pull Requests

Ein Pull Request würde später die Änderungen der getesteten Bildvariante gegenüber dem bisherigen Code zeigen und vor einer Übernahme prüfen lassen. Er ersetzt weder diesen Archivzweig noch den Release-Tag. Das Zusammenführen eines Pull Requests stellt außerdem nicht automatisch den Alexa-Skill bereit, sofern dafür keine entsprechende Bereitstellungsautomatik eingerichtet ist.

Dieses Archiv enthält keine Übernahme der aktuellen Bild-Beta und löst keine Produktionsbereitstellung aus.
