# Bildbasierte Wertebereiche â€“ separate Beta

Diese Variante hÃ¤lt Ãœberschriften, Kacheln und Bedienelemente als native APL-Komponenten auf dem Echo Show. Nur die Messwertbereiche sind kleine PNG-Bilder. Das reduziert das sichtbare Aufblinken gegenÃ¼ber einem neu geladenen Vollbild. Die Sprachsitzung bleibt geschlossen; die Bilder werden lokal Ã¼ber `SetValue` nachgeladen.

Die Standarddateien `beta_live_lambda.py`, `build_skill.py`, die HACS-Integration und der produktive Relay-Worker werden durch diesen Vorschlag nicht ersetzt. Es gibt keine automatische Bereitstellung oder neue HACS-Version.

## Umfang

- Live/Heute: PV inklusive BKW, Hausverbrauch, Netzbezug und Einspeisung, Akkustand, Laden/Entladen sowie Tagesenergien.
- Monat/Jahr: Erzeugung, Verbrauch, Netz- und Akkuenergien.
- Acht getrennte Wertebilder je Seite; regelmÃ¤ÃŸiger Abruf alle 60 Sekunden fÃ¼r die sichtbare Seite.
- Nach Ladefehlern erneuter Versuch nach zehn Sekunden. Ein erfolgreicher Abruf setzt den Fehlerhinweis zurÃ¼ck.
- Lokaler Seitenwechsel und manuelles Aktualisieren ohne `SendEvent`.
- Uhrbild, Tick, Versuche und BildzÃ¤hler bleiben zur Diagnose erhalten. â€žVersucheâ€œ gehÃ¶rt zum alten SendEvent-Test und zÃ¤hlt nicht die PNG-Abrufe.
- Keine doppelt gepufferten Bilder: Beide Versuche damit wurden am echten Echo Show verworfen, obwohl der Simulator Aktualisierungen zeigte.

## Beispielansichten

Die folgenden Bilder zeigen den PNG-Renderer mit **synthetischen Beispielwerten**, keine privaten Messwerte und keine GerÃ¤teaufnahmen. In der Beta werden die Wertebereiche daraus einzeln in native Kacheln gesetzt.

![Live und Heute â€“ synthetische Werte](assets/renderer-live.png)
![Monat und Jahr â€“ synthetische Werte](assets/renderer-history.png)

## Separat aufbauen

Voraussetzung ist die vorhandene KontoverknÃ¼pfung des eigenen Test-Skills mit dem Lesebereich `solar:read`. Eine reine HACS-Aktualisierung aktiviert diese Variante nicht. FÃ¼r die bestehende Testinstallation ist kein neuer HA-Upload nÃ¶tig.

1. `python build_live_images.py` in diesem Verzeichnis ausfÃ¼hren. Das erzeugte `image-live/lambda_function.py` ist syntaktisch mit Python 3.8 kompatibel.
2. `worker/wrangler.example.jsonc` nach `worker/wrangler.jsonc` kopieren und einen **separaten** Testworker verwenden. Die beiden erwarteten Hostnamen in `live_image_runtime.py`, `diagnostic_display.py` und `worker/sessions.mjs` mÃ¼ssen zur eigenen Testumgebung passen; der Relay-Upstream bleibt fest konfiguriert.
3. Zwei unabhÃ¤ngige SchlÃ¼ssel erzeugen, beispielsweise zweimal `python -c "import secrets; print(secrets.token_hex(32))"`. `SESSION_KEY` und `DISPLAY_KEY` als Worker-Secrets setzen. Niemals echte SchlÃ¼ssel in `.secrets.example.json` eintragen oder committen.
4. Nur den separaten Bildworker bereitstellen. Er erhÃ¤lt keine Datenbankbindung. Seine einzige Datenquelle ist die fest eingestellte `/v1/pv`-Leseroute des Relays.
5. `relay_config.example.json` privat als `relay_config.json` neben die gebaute Lambda-Datei legen. `image_session_key` ist derselbe Wert wie `SESSION_KEY`; `DISPLAY_KEY` verbleibt ausschlieÃŸlich im Worker.
6. Lambda und private Konfiguration ausschlieÃŸlich in den gewÃ¼nschten Test-Skill hochladen und dessen Entwicklungsstand bereitstellen. Nicht â€žPromote to liveâ€œ wÃ¤hlen.
7. Den Test-Skill in der Alexa-App separat verknÃ¼pfen und mit â€žAlexa, Ã¶ffne meine Solaranlage Testâ€œ starten.

Ohne KontoverknÃ¼pfung oder bei fehlgeschlagenem Bildzugang zeigt die Beta einen Hinweis. Das DiagnosegerÃ¼st enthÃ¤lt keine Demo-Messwerte; Solar-Sprachantworten lesen die echten Werte Ã¼ber den vorhandenen Reader.

## Bildzugriff und Laufzeit

Der Bilddienst prÃ¼ft bei der Vergabe das OAuth-Lesetoken gegen den festen Relay-Upstream. Die Bildadresse enthÃ¤lt einen authentifiziert verschlÃ¼sselten Zugang (AES-GCM), der maximal eine Stunde gilt. Jeder Bildabruf prÃ¼ft ihn erneut und fragt das Relay mit diesem Lesetoken ab. Es gibt keine Ã¶ffentlich lesbare Messwertadresse und keine frei wÃ¤hlbare Upstream-URL. Bildadressen sind trotzdem vertraulich: Wer eine gÃ¼ltige Adresse besitzt, kann bis zu deren Ablauf die zugehÃ¶rigen Werte lesen. Sie gehÃ¶ren weder in Issues noch in Screenshots oder Logs.

Redirects werden nicht verfolgt; Nicht-2xx-Antworten werden abgelehnt. Antworten sind grÃ¶ÃŸenbegrenzt, werden nicht gecacht und enthalten keine Kontotoken im Klartext. Observability bleibt im Beispiel deaktiviert. Der separate Uhrbild-Endpunkt enthÃ¤lt keine Haushaltsdaten.

Der Zugang wird bei geschlossener Sprachsitzung nicht automatisch verlÃ¤ngert. Nach Ablauf muss der Skill erneut geÃ¶ffnet werden. Der Datenstand und Fehlerhinweise sind deshalb Teil des Tests.

## PrÃ¼fen

```text
python -m unittest -q test_live_images
node --test worker/worker.test.mjs worker/sessions.test.mjs
```

Sieben Python-Tests und zehn Worker-Tests prÃ¼fen unter anderem KontoverknÃ¼pfung, echte Sprachantworten, Ablauf/Manipulation, Zugriffsschutz, begrenzte Koordinaten und alle 16 Wertebilder.

Die geglÃ¤ttete Schrift im Ã¶ffentlichen Paket wird aus der mit ReportLab verteilten, weiterverteilbaren Schrift erzeugt; siehe `worker/FONT-LICENSE.txt`. Zum reproduzierbaren Neuaufbau: AbhÃ¤ngigkeiten aus `requirements-dev.txt` installieren und `python worker/build_font.py` ausfÃ¼hren. Der laufende private Beta-Prototyp verwendete zuvor einen lokalen Windows-Font; der PR enthÃ¤lt keine Windows-Schriftdateien.

## Vor einer Live-Ãœbernahme offen

- LÃ¤ngeren GerÃ¤tetest der vollstÃ¤ndigen Ansicht und mehrerer Aktualisierungen bestÃ¤tigen. Der Betreiber hat den Einzelbild-Test als deutlich unauffÃ¤lliger bewertet. Der vollstÃ¤ndige Aufbau wurde bislang im Simulator geprÃ¼ft.
- Die einzelnen Kachel-Uhrzeiten und Diagnoseanzeigen entfernen. FÃ¼r die endgÃ¼ltige Ansicht ist ein gemeinsamer Datenstand vorgesehen.
- Ablauf nach einer Stunde und zeitweise nicht verfÃ¼gbare Daten sichtbar am GerÃ¤t prÃ¼fen.
- ZusÃ¤tzliche Worker-Aufrufe und Betriebsgrenzen fÃ¼r mehr als die private Testinstallation bewerten. Dieser PR aktiviert keinen kostenpflichtigen Tarif.

## RÃ¼ckkehr

Der bisherige native Produktionsstand bleibt als [Release v1.0.5](https://github.com/kulmi84/solaranlage-echo-show/releases/tag/v1.0.5) und im [Archivzweig](https://github.com/kulmi84/solaranlage-echo-show/tree/codex/archive-v1.0.5-native-apl) erhalten. Zur RÃ¼ckkehr muss der zentrale Alexa-Code aus diesem Stand bereitgestellt werden; ein HACS-Downgrade allein genÃ¼gt nicht. Die private Komplettsicherung mit Konfiguration bleibt auÃŸerhalb des Ã¶ffentlichen Repositorys.

## Layoutanpassung am 21. Oktober 2026

Das native Gerüst übernimmt die bisherigen Maße: 3 vw Seitenrand, 10 vh Kopfzeile, 30 vh je Kachelreihe, 23 vw Kachelbreite, 14 dp Rundung, 3,4 vh Kachelbeschriftung und Wertebilder passend zu den bisherigen Schriftgrößen. Die Navigation steht wieder oben. Live/Heute und Monat/Jahr nutzen den vollen Bildschirm; die Diagnose bleibt am unteren Rand der Beta. Der vorherige kompakte Beta-Aufbau bleibt im Archivzweig `codex/archive-beta-before-final-layout` erhalten. Die private Komplettsicherung enthält zusätzlich den tatsächlich eingesetzten Windows-Schriftatlas und die privaten Konfigurationen.
