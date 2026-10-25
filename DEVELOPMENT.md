# Weiterentwicklung

## Lokale Umgebung unter Windows

Der Quellcode besteht aus Python (Alexa-Skill, Einrichtungsassistent und
Home-Assistant-Integration) und JavaScript-Modulen (Cloudflare Worker).
Die Worker-Tests verwenden den eingebauten Node-Testlaeufer und brauchen
keine npm-Pakete. Home Assistant selbst wird fuer die lokalen Tests gemockt.

Voraussetzungen: Git, Python 3.12 mit pip und Tcl/Tk fuer den optionalen
Einrichtungsassistenten, Node.js 22 oder neuer sowie PowerShell.
Fuer Cloudflare-Bereitstellungen wird zusaetzlich npm/npx benoetigt.

Im Projektordner:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
.\scripts\check.ps1
```

Eine Aktivierung der Umgebung ist nicht erforderlich. Bei externen Laufzeiten
koennen `-PythonPath 'C:\Pfad\python.exe'` und `-NodePath 'C:\Pfad\node.exe'`
an `check.ps1` uebergeben werden. Fuer Tests muss die angegebene Python-Umgebung
die Pakete aus `requirements-test.txt` enthalten.

Der Pruefbefehl stoppt beim ersten Fehler und fuehrt nacheinander aus:

1. Alle Python-Tests im Projektstamm, einschliesslich Sprache, Anzeige, HACS und Installer.
2. Die drei produktiven Worker-Testsuiten (privates Relay, Public Beta und Bilddienst).
3. Den Skill-Build mit Syntaxpruefung fuer Python 3.8 nach `dist/lambda_function.py`.

Experimente unter `experiments/` haben eigene Tests und gehoeren nicht zur
Standardpruefung. Der Pruefbefehl benoetigt keine Anbieter-Zugangsdaten und
deployt nichts. Der Build ist lokal generiert und wird nicht eingecheckt.

## Aufbau und Aenderungen

- `beta_live_reader.py`: Messwerte lesen, pruefen und Zeitraeume bewerten.
- `beta_live_lambda.py`: native Anzeige und einzelne Sprachabfragen.
- `image_runtime.py`: produktiver Einstiegspunkt und Bildaktualisierung.
- `build_skill.py`: die drei Module zum Alexa-Modul zusammenfuehren.
- `alexa/interaction-model.de-DE.json`: deutsche Intents und Beispielsaetze.
- `custom_components/solaranlage_echo/`: HACS-Integration.
- `cloudflare/`, `cloudflare/public-beta/`, `cloudflare/display/`: getrennte Dienste.

Neue Aenderungen auf einem eigenen Branch entwickeln. Vor einem Pull Request
`check.ps1` ausfuehren. Bei Sprachfunktionen sowohl die nativen Handler als auch
das erzeugte produktive Modul testen; Echo mit und ohne APL beruecksichtigen.
Neue Intents erfordern auch einen Import und Build des Alexa-Sprachmodells.
Ein bestandener lokaler Test ersetzt keinen Alexa-Simulator- oder Geraetetest.

Private Dateien nur aus den vorhandenen Beispielen anlegen. Keine echten Token,
HA-Zugangsdaten oder produktiven Konfigurationen einchecken. Fuer lokale Tests
sind solche Dateien nicht erforderlich. Deployments und echte Relay-Abfragen
sind separate, bewusste Schritte.

## Git auf dem NAS

Meldet Git wegen des NAS-Besitzers `dubious ownership`, kann genau dieser Checkout
fuer einen einzelnen Befehl als vertrauenswuerdig angegeben werden:

```powershell
git -c safe.directory=//NAS04-MD/UnInst/GitHub/DK/solaranlage-echo-show status
```

## Geplanter naechster Schritt: Gesamtansage

Einzelabfragen ohne Bildschirm sind bereits vorhanden: aktuelle Gesamtleistung,
Akkustand, Hausverbrauch, heutige Gesamtproduktion und heutige Einspeisung.
Beim Oeffnen ohne APL gibt es bereits eine kurze Zusammenfassung.
Ein eigener Befehl fuer alle Werte ist im aktuellen Sprachmodell nicht vorhanden.

Fuer einen separaten Funktions-PR: Umfang der Gesamtansage festlegen (Livewerte,
Tageswerte, gegebenenfalls Monat/Jahr), einen passenden Intent ergaenzen und
fehlende/veraltete Werte sowie Nullwerte korrekt sprechen. Bestehende stille
Anzeigeaufrufe auf dem Echo Show erhalten und den produktiven Bild-Wrapper
mitpruefen. Vorgeschlagener Aufruf: "Alexa, frage meine Solaranlage nach allen Werten."
