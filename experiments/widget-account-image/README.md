# Kontobildwidget 2.0.1 – Entwicklungsstand

Aktuelles kontoneutrales APL-Dokument, Paketmanifest und isolierte Router-/Publisher-Bausteine des geprüften Bildwegs. Keine privaten Bildzugänge oder produktiven Lambda-Kopien enthalten.

Die einmalige Kontoverknüpfung liefert einen kurzlebigen Bildzugang über `SolarAccountImages/access`. Messwerte und Zeitstand werden als Bilder geladen; der letzte komplette Bildsatz bleibt bis zum vollständigen Nachladen erhalten. Der entfernte alte Data-Store-Zahlenversuch ist davon getrennt.

Am Gerät bestätigt: Nachladen beim Einblenden, automatische Erneuerung nach echtem Ablauf, Fehlerpuffer und richtige Vollbild-Zuordnung. Die weiße Fußzeile unter dem Stand wurde gebaut/gesendet; Gerätebestätigung noch offen. Dies ist noch keine öffentliche Freigabe und kein Ersatz für die abschließende Runtime-Integration in PR #9.

Tests: `python -m unittest discover -s experiments/widget-account-image -p "test_*.py"` (nur Fixtures, kein Netzwerk). Publisher-Zugangsdaten gehören ausschließlich in private Betriebskonfiguration; nie ins Widgetpaket.

[Offene Punkte #10](https://github.com/kulmi84/solaranlage-echo-show/issues/10) · [Projektstatus](../../docs/ALEXA-STATUS.md)
