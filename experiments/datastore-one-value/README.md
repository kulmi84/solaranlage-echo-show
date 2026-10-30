# Alexa Data Store: eigenständiges Einwert-Testwidget

Wiederverwendbarer Diagnose-Reproducer **DataStoreOneValue01, Version 1.0.1**.
Er liest genau `AccessProbeOne/sample` mit einem Feld `value`.
**Kein bestätigter Fix:** Auf dem untersuchten Echo steigen Abruf- und Antwortzähler, während das Objekt weiterhin `null` bleibt. Details: [STATUS.md](STATUS.md), [Issue #10](https://github.com/kulmi84/solaranlage-echo-show/issues/10).

## Dateien

- [document.json](document.json): tatsächlich getestetes APL-Dokument, unverändert aus dem isolierten Test.
- [manifest.json](manifest.json): tatsächlich getestetes Paketmanifest. Die öffentlichen Icon-/Vorschaubilder gehören zum ursprünglichen Repository und können für ein anderes Projekt ersetzt werden; die Vorschau beweist keinen Datenempfang.
- [commands.json](commands.json): genau ein PUT_OBJECT mit einem unvertraulichen Testwert.
- [request.example.json](request.example.json): REST-Anfrage mit Platzhalter für die Gerätekennung.
- [send_probe.py](send_probe.py): optionaler Sender; standardmäßig nur lokale Vorschau, Versand ausschließlich mit `--send`.

Keine persönlichen Bildzugänge, OAuth-Geheimnisse, echten Nutzer-/Gerätekennungen oder produktiven Lambda-Quellen sind enthalten. Das ist ein Data-Store-Test, kein Test des Bildzugangs oder der Kontoverknüpfung.

## In einem anderen Skill verwenden

1. In der Alexa Developer Console den gewünschten eigenen Skill und dessen Widget-Editor öffnen. Die Data-Store-Unterstützung und angeforderte Erweiterung `alexaext:datastore:10` des Skills prüfen. Das APL-Dokument allein ist kein vollständiges Skill-Manifest.
2. Paketmanifest und Dokument übernehmen: `presentationDefinitions[0].url` verweist auf `presentations/default.tpl`; dort gehört der Inhalt von `document.json` hin. Bei Nutzung des Editors dessen Dokument- und Manifestansicht verwenden. Für parallele Versuche eine eindeutige Paketkennung wählen und dokumentieren.
3. Bauen und genau eine eindeutig zuordenbare Testinstanz auf dem gewünschten Gerät installieren. Skill, Stufe, Paketkennung/-version und Gerätezuordnung notieren.
4. Entweder den einzelnen Befehl aus `commands.json` über die Data-Store-Testoberfläche senden oder das REST-Beispiel mit eigenen Angaben verwenden. Gerätekennungen müssen aus genau dem verwendeten Skill stammen. Keine Kennungen eines anderen Skills übernehmen.
5. Auf der Kachel Wert, Status, Abrufe, Antworten und Bindung vergleichen. Ein erfolgreicher Schreibauftrag allein ist kein Nachweis, dass genau diese Instanz das Objekt lesen kann.

Das Beispiel schreibt in den separaten Namespace `AccessProbeOne`; es enthält weder CLEAR noch Löschbefehle. Es verwendet nicht `Solar/live` und verändert keine Bildwidget-Dokumente. Ein vorhandener Wert unter `AccessProbeOne/sample` wird beim Versand überschrieben. Für einen anderen Namespace **alle** Referenzen in Dokument, Befehlsdatei und Anfrage gemeinsam ändern.

### Optionaler REST-Versand

Python 3, nur Standardbibliothek. Zunächst ohne Netzwerkzugriff prüfen:

```powershell
python send_probe.py
```

Für genau einen Versand die Umgebungsvariablen `ALEXA_DATASTORE_ACCESS_TOKEN` (gültiger Token mit Scope `alexa::datastore`) und `ALEXA_DEVICE_ID` ausschließlich lokal setzen. Der Token muss zu den Berechtigungen des gewählten Skills gehören. Dann:

```powershell
python send_probe.py --send
```

Der Sender verwendet den EU-Endpunkt `https://api.eu.amazonalexa.com/v1/datastore/commands` des ursprünglichen Versuchs. Für andere Regionen den passenden Endpunkt vor Übernahme klären. Er erzeugt keine Zugangsdaten und liest keine privaten Projektkonfigurationen. Ausgabe enthält nur HTTP-Status, Ergebnisarten und einen booleschen Zielabgleich, keine Tokens oder Gerätekennungen. HTTP 200/SUCCESS ist weiterhin kein Geräte-Lesenachweis.

## Verhalten und Grenzen

- Ein GetObject direkt beim Dokumentstart, zusätzlich WatchObject.
- Solange die Laufzeit Ticks ausführt: GetObject alle fünf Sekunden auf dem Sequencer `ProbeRead`.
- `Abrufe` zählt lokale Start-/Tick-Versuche, nicht serverseitig bestätigte Anfragen.
- `Antworten` zählt passende OnObjectReceived- und OnObjectChanged-Ereignisse, auch bei `null`.
- `Bindung` zeigt unabhängig den Wert aus der deklarativen Data-Bindung.
- Keine Sprachbefehle, SendEvent-Aufrufe, Vollbildöffnung oder Bilddownloads.

Der globale Development/Live-Schalter der Testkonsole wurde im Ausgangsversuch ausprobiert und wieder zurückgestellt. Das Ergebnis blieb `Objekt fehlt`. Damit ist die tatsächliche Stufenzuordnung der installierten Widget-Instanz **nicht** geklärt. Bitte nicht als automatische Migration einer vorhandenen Instanz oder als bestätigten Fix verwenden.

Ein anderes Gerät bzw. ein anderer Skill kann mit diesen Dateien separat untersucht werden; Erfolg dort ist noch nicht nachgewiesen.
