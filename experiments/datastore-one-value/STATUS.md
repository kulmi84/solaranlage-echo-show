# Beobachteter Stand am 30.10.2026

## Tatsächlich am Gerät bestätigt

- Echo Show 8 (2. Generation), Deutsch/EU, Alexa+ Early Access.
- DataStoreOneValue01 1.0.1: Abrufe und Antworten steigen.
- Gelesener Wert bleibt leer; Status „Objekt fehlt“.
- Das separate private Bildwidget 1.3.1 funktioniert und aktualisiert sich. Es nutzt einen vorab hinterlegten persönlichen Bildzugang und ist nicht Bestandteil dieses Beispiels.

## Durchgeführte Versuche

- Ein einzelner REST-PUT_OBJECT für AccessProbeOne/sample mit dem Wert 731042: HTTP 200, ein SUCCESS, zurückgemeldete Gerätekennung entsprach dem vorgesehenen Ziel.
- Paket, Version, Namespace und Key in der gespeicherten Quelle verglichen: DataStoreOneValue01 1.0.1 und AccessProbeOne/sample stimmen überein.
- Antwortzähler gegenüber 1.0.0 korrigiert: event.target.bind.readCount; separater Abrufzähler und expliziter ProbeRead-Sequencer ergänzt.
- Direkter Schreibversuch aus der Authoring-Oberfläche mit dem Marker DEV-731043: Erfolgsmeldung, weiterhin kein sichtbarer Objektwert.
- Globalen Skill-Testschalter Development → Live ausprobiert: Nutzer bestätigt weiterhin „Objekt fehlt“. Anschließend Development wiederhergestellt. Kein neuer Build, keine weitere Installation, keine Code- oder Backendänderung für diesen Schalterversuch.

## Aussage von Amazon und verbleibende Unsicherheit

Die vom Betreiber bereitgestellte Supportantwort beschreibt Development-Lesezugriffe und Live-Schreibzugriffe sowie zusätzlich einen Plattform-Zuordnungsfehler. Die konkrete Tick-Beobachtung in dieser Antwort stammt aus einem früheren SharedAccount-Test und ist kein direkter Laufzeitnachweis dieses minimalen Testdokuments; dieses enthält keine SendEvent-Aufrufe.

Die REST-Anfrage dieses Reproducers adressiert ein Gerät im Skill-Kontext, keine Paketversion. Sie enthält keinen Stage- oder Package-ID-Parameter. Welcher Store der installierten Testinstanz tatsächlich zugeordnet ist, ist weiterhin nicht unabhängig bestätigt.

Der negative globale Umschaltversuch widerlegt die von Amazon beschriebene Stufenabweichung nicht. Gespeicherte Quellen, API-SUCCESS und Simulatorergebnisse ersetzen keinen erfolgreichen Abruf am Gerät.

## Nicht enthalten / nicht behauptet

Keine Behebung des Plattformproblems, kein öffentlicher Bildzugang, keine fertige allgemeine Kontoeinrichtung und kein HACS-/Amazon-Release. Bestehendes Bildwidget, Vollbild und Produktionscode wurden für diesen Export nicht verändert.
