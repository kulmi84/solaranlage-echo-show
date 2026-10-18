# Monat und Jahr: zweite Echo-Show-Seite

Auf der ersten Seite **nach rechts wischen**, um die zweite Seite zu öffnen.
Ein horizontaler Pager mit zwei umlaufenden Seiten erlaubt den Wechsel auch
in der anderen Richtung. Zusätzlich gibt es **Monat/Jahr →** und
**Live/Heute →** als große Touch-Ziele.

## Zeiträume und Werte

Die Reihen **MONAT · JJJJ-MM** und **JAHR · JJJJ** verwenden HA-Ortszeit:
Monatsbeginn bzw. 1. Januar, jeweils bis zum Abrufzeitpunkt. Gezeigt werden
PV inklusive BKW, Hausverbrauch, Netz-Einspeisung/-Bezug und Akku-Ladung/-Entladung
in kWh. Es sind keine vollständigen abgeschlossenen Monate/Jahre und keine
Prognosen. Der Stand im Footer wird ausdrücklich in UTC angegeben.

Wie bisher stammen die Energien aus `recorder.get_statistics`, Typ `change`,
mit Ausgabe in kWh. Monat und Jahr werden getrennt mit `period: month` bzw.
`period: year` abgefragt. Die sechs Zähler entsprechen dem bestehenden
Tagespackage. Die Hausenergie wird bilanziert:

`PV + BKW + Netzbezug + Akkuentladung − Einspeisung − Akkuladung`.

Fehlende Quellen bleiben unbekannt (—). Die PV-Statistik darf das separat
gewählte BKW nicht bereits enthalten. HA muss die nötigen Langzeitstatistiken
besitzen; fehlende ältere Statistik wird nicht durch den Skill rekonstruiert.
Ob seit Jahresbeginn alles erfasst wurde, muss im HA-Energie-Dashboard geprüft
werden. Ein vorhandener Teilzeitraum darf nicht als garantierte Vollständigkeit
missverstanden werden.

## Sechs-Stunden-Takt

Die neue HA-Automation läuft um 00, 06, 12 und 18 Uhr und beim HA-Start.
Einmalig nach Installation manuell ausführen. Sie lädt weder Live-Sensoren
noch alle Jahresdaten im Minutentakt. Ihre Ergebnisse liegen in der separaten
D1-Tabelle `solar_history`; Minuten-Uploads verändern diese Tabelle nicht.

Beim Öffnen liest der Skill den letzten Datensatz zusammen mit den Livewerten.
Die erste Seite behält den Minutenabruf. Die zweite Seite hat einen eigenen
Sechs-Stunden-Abrufschwellwert und löst keine Minutenabrufe aus. Da die
vorhandene Anzeigedauer eine Stunde beträgt und Alexa diese begrenzen darf,
wird der neue Sechs-Stunden-Stand in der Regel beim nächsten Öffnen sichtbar.
Diese Erweiterung erzwingt keinen sechsstündigen Dauerbetrieb des Displays.

Ein Datenalter über sechs Stunden plus zehn Minuten wird markiert. Beim
Monatswechsel werden alte Monatswerte nicht als neuer Monat angezeigt, die
Jahreswerte bleiben bis zum Jahreswechsel gültig. Ungültige langsame Daten
verhindern das Lesen der Livewerte nicht. Ein ausgefallener Statistikabruf
wird nicht als gültiger Nullverbrauch dargestellt.

## Upgrade

Vorher den bisherigen Code sowie private Konfigurationen sichern. Der
unveränderte bestätigte Stand liegt im Branch `codex/stable-2026-10-17`;
die nachfolgende Sprachkorrektur im Branch `codex/fix-fallback-2026-10-18`.
Die neue Seite wird im Branch `codex/month-year-page` weiterentwickelt.

1. Mit der vorhandenen privaten Wrangler-Konfiguration nur die Tabelle ergänzen:

   ```sh
   npx wrangler d1 execute homeassistant-pv-beta --remote --file cloudflare/history-schema.sql --config cloudflare/wrangler.jsonc
   ```

   Eigenen Datenbanknamen einsetzen. Die Migration löscht/ändert keine Livezeile.
   Bei einer Neuinstallation reicht das erweiterte `cloudflare/schema.sql`.

2. Neuen Worker deployen. Lese-/Schreibschlüssel und vorhandenes D1-Binding
   beibehalten. Die neue Erweiterung akzeptiert den Datentyp `kind: history`
   über dieselbe URL `/pv` und denselben Schreibschlüssel. GET benötigt wie
   bisher ausschließlich den Leseschlüssel.
3. `home-assistant/pv_history.yaml` im schon eingebundenen HA-Package-Verzeichnis
   **zusätzlich** ablegen. Die sechs Energiezähler ggf. wie im Tagespackage
   anpassen. Keine Secrets ersetzen: `pv_beta_url` und
   `pv_beta_write_authorization` werden wiederverwendet.
4. HA-Konfiguration prüfen, **RESTful Command** und **Automationen** neu laden.
   Die Automation „Solaranlage - Monats- und Jahreswerte alle 6 Stunden“ einmal
   manuell ausführen und ihren Trace auf Fehler prüfen. Kein HA-Neustart nötig.
5. `python build_skill.py` ausführen, erzeugte Datei vollständig im Alexa-Codeeditor
   ersetzen, speichern und deployen. `relay_config.json` bleibt unverändert.
   Keine Änderung am Sprachmodell erforderlich. Skill schließen und neu öffnen.

## Rückkehr

Für eine Rückkehr zum Stand vor dieser Seite den Alexa-Code aus
`codex/fix-fallback-2026-10-18` bauen und bereitstellen. Die neue HA-Automation
deaktivieren. Der bisherige Minuten-Upload arbeitet unverändert weiter.
Bei Bedarf den alten Worker aus demselben Branch bereitstellen. Die zusätzliche
D1-Tabelle kann bestehen bleiben; keine Datenbank löschen oder zurücksetzen.
Das Zusatzpackage bei Gelegenheit aus dem Package-Verzeichnis nehmen und
REST-Befehle/Automationen neu laden. Private Schlüssel müssen nicht geändert
werden. Der ältere Sicherungsbranch bleibt als weiterer Rückkehrpunkt erhalten.

## Tests

```sh
python -m pip install -r requirements-test.txt
python -m unittest test_beta_live.py test_history.py
node --test cloudflare/worker.test.mjs
python build_skill.py
```

Geprüft werden getrennte Speicherung und Berechtigungen, Kalenderwechsel,
Einheiten, Null-/Fehlwerte, periodische HA-Templates, beide Pager-Seiten,
Seitenzustand beim erneuten Rendern und die bisherigen Sprachabfragen.

Quellen: [HA-Statistikaktion](https://www.home-assistant.io/actions/recorder.get_statistics/),
[Amazon APL Pager](https://www.developer.amazon.com/en-US/docs/alexa/alexa-presentation-language/apl-pager.html),
[APL-Tick-Handler](https://developer.amazon.com/en-US/docs/alexa/alexa-presentation-language/apl-tick-event-handlers.html).
