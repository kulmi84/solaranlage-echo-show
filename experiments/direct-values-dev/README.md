# Textwerte in Development: 1.1.0 (Build 1611.7)

Dieser getrennte Entwicklungsstand ersetzt die vier Messwertbilder der kleinen Kachel durch native Textwerte. Die Vollbildansicht rendert ebenfalls Text. Der sichtbare Versionshinweis lautet DEV · 1.1.0 (Build 1611.7); Amazons interne Paketversion lautet 1.1.7.

## Datenweg und Kosten

Die kleine Kachel liest Solar, Hausverbrauch, Akku und Messzeit gemeinsam aus SolarDirectValuesDev/snapshot. Ein separater Worker stellt das vollständige Objekt jede Minute zu: eine Worker-Ausführung, ein D1-SELECT und zwei Amazon-Anfragen (Token und Datenspeicherauftrag). Keine Bildabrufe und keine internen Worker-Weiterleitungen.

Das DEV-Vollbild ruft GET /v1/pv desselben DEV-Workers auf. Ein einzelner parametrisierter SELECT prüft gleichzeitig den bestehenden OAuth-Zugang, dessen Laufzeit, den ausdrücklich freigegebenen aktiven Haushalt und dessen Generation und liefert Live-/Tages-/Historienwerte zusammen. Ein gemessener erfolgreicher Vollbildabruf benötigte eine Worker-Ausführung und einen D1-SELECT, ohne Bildabrufe oder interne Weiterleitungen.

Bei fehlgeschlagenen kleinen Aktualisierungen bleibt das letzte gültige Objekt erhalten. Beim fehlgeschlagenen Vollbild-Refresh wird keine Ersetzungsanweisung gesendet. Ursprüngliche Messzeiten bleiben erhalten; alte Quelldaten werden als veraltet gekennzeichnet.

## Abnahme

Am Echo bestätigt: native Textwerte der kleinen Kachel, automatische Aktualisierung und Öffnen des DEV-Vollbilds per Antippen. Der passende Vollbild-Datenabruf wurde mit HTTP 200 und den oben genannten Zählern protokolliert. Drei kontrolliert wechselnde Datensätze und Fehlerfälle wurden lokal geprüft.

Offen: optischer Detailvergleich mit identischen Testwerten, längerer Vollbild-Dauerlauf und spätere Live-Abnahme. Dieser Stand ist kein Store-Update und keine allgemeine Migration bestehender Haushalte. Der ältere Bildstand bleibt als Rückweg gesichert.

## Quellen und Konfiguration

lambda_function.py ist ein Snapshot des laufenden Development-Handlers einschließlich bestehender Bildpfade. Der private Diagnose-Korrelationsschlüssel wurde für diese öffentliche Kopie durch einen neutralen Beispielwert ersetzt. Keine reale Konfiguration, Zugangsdaten, Geräte-/Haushaltszuordnung, privaten Protokolle oder Backups veröffentlichen.

relay_config.example.json und wrangler.example.jsonc sind Vorlagen. Die laufende Instanz ist bewusst auf einen ausdrücklich freigegebenen Testhaushalt begrenzt. Im Worker werden ALEXA_CLIENT_ID, ALEXA_CLIENT_SECRET und DEV_TARGET als Secrets benötigt. DEV_TARGET enthält device, household und generation (SHA-256 des aktuellen gespeicherten write_hash). Keine neuen Tokens oder Haushalte für das Beispiel erzeugen. Bestehende Kontoverknüpfung verwenden.

Amazons Hosted-Runtime verwendet Python 3.8. Deshalb wird dateutil.tz mit python-dateutil==2.8.2 statt zoneinfo verwendet. Winter-/Sommerzeit und Kaltstart gesondert prüfen. Build- und Installationsbestätigungen ersetzen keinen Gerätenachweis.

Die zuvor gespeicherten Amazon-Geräte- und Kontobezeichner waren keine verlässliche alleinige Freigabe für den ankommenden Widget-Tipp. Die Datenquelle prüft deshalb die tatsächliche Haushaltsberechtigung beim Abruf. Eigene Skill-/Paketkennung und Development-Stage bleiben eingeschränkt.

## Lokale Prüfungen

Aus diesem Verzeichnis: python -B -m unittest test_dev_text.py und node --test worker.test.mjs. Die Tests verwenden synthetische Daten und rufen keine Cloud-Dienste auf. Vor dem Python-Test die gepinnten Anforderungen in einer eigenen Umgebung bereitstellen.

Kein automatisches Deployment aus diesem Verzeichnis. Quellen vor Paketwechsel sichern, neue Paketkennung abstimmen und ein geändertes Dokument am Echo anhand der Versionszeile prüfen. Eine Änderung am Hauptzweig oder eine Store-Veröffentlichung gehört nicht zu diesem Entwicklungs-PR.
