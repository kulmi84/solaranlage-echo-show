# Zusätzliches Solaranlagen-Widget

Die funktionierende Vollbildansicht bleibt bestehen. Das Widget ist eine zusätzliche Ansicht für PV-Leistung,
Hausverbrauch, Akkustand und Empfangszeit. Antippen öffnet die bisherige Vollbildanzeige.

Der bestehende Sprachaufruf wird nicht umbenannt. Außerhalb der neuen Widget-Ereignisse reicht der Router
Anfragen unverändert an den aktuellen Produktionshandler der v1.0.7 weiter. Der Widget-Build verwendet den normalen Produktionsbuilder, einschließlich Statusansage.
Es gibt keine Änderungen am Bilddienst, an Home Assistant oder am produktiven Relay.

## Gemeinsame Basis mit v1.0.7

Der Widget-Kandidat enthält die Statusansage aus v1.0.7 und das transparente Widget 1.1.0 zusammen. Der Builder fällt nicht mehr auf das Archiv v1.0.6 zurück. Alle bisherigen Anfragen werden unverändert an den v1.0.7-Handler weitergereicht. 56 Python-Tests bestehen: 38 Produktionstests, 9 Widgettests und 9 Statusprüfungen durch den kombinierten Widget-Einstieg. Zusätzlich bestehen 18 Node-Tests des Widgetdiensts.

Der geänderte Build ist zunächst ein Quellcode-Kandidat im PR. Er wurde nicht live ausgerollt. Vor Veröffentlichung den tatsächlich bei Amazon eingesetzten Kandidaten mit dieser Kombination vergleichen; eine laufende Prüfung nicht automatisch zurückziehen.

## Status — 25. Oktober 2026

**Widget 1.1.0: zur Amazon-Zertifizierung eingereicht, noch nicht veröffentlicht.**

Amazon zeigt weiterhin **In review**. Die zuletzt angezeigte Einreichung ist vom **25.10.2026, 15:53 Uhr (Europe/Berlin)**. Der angezeigte Ergebnistermin ist der 06.11.2026, 15:53 Uhr; das ist keine Zusage einer früheren Freigabe.

Die zugehörige Beta-Ansicht wurde auf dem Echo Show mit Live-Werten und funktionierendem Antippen bestätigt. Für den normalen Skill ist dieselbe große, transparente Gestaltung vorgesehen:

- Werte für PV + BKW, Hausverbrauch und Akku in **Schriftgröße 48**.
- Kein sichtbarer Rahmen und keine eigene Hintergrundfläche.
- Vorhandene Fläche mit gleichmäßigen Abständen ausgenutzt.
- Name **Solaranlage**, interne Paketkennung **SolarWidget**, Paketversion **1.1.0**.
- Antippen öffnet die **normale Vollbildansicht**, nicht die Beta.
- Bestehende Vollbildansicht, Sprachaufruf, Bildaktualisierung, Home Assistant und Relay bleiben unverändert. Die separate Beta bleibt erhalten.

Build und Amazon-Validierung waren erfolgreich. **27 Tests bestanden** (9 Python, 18 Node), einschließlich Regressionstests für bisherige Vollbild- und Sprachantworten.

Die frühere Einreichung mit altem Layout wurde zurückgezogen. Das bestätigte Layout ist Bestandteil des neuen Kandidaten. Die Veröffentlichung und der zusätzliche Widget-Code-Rollout sind nach bestandener zugehöriger Prüfung vom Betreiber freigegeben. Bis dahin kein Live-Rollout. Main und HACS stehen separat auf v1.0.7.

Die bisherigen Abbildungen unten zeigen den **älteren Entwurf mit Schriftgröße 42**, nicht die finale 1.1.0:

![Historischer Widget-Entwurf mit Beispielwerten](../docs/images/widget-large.png)

Die Abbildungen enthalten Beispielwerte; private Konfigurationen oder Zugangsdaten werden nicht veröffentlicht.

## Bauen und prüfen

```sh
python widget/build_widget.py
python widget/build_skill.py
cd widget
python -m unittest -v test_widget
cd cloudflare
python build_assets.py
node --test push.test.mjs worker.test.mjs registry.test.mjs
```

`build_assets.py` benötigt Pillow. Es verwendet ausschließlich das vorhandene Projektlogo.
`widget/dist/lambda_function.py` ist die zusätzliche Widget-Version. Der normale Root-Build bleibt unverändert.
Private Konfigurationen oder Schlüssel werden niemals in GitHub hinterlegt.

## Hintergrunddienst

Separate D1-Datenbank für die Widget-Zuordnung; bestehende Quelldatenbank wird im Anwendungscode ausschließlich
mit SELECT gelesen. Cloudflare-D1-Bindings selbst sind technisch nicht auf Lesezugriff beschränkt.
Minutentakt mit begrenzten Wiederholungen, erfolgreicher Geräte-Zustellbestätigung und Empfangszeit.
Bei fehlenden oder alten Werten keine erfundenen Messwerte. Amazon steuert tatsächliche Zustellung und Widgetgröße.
Ohne Datenspeicher in der Authoring-Tool-Vorschau erscheinen Striche; das ist keine Live-Geräteprüfung.

Als Betreiber `wrangler.example.jsonc` lokal kopieren, beide Datenbank-IDs einsetzen und die Tabelle aus
`schema.sql` ausschließlich in der neuen Widget-Datenbank erstellen. Secrets: `ALEXA_CLIENT_ID`,
`ALEXA_CLIENT_SECRET`, `REGISTER_KEY`. Den Registrierungs-Endpunkt und denselben Registrierungsschlüssel
in der privaten Alexa-Konfiguration als `widget_registration_url` und `widget_registration_key` ergänzen.
Amazon-Zugangsdaten brauchen den Scope `alexa::datastore`; keine HA-Zugangsdaten hinterlegen.

Beim ersten Installationsereignis wird ein gültiges Kontoverknüpfungstoken geprüft, aber nicht gespeichert.
Ist es dort nicht vorhanden, kann der erste Widget-Tipp die Registrierung nachholen.
Eine fehlgeschlagene Registrierung beim Tippen darf die Vollbildanzeige nicht blockieren.
Deinstallation entfernt die Registrierung. Sperre, Löschung oder Haushaltsschlüsselwechsel stoppen weitere
Übertragungen beim nächsten Lauf. Amazon-Unlink allein ist kein garantiert sofortiger Widerruf.

## Rückkehr zum vorherigen Stand

Die unveränderte v1.0.6 ist auf `codex/archive-v1.0.6-before-widget` und als Release v1.0.6 erhalten.
Zusätzlich wurde der private komplette Stand lokal mit Prüfsummen gesichert.
Für Alexa-Rollback den bisherigen Code und die bisherige private Konfiguration wieder deployen und live übernehmen.
Ein HACS-Downgrade allein stellt den Alexa-Code nicht wieder her. Den separaten Widgetdienst bei Bedarf anhalten.

## Referenzen

- https://developer.amazon.com/en-US/docs/alexa/alexa-presentation-language/apl-interface.html
- https://developer.amazon.com/en-US/docs/alexa/alexa-presentation-language/data-store-rest-api-reference.html
- https://developer.amazon.com/en-US/docs/alexa/alexa-presentation-language/create-and-manage-widgets.html
- https://solaranlage-widget.kulmi84.workers.dev/privacy
