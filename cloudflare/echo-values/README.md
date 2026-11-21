# Solaranlage Echo Werte · Build 2311

Store-Update **1.1.0 (Build 2311)** ist am 21.11.2026 bei Amazon in Zertifizierung, mit automatischer Veröffentlichung nach Freigabe. Noch keine bestätigte Store-Freigabe. Separate DEV bleibt Build 1811.

Die Sprachsitzung wird nach Start, Tipp, automatischen Updates und Fallback beendet, ohne die APL-Anzeige ausdrücklich zu schließen. Layout, Datenversorgung, bestehende Store-Paketkennung und DEV-Dokument bleiben erhalten. Kleine Kachel und Vollbild verwenden direkte Werte. Der erneute Echo-Test der Sprachfreigabe und weiteren Aktualisierung ist offen.

Technische Store-Paketversion: 1.1.1 bei unveränderter Paketkennung SolarAccountImageBuild1211. Die sichtbare Skillversion bleibt 1.1.0 (Build 2311). Vorherstand, private Konfiguration und vollständige Cloud-Sicherung liegen ausschließlich lokal.

Prüfen: `python -m unittest discover -s . -p "test_*.py"` und `node --test worker.test.mjs`. Kein automatisches Deployment aus GitHub.

[Projektstatus](../../docs/ALEXA-STATUS.md) · [Vorheriger Referenzstand](../../docs/ALEXA-BESTAETIGTER-STAND-1811.md)
