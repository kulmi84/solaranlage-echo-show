# Automatische Kontoanlage – seit 31. Oktober 2026 aktiv

Neuer Weg: `/v2/enroll`, nur bei `PUBLIC_ENROLLMENT_ENABLED=true`. Der bisherige Einladungsweg `/v1/enroll`, Uploads, Sensoren und OAuth bleiben erhalten. Es wird kein vorhandenes Konto umbenannt, ersetzt oder erneut verknüpft. Keine zusätzliche Datenbank und kein zusätzlicher Worker sind nötig.

## Schutz und Wiederholungen

- Aktive Grenzen: 3 neue Konten je IP/Stundenfenster, 10 je IP/UTC-Tagesfenster, insgesamt weiterhin höchstens 20 Haushalte.
- Eigener `SIGNUP_LIMITER` für kurze Anfragebursts. Er teilt keine Zähler mit dem bestehenden Dienst. Stunden-/Tageskontingente und Kapazität werden zusätzlich in einer D1-Transaktion geprüft; Cloudflares standortbezogene Zähler allein sind keine genaue globale Quote.
- Nur `CF-Connecting-IP` wird berücksichtigt. IP-Adressen gehen nicht im Klartext in die neuen Tabellen oder Logs; die Zähler verwenden einen HMAC mit einem separaten privaten `REGISTRATION_KEY`. IPv6-Schreibweisen werden normalisiert. Wechselnde IPs bleiben ein Grund, zusätzlich die Gesamtgrenze beizubehalten.
- HA erzeugt erst nach bewusstem Bestätigen einen zufälligen 32-Byte-`installation_key`, speichert ihn atomar mit privaten Dateirechten in `.storage` und prüft die Speicherung vor der ersten Anfrage. Der Schlüssel bleibt für Wiederholungen und nach Neustarts erhalten; jeder Server bekommt einen eigenen Schlüssel. Gleicher Schlüssel: gleiches Konto und gleicher Writer, auch nach verlorener Antwort. Neue Geräte-/Kontoverknüpfungen werden dabei nicht angelegt.
- Beim Löschen widerruft der bestehende Weg die Zugangsdaten. Ein Hash-Sperrvermerk verhindert die Wiederbelebung des alten Einrichtungsschlüssels; eine bewusste Neueinrichtung erzeugt einen frischen Schlüssel. Die minimale Sperrvermerk-Aufbewahrung ist in den Datenschutzhinweisen beschrieben.
- Kapazitäts- und IP-Grenzen liefern verständliche Meldungen und `Retry-After`; bestehende Uploads und OAuth-Erneuerungen verwenden diese neuen Kontingente nicht.

## Durchgeführte Freischaltung

1. Produktive Quelle und Einstellungen gesichert; Datenbank-Wiederherstellungspunkt vor der additiven Erweiterung erstellt.
2. Zwei zusätzliche Tabellen angelegt; Haushaltsdaten, ursprüngliche Bindings und Geheimnisse erhalten. Zunächst deaktiviert ausgerollt, danach freigeschaltet.
3. HACS-Flow erkennt `/v2/enrollment`; alte Server bleiben beim Einladungsweg. Ein Konto entsteht erst nach bewusstem Bestätigen. Wiederholungen verwenden den dauerhaft lokal gespeicherten Schlüssel.
4. Lokaler HTTP-Durchlauf und zwei neue Testhaushalte am echten Dienst: Anmeldung ohne Einladung, gleicher Schlüssel → gleiches Konto, getrennte Uploads und passender OAuth-Abruf erfolgreich. Anschließend ausschließlich die beiden Testhaushalte gelöscht. Die vier bisherigen Haushalte bleiben bestehen.

Zusätzlich ist die echte HA-Neueinrichtung ohne Einladung inzwischen bestätigt: eigener Haushalt und erster Messwert-Upload. Zusammen mit dem bestandenen Bestandsupdate bleiben bei Punkt 6 noch Datentrennung am Echo und externe Bestandsupdates offen. Der separate HA-Testhaushalt bleibt erhalten; derzeit fünf Haushalte.

HACS 1.0.11 zeigt den Speicherhinweis mit **Verbinden und übertragen**, ohne zusätzliche Checkbox. Die Anmeldung startet erst beim bewussten Bestätigen. Die neue Expertenbeschriftung ist im Hauptzweig für das nächste Update vorbereitet.

[Cloudflare Rate Limiting](https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/) · [D1-Transaktionen mit batch](https://developers.cloudflare.com/d1/worker-api/d1-database/#batch)
