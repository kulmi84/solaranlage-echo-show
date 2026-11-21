# Projektstatus · 21.11.2026

- Store-Update **1.1.0 (Build 2111)** seit 17:53 Uhr in **CERTIFICATION**. Automatische Veröffentlichung nach Amazon-Freigabe beauftragt. Build 2311 wurde zurückgezogen.
- Vollbildkorrektur seit 17:43 Uhr im Live-Code. DEV bleibt getrennt erhalten, ebenfalls mit Anzeige Build 2111. Paketkennungen bleiben unverändert.
- Vollbild übernimmt direkte Textwerte aus dem verifizierten Datenspeicher im Root-Tick. Geschlossene Sprachsitzung, Optik und Navigation bleiben erhalten.
- Angefordertes Anzeigeprofil und verifizierte Datenautorität bleiben getrennt. Ein bestehender DEV-Datenzugang macht Store-Vollbild nicht zur DEV-Anzeige.
- Der bestehende Minuten-Cron versorgt DEV und Store getrennt. Gemeinsames PUT_OBJECT enthält kleine Werte und Vollbild aus derselben Messung. Keine Zahlenbilder; vorhandene Inline-Abrufe bleiben erhalten.
- 155 Python- und 49 Worker-Tests bestanden; gebündelter Worker ebenfalls 49. Nutzer meldet funktionierende DEV-Aktualisierung. Live-Echo-Abnahme und Amazon-Freigabe bleiben offen.
- Vollständige private Sicherung mit Quellen, Konfiguration, Einreichungsbelegen und Wiederherstellungsweg liegt lokal. Keine privaten Daten in GitHub.

[Quellen](../cloudflare/echo-values) · [Wiederherstellung](ALEXA-WIEDERHERSTELLUNG-2111.md)
