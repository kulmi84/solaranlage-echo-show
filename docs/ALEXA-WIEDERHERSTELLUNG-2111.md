# Wiederherstellung Build 2111

Referenz: 21.11.2026, Live-Code 17:43 bereitgestellt, Store-Einreichung 17:53:49 in CERTIFICATION mit automatischer Veröffentlichung nach Freigabe. DEV bleibt separat erhalten. Einreichung ist keine Zertifizierung oder Live-Echo-Abnahme.

## Funktionsbestand

Direkte Textwerte ohne Zahlenbilder. Vollbild übernimmt den verifizierten Snapshot im Root-Tick. Der Handler der DataStore-Erweiterung läuft im Dokumentkontext und darf dort nicht auf komponentenlokales `fsSampleTime` zugreifen. Diese Scope-Falle war Ursache des Stillstands nach den Anfangswerten.

Namespace aus bestätigter Datenautorität, Anzeigeprofil aus angefordertem Paket/Token: niemals `cfg=resolved`. DEV-Tipp bleibt DEV, Store und Sprachstart bleiben Store. Sprachabschluss `shouldEndSession:true`, kein reprompt und kein Finish. Layout, Navigation, Fehlerverhalten und bestehende Kachelversorgung bleiben erhalten.

## Rücksprung

1. Vor jedem Eingriff neuen aktuellen Stand sichern, SHA-256-Inventar und Archivintegrität prüfen. Die privaten Originalkonfigurationen nicht durch Beispielwerte ersetzen.
2. Im lokalen Gesamtarchiv: aktuelle Skillquellen, Widgetpakete und Amazon-Belege, Worker inklusive Formatierung, Variablen/Cron/Bindungen und private Geheimnisse; Git-Historien und D1-Snapshot liegen getrennt bei.
3. Nur den benötigten Skill-Code nach Development übernehmen. Live erfordert ausdrückliche Promotion. Store-Paket separat einreichen. Paketkennungen `Solaranlage1811` und `SolarAccountImageBuild1211` erhalten.
4. Worker `solaranlage-echo-werte`: Module aus dem gesicherten Stand, originale D1-Bindung und Secrets wiederverwenden. `FULLSCREEN_DATASTORE_ENABLED=true`, `FULLSCREEN_STORE_ENABLED=true`, `PUBLISH_MODE=inline`; vorhandener Cron `*/1 * * * *`. DEV- und Live-Auswahl bleiben getrennt, derselbe Cron kann mehrere Zustellgruppen bearbeiten.
5. Datenbankrücknahme ist kein normaler Code-Rollback. Sie kann neue Konten, Widerrufe und Zuordnungen überschreiben; dafür eigenen Auftrag und Abgleich des aktuellen Zustands benötigen. Keine alten Instanzen pauschal reaktivieren. Datenbankexport vor Nutzung lokal auf Integrität geprüft.
6. Einmal neu geöffnetes Vollbild und kleine Kachel getrennt am Echo prüfen: automatische Werte, Einblenden/Aufwachen, Navigation, Store-/DEV-Footer und normale Alexa-Sprache. Backend- und Build-Erfolg ersetzen diesen Nachweis nicht.

Grenze: Ein Archiv ist kein Echo-Geräteimage. Amazon-interne Installationen, Cache, zukünftige Token-Gültigkeit und Zertifizierungsstatus können nicht durch Dateien zurückgesetzt oder dauerhaft garantiert werden. Gesichert ist der dokumentierte eigene Code-/Konfigurations-/Datenstand; keine automatische Wiederherstellung aus GitHub.

Private Konfiguration, Datenbankinhalte und Zugangsdaten bleiben lokal und gehören nicht in den PR.
