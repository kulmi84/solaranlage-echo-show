# Zusätzliches Solaranlagen-Widget

Die funktionierende Vollbildansicht bleibt bestehen. Das Widget ist eine zusätzliche Ansicht für PV-Leistung,
Hausverbrauch, Akkustand und Empfangszeit. Antippen öffnet die bisherige Vollbildanzeige.

Der bestehende Sprachaufruf wird nicht umbenannt. Außerhalb der neuen Widget-Ereignisse reicht der Router
Anfragen unverändert an den gesicherten Live-Handler der v1.0.6 weiter. Der Build prüft dessen SHA-256.
Es gibt keine Änderungen am Bilddienst, an Home Assistant oder am produktiven Relay.

## Status

Am 23. Oktober 2026 im Entwicklungsstand des normalen Skills bereitgestellt und auf dem Echo Show 8
installiert. Amazon bestätigt die Zustellung echter Messwerte. Der bisherige Sprachaufruf und die echte
Vollbildanzeige wurden im Simulator geprüft. Ein tatsächlicher Tipp am Gerät muss vom Nutzer bestätigt werden.
Das Widget ist erst nach Amazons erneuter Zertifizierung allgemein in der Widget-Galerie verfügbar.

![Beispielansicht des zusätzlichen Widgets](https://solaranlage-widget.kulmi84.workers.dev/preview.png)

Die Vorschau enthält ausdrücklich Beispielwerte. Das installierte Widget erhält Werte des verknüpften Haushalts.
Nur der isolierte Zertifizierungs-Haushalt erhält klar markierte Demowerte.

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
