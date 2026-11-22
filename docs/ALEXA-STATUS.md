# Projektstatus · 22.11.2026

- **1.1.0 (Build 2211)** um20:28 Berlin erneut eingereicht: **CERTIFICATION / In review**, automatische Veröffentlichung nach Amazon-Freigabe. Vorherige Prüfung zurückgezogen; noch nicht veröffentlicht.
- Ruhemodus mit Handler und Worker ausgerollt. Nach sechs bestätigten erfolglosen Registrierungen pausiert die leere Store-Kachel. Sicherer Wiederanlauf nach erfolgreicher Verknüpfung oder authentifiziertem Store-Vollbildstart; Berechtigung wird frisch geprüft. [Umfang und Grenzen](ALEXA-KACHEL-VERBINDUNG.md).
- Worker `c10cc302`, zusätzliche Status-Tabelle und Aktivierungsflag aktiv. Handler20:25 in Development und20:27 nach Live übernommen. Bestehender Cron bleibt erhalten.
- DEV-Paket, Sprachmodell und andere Pakete nach Import bytegleich geprüft. DEV-Verhalten, Sprache, Layout bei Verbindung und Vollbild unverändert; keine Konten-/Testmodusänderung oder Reaktivierung.
- 215 Python-/73 Worker-/73 Bündeltests und Amazon-Pflichtvalidierung erfolgreich. **Echo-Abnahme der neuen Ruhefunktion und Veröffentlichung offen.** Backend-Erfolg ist kein Gerätenachweis.
- Quellen und Auslieferungsbelege lokal gesichert; ausschließlich PR22 aktualisiert, kein Merge.

[Quellen](../cloudflare/echo-values) · [Grundlage und Rücksprung2111](ALEXA-WIEDERHERSTELLUNG-2111.md)
