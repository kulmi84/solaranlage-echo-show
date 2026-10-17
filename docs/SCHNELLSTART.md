# Neue Installation mit Einrichtungsassistent

**Entwicklungsversion – der funktionierende Stand und die laufenden Dienste
werden dadurch nicht automatisch geändert.** Verwende für den ersten Versuch
eine getrennte HA-Testinstanz, einen neuen Worker mit eigener D1-Datenbank und
einen neuen Alexa-Entwickler-Skill. Nicht zusätzlich zur vorhandenen Automation
dieselben Produktionsdaten an dasselbe Relay schicken.

## Was ist einfacher geworden?

Der lokale Assistent zeigt die Sensoren aus Home Assistant zur Auswahl an,
prüft Einheiten und Werte und erzeugt passende Dateien einschließlich zweier
getrennter zufälliger Schlüssel. Der HA-Zugangstoken wird verdeckt eingegeben,
nur für lesende API-Aufrufe benutzt und nicht gespeichert. Alternativ lassen
sich Sensor-IDs ohne HA-Zugriff eingeben. Das benötigt nur Python 3.8 oder neuer.

Für spätere Änderungen an einer vollständigen Installation kann ein Blueprint
die 15 Sensoren direkt im HA-Formular auswählen. Ein Blueprint kann keinen
REST-Befehl und keine Secrets installieren; deshalb bleibt ein vorbereitender
Konfigurationsschritt notwendig. Bei fehlenden optionalen Sensoren den
Generator-/Package-Weg nutzen.

## 1. Voraussetzungen und frisches Relay vorbereiten

Python 3.8+, Node.js mit npm, Home Assistant mit Recorder, ein kostenloses
Cloudflare-Konto und das Amazon-Entwicklerkonto werden benötigt. Ein eigener
Alexa-Entwickler-Skill bleibt erforderlich; dies ist kein öffentlicher Skill.
Die Anbieterlimits gelten weiterhin, kostenpflichtige Pläne sind nicht nötig.

Im neuen Projektordner am PC:

```sh
npx wrangler login
npx wrangler d1 create solar-neu
```

Wähle **einen neuen, freien Namen** für Worker und Datenbank, hier `solar-neu`.
Notiere die ausgegebene `database_id`. Den Workers-Subdomain-Namen findest du
im Cloudflare-Dashboard unter Workers & Pages. Die spätere Relay-Adresse ist
`https://solar-neu.DEINE-WORKERS-SUBDOMAIN.workers.dev/pv`.
Die Anmeldung und Datenbankerstellung sind bewusste manuelle Schritte;
der Assistent führt keine Cloud-Änderungen aus.

## 2. Sensoren auswählen

```sh
python installer.py wizard --ha-url https://DEINE-HA-ADRESSE:8123 --out .private/installation-neu
```

Im HA-Profil unter Sicherheit einen Long-Lived Access Token erzeugen und
**nur in die verdeckte lokale Abfrage** eingeben. Nicht als Befehlsargument,
in Chatnachrichten oder Screenshots einfügen. Ein gültiges TLS-Zertifikat wird
geprüft; Zertifikatsprüfung wird nicht ausgeschaltet.
Falls HA ausschließlich HTTP im vertrauenswürdigen Heimnetz verwendet,
ist das möglich, verlangt aber eine ausdrückliche Bestätigung wegen des
unverschlüsselten Tokens. Ohne Token/API-Zugriff:

```sh
python installer.py wizard --out .private/installation-neu
```

Der Assistent fragt die Sensoren nacheinander ab. Bei API-Zugriff wählst du
eine Nummer aus passenden Einheiten; sonst gibst du `sensor.deine_entitaet`
ein. Freundliche Namen und Messwerte werden nicht protokolliert.

- Pflicht: **PV-Gesamtleistung inklusive BKW** in W oder kW.
- Optional: PV ohne BKW, BKW, Hausverbrauch, getrennte Netzleistungen,
  Akkustand in Prozent, Lade- und Entladeleistung.
- Tageswerte: kumulierte Energiezähler in Wh, kWh oder MWh, mit
  `state_class: total` oder `total_increasing`. Keine Leistungssensoren und
  keine täglich auf null springenden Anzeigehelfer auswählen. Die Zähler
  müssen zur Recorder-Statistik des Energie-Dashboards passen.
- Der PV-Energiezähler darf das separat gewählte BKW **nicht bereits enthalten**.
  Doppelte Energiezähler werden abgewiesen. Vorzeichenbehaftete Netzsensoren
  zuerst in getrennte, nichtnegative Bezugs-/Einspeisesensoren aufteilen.
- Fehlendes optionales Feld: Enter. Fehlende Werte bleiben unbekannt und
  werden nicht zu Null. Für PV-Tagesgesamt und Tageshausverbrauch müssen alle
  dafür benötigten Quellen vorhanden sein. Wenn BKW/Akku physisch nicht
  existieren, braucht die vollständige Bilanz bewusst definierte Nullquellen;
  der Assistent nimmt deren Abwesenheit nicht automatisch als Null an.

Danach neue Worker-Adresse, Worker-/Datenbankname und Datenbank-ID eingeben.
Der Ausgabeordner muss neu sein. Bestehende Ordner werden nie überschrieben;
für einen weiteren Versuch einen anderen Namen wählen. Die Dateien enthalten
**geheime Schlüssel** und gehören nicht auf GitHub. `.private/` ist ignoriert.

## 3. Nur das neue Relay bereitstellen

Im erzeugten Unterordner `relay`:

```sh
npx wrangler deploy
npx wrangler secret bulk secrets.json
npx wrangler d1 execute solar-neu --remote --file schema.sql
```

Den tatsächlichen neuen Namen einsetzen. Die erzeugte `wrangler.jsonc` zeigt
auf die neue D1-Datenbank. Diese Befehle verändern Cloudflare, werden vom
Assistenten aber **nicht** automatisch ausgeführt. `secret bulk` liest die
Schlüssel aus der Datei; sie müssen nicht im Terminal kopiert werden.
Bei einer falschen Adresse/Datenbank zuerst die generierte Konfiguration
korrigieren, bevor du diese Befehle ausführst. Keinen vorhandenen Worker oder
eine vorhandene Datenbank überschreiben.

## 4. Home Assistant: einen von zwei Wegen wählen

**A – Generator/Package, auch mit fehlenden optionalen Sensoren:**

1. `home-assistant/pv_beta.yaml` aus dem Ausgabeordner in ein bereits
   eingebundenes HA-Package-Verzeichnis der **Testinstanz** kopieren.
2. Einträge aus `secrets-ergaenzen.yaml` an bestehende `secrets.yaml` anhängen;
   bestehende Datei niemals ersetzen. Beide Schlüsselnamen dürfen jeweils nur
   einmal vorkommen.
3. Falls Packages bisher nicht eingebunden sind, im vorhandenen
   `homeassistant:`-Block ergänzen: `packages: !include_dir_named packages`.
   Dazu das Verzeichnis `/config/packages/` verwenden. Vorhandene Blöcke
   zusammenführen, keinen zweiten `homeassistant:`-Block anlegen.
4. HA-Konfiguration prüfen, Testinstanz neu starten und Automation aktivieren.

**B – Blueprint mit HA-Sensorauswahl für eine vollständige Anlage:**

1. Statt des vollen Packages nur die erzeugte `home-assistant/rest-only.yaml`
   als Package einbinden und Secrets wie in A ergänzen.
2. Erzeugte `solaranlage-blueprint.yaml` nach
   `/config/blueprints/automation/solaranlage/upload.yaml` kopieren.
3. Konfiguration prüfen, Testinstanz neu starten. Unter Einstellungen →
   Automatisierungen & Szenen → Blueprints daraus **eine** Automation erzeugen
   und die 15 Sensoren im Formular auswählen.
4. Nicht zusätzlich die Package-Automation aus A aktivieren.

Die aktuelle Blueprint-Datei liegt auch unter
[`home-assistant/blueprints/solaranlage_upload.yaml`](../home-assistant/blueprints/solaranlage_upload.yaml).
Solange das Repository privat ist, ist das lokale Kopieren der verlässliche
Weg; ein öffentlicher Blueprint-Importlink wird erst nach Veröffentlichung
sinnvoll. Recorder-Tagesstatistiken lassen sich nicht allein aus einer
Entitätenliste sicher bestätigen. Prüfe den ersten Tageswert in HA und im Relay.

## 5. Verbindung prüfen

Vom Projektordner, nach ein bis zwei Minuten:

```sh
python installer.py check --config .private/installation-neu/alexa/relay_config.json
python installer.py check-ha --ha-url https://DEINE-HA-ADRESSE:8123 --mapping .private/installation-neu/sensoren.json
```

`check` liest nur vom Relay. Es prüft Anmeldung, gültige Messwerte,
Empfangszeitpunkt und fehlende optionale Werte. Veraltete Daten ergeben einen
Fehlerstatus, fehlende optionale Werte eine Warnung. Es wird kein Testdatensatz
in die Datenbank geschrieben. `check-ha` prüft die gespeicherte Sensorauswahl
noch einmal gegen HA; der HA-Token wird erneut verdeckt abgefragt.

| Ausgabe | Nächster Schritt |
| --- | --- |
| HTTP 401 / Zugriff verweigert | Leseschlüssel für Relay, HA-Token für HA prüfen; nicht vertauschen |
| HTTP 404 | Worker-Adresse mit `/pv` prüfen oder ersten HA-Upload abwarten |
| HTTP 503 | D1-Binding, Datenbank-ID und Schema prüfen |
| Verbindung/Dateizugriff fehlgeschlagen | URL, Dateipfad, Netzwerk und Zertifikat prüfen |
| Entität fehlt / falsche Einheit | Sensorauswahl korrigieren, erneut in neuen Ordner generieren |
| Upload veraltet | HA-Automation, Trace und REST-Befehl prüfen |
| Tageswert fehlt | Recorder, Zählerzuordnung und heutige Statistik prüfen |

## 6. Neuen Alexa-Skill testen

Im Amazon-Entwicklerportal einen separaten Custom Skill, Deutsch,
Alexa-hosted Python, Vorlage „Start from Scratch“ anlegen. Für einen parallelen
Test einen anderen Aufrufnamen wählen, etwa „meine solaranlage test“; dazu
`invocationName` in der erzeugten JSON-Datei ändern. Den bestehenden Skill
„Solaranlage“ nicht bearbeiten.

Aus dem erzeugten Ordner `alexa`:

1. `interaction-model.de-DE.json` importieren und bauen.
2. APL unter Interfaces aktivieren.
3. `lambda_function.py` und `relay_config.json` im Codeeditor als gleichnamige
   Dateien im Verzeichnis `lambda` speichern, dann Deploy.
4. Development-Testmodus und Simulator verwenden. Auf einem eigenen Echo
   denselben Amazon-Account und den neuen Entwickler-Skill verwenden.

Der Assistent hat Datenleser und Anzeige bereits zu einer Python-Datei
zusammengebaut. Kein manuelles Zusammenkopieren von Modulen nötig.
Die Alexa-Konsole und HA-Neustarts sind weiterhin manuell: Der Assistent
meldet sich dort nicht an und veröffentlicht keinen Skill.

## Rückkehr und Sicherung

Der bestätigte Stand vom **17. Oktober 2026** ist Commit
`0abddc007da6575bd9109a4d05f3a70b6a867650`, Branch
[`codex/stable-2026-10-17`](https://github.com/kulmi84/solaranlage-echo-show/tree/codex/stable-2026-10-17).
Die Einrichtungshilfen liegen getrennt im Branch `codex/setup-simplification`.
`main`, Sicherungsbranch und bestehende Dienste bleiben unverändert.

Zum bloßen Öffnen des alten Codes ein neues Verzeichnis verwenden:

```sh
git clone --branch codex/stable-2026-10-17 https://github.com/kulmi84/solaranlage-echo-show.git solaranlage-stabil
```

Das stellt Quellcode wieder her, führt aber kein Deployment durch. Wer später
bewusst eine Testversion bereitstellt und zurückwechseln möchte, baut im
stabilen Verzeichnis `python build_skill.py` und verwendet ausschließlich die
dazugehörigen gesicherten Konfigurationen. Ein HA-Package nicht gleichzeitig
in zwei Versionen aktivieren. Schlüssel sind nicht im Repository; sie müssen
aus der eigenen privaten Sicherung kommen. Eine vorhandene produktive
Konfiguration muss nicht ersetzt werden, wenn ausschließlich separat getestet
wurde. Keine Versionsrückkehr erfordert ein Löschen oder Überschreiben von D1.

## Validierung und Grenzen

Der Installer selbst hat keine zusätzlichen Python-Paketabhängigkeiten.
Zusätzliche Offline-Tests für YAML und Jinja:

```sh
python -m pip install -r requirements-test.txt
python -m unittest test_installer.py test_beta_live.py
node --test cloudflare/worker.test.mjs
```

Die generierten Dateien werden syntaktisch geprüft. Eine vollständige
HA-Laufzeitprüfung und ein Cloudflare-/Alexa-Deployment auf einer neuen
Testinstallation sind damit nicht ersetzt. Es wurde bewusst keine Produktion
zum Test verändert.

Technische Grundlagen: [HA-Blueprint-Schema](https://www.home-assistant.io/docs/blueprint/schema/),
[HA-Sensorauswahl](https://www.home-assistant.io/docs/blueprint/selectors/),
[Wrangler und Secrets](https://developers.cloudflare.com/workers/configuration/secrets/),
[D1-Befehle](https://developers.cloudflare.com/d1/wrangler-commands/).
