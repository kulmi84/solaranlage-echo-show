# Solaranlage Echo Werte · Build 2211

Store-Update **1.1.0 (Build 2211)** ist in Zertifizierung. Live-Codekorrektur ist bereitgestellt; DEV bleibt separat erhalten. Keine abgeschlossene Live-Echo-Abnahme behaupten.

Vollbild liest die lebende `FullscreenSnapshot`-Datenbindung im Root-Komponenten-Tick. Dokumentweite Extension-Handler dürfen keine lokalen Root-Bindungen wie `fsSampleTime` verwenden. Binding, Schema, Originalzeitstempel und vollständige Textfelder werden vor Übernahme geprüft; Fehler erhalten den letzten gültigen Stand.

`fullscreen_store.py` wird von beiden Anzeigeprofilen verwendet. Der Namespace stammt aus der verifizierten Datenautorität, Token und Footer aus dem angeforderten Anzeigeprofil. Sprachabschluss bleibt `shouldEndSession:true`, ohne reprompt oder Finish.

Worker: `FULLSCREEN_DATASTORE_ENABLED=true`, `FULLSCREEN_STORE_ENABLED=true`. Der vorhandene Minuten-Cron versorgt DEV und Live getrennt unter bestehenden Bindungs-/Generations-/Widerrufsprüfungen. Keine neue Registrierung, keine zweite Haushaltsabfrage für einzelne Werte und keine Zahlenbilder. Die bisherigen Inline-Aufrufe bleiben erhalten.

Prüfen: `python -m unittest discover -s . -p "test_*.py"` und `node --test worker.test.mjs`. Kein automatisches Deployment aus GitHub.

[Projektstatus](../../docs/ALEXA-STATUS.md) · [Wiederherstellung](../../docs/ALEXA-WIEDERHERSTELLUNG-2111.md)

Ruhemodus-Protokoll3 ist im Backend bereitgestellt; Store2211 erneut in Prüfung. `retry-schema.sql` und `CONNECTION_RETRY_PAUSE_ENABLED=true` gehören dazu. DEV bleibt unverändert. Details im Projektstatus; Echo-Nachweis offen.
