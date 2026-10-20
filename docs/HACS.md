# Solaranlage v1 über HACS

## Version 1.0.5: Anzeige ohne offene Sprachsitzung

Das Dashboard wird beim Öffnen angezeigt, während die Sprachsitzung sofort endet. Bildschirmaktualisierungen halten die Sprachsitzung ebenfalls geschlossen. Es gibt keine Abschiedsansage. Normale Alexa-Befehle können so wieder direkt verarbeitet werden; Wetter- oder Smart-Home-Karten können die Solaranzeige ersetzen. Eine automatische Rückkehr wird nicht erzwungen.

Die Änderung wurde auf dem Echo Show in der separaten Testversion erfolgreich erprobt. Verhalten und Anzeigedauer bestimmt weiterhin auch das jeweilige Alexa-Gerät. Live-Werte und Kontoverknüpfung werden unverändert verwendet. Ein HA-Neustart oder erneutes Verknüpfen ist für dieses Alexa-Codeupdate nicht erforderlich.

[Änderung und Rückkehr zu 1.0.4](V1.0.5.md) · [1.0.4 bleibt verfügbar](https://github.com/kulmi84/solaranlage-echo-show/releases/tag/v1.0.4)


Die HACS-Version wurde mit echten Messwerten und Kontoverknüpfung auf einem Echo
Show geprüft. Der Skill heißt **Solaranlage**, Sprachaufruf **meine solaranlage**.
Der Alexa-Skill wurde am 19. Oktober 2026 zur Zertifizierung eingereicht;
der zuletzt bestätigte Status lautet **„Wird überprüft“**. Eine öffentliche
Store-Freigabe steht noch aus. Neue Nutzer können den gemeinsamen Skill erst
danach regulär aktivieren; bestehender Entwicklerzugriff funktioniert weiter.
Das Relay erfordert eine Einladung und erlaubt zunächst maximal 20 Haushalte.
Bitte vor der Einrichtung unter support@dorisundmarcin.de nachfragen. Das GitHub-Repository
ist öffentlich und kann in HACS als benutzerdefiniertes Repository hinzugefügt werden.

## Der neue Ablauf für Nutzer

Die Skill-Aktivierung in Schritt 4 setzt die Amazon-Freigabe oder bereits
vorhandenen Entwicklerzugriff voraus. [Status und Voraussetzungen](ALEXA-STATUS.md).

1. `https://github.com/kulmi84/solaranlage-echo-show` als benutzerdefiniertes Repository in HACS
   hinzufügen und **Solaranlage Echo Show** herunterladen. HA neu starten.
2. Einstellungen → Geräte & Dienste → Integration hinzufügen →
   **Solaranlage Echo Show**. Die Einladung des Relay-Betreibers eingeben.
3. Live-Sensoren und kumulierte Energiezähler auswählen und der Übertragung
   zustimmen. Keine YAML-Dateien, HA-Zugangstoken oder eigenen Cloudflare-Konten.
4. In den Integrationsoptionen **Alexa verbinden** wählen. Den einmaligen,
   zehn Minuten gültigen Code kopieren. In der Alexa-App den gemeinsamen Skill
   aktivieren und den Code auf seiner Verknüpfungsseite einfügen.
5. „Alexa, öffne meine Solaranlage.“ Die bekannten Sprachfragen und beide
   Anzeigeseiten bleiben erhalten.

Der Verbindungscode ist lang, damit er nicht erraten werden kann. Er wird
kopiert und eingefügt, nicht auf dem Echo diktiert. Er ersetzt einen eigenen
Benutzernamen und ein Passwort beim Relay.

Die Skill-URL wird nach der Amazon-Freigabe ergänzt. Für den derzeitigen
Entwicklerbetrieb muss der Echo dasselbe Amazon-Konto wie die Developer Console
verwenden. Eine neue Kontoverknüpfung ist bei der Umbenennung der HACS-Beta nicht nötig.

## Sensorauswahl

- PV-Gesamtleistung in W/kW ist Pflicht und enthält das BKW bereits.
- Weitere Leistungen und Akkustand in Prozent sind optional.
- **Hausverbrauch prüfen:** Eine Energieflusskarte kann diesen Wert selbst berechnen.
  Ein gleichnamiger Sensor muss nicht dieselbe Berechnung liefern. Vergleiche die
  Auswahl mit der Karte. Die Bilanz lautet: PV inklusive BKW + Netzbezug +
  Akkuentladung − Einspeisung − Akkuladung. Für die getestete Anlage wird ein
  eigener Template-Helfer mit dieser Bilanz als Hausverbrauch ausgewählt.
- Energiezähler in Wh/kWh/MWh müssen kumulierte Recorder-Zähler sein
  (`total`/`total_increasing`). Keine täglich zurückgesetzten Anzeigehelfer.
- Der PV-Energiezähler enthält das separat gewählte BKW nicht bereits.
  Doppelt ausgewählte Energiezähler werden abgewiesen.
- Fehlende Werte bleiben unbekannt. Für die berechnete Hausenergie sind alle
  sechs Energiequellen erforderlich. Bei nicht vorhandenen BKW/Akku-Komponenten
  sind bewusst definierte Nullzähler erforderlich; Abwesenheit wird nicht geraten.

Live-/Tageswerte werden minütlich übertragen. Monat und Jahr werden beim Start
und nach einem Wechsel des lokalen Sechs-Stunden-Fensters ermittelt. Nach
vorübergehend fehlender Recorder-Statistik wird erneut versucht. Ein lokaler
Verbindungssensor zeigt letzten Upload, Status und fehlende Messwertarten.
Die Integration überträgt keine Entitäts-IDs oder HA-Zugangsdaten.

Die vorhandenen Statistiken bestimmen den verfügbaren Zeitraum. Daten aus
Zeiten vor der Recorder-Erfassung werden nicht nachträglich erfunden.

## Änderungen und Entfernen

Sensoren lassen sich in den Integrationsoptionen ändern. Änderungen laden die
Integration neu. **Relay-Daten und Verknüpfung löschen** entfernt nach ausdrücklicher
Bestätigung alle gespeicherten Relay-Messwerte und Zugriffsberechtigungen dieses
Haushalts. Anschließend die Integration in HA entfernen. Zum erneuten Einrichten
ist eine neue Einladung nötig.

Das bloße Entfernen der lokalen HA-Integration löscht Remote-Daten nicht. Wenn
HA nicht mehr erreichbar ist, muss der Betreiber den betreffenden Haushalt auf
Anfrage aus der Relay-Datenbank entfernen. Deshalb erst im Optionsdialog löschen.

## Betreiber: gemeinsames Relay

**Betriebsstand vom 19. Oktober 2026:** Die aktive D1-Datenbank heißt
`solaranlage`, das Worker-Binding weiterhin `DB`. Der bisherige Datenbankstand
wurde vollständig übertragen und geprüft; `solaranlage-public-beta` wurde danach
gelöscht. Worker-Name, Relay-URL und OAuth-Client-ID bleiben zur Kompatibilität
unverändert. Bestehende Nutzer müssen nichts neu verknüpfen.
Details und Wiederherstellung: [Datenbank und Sicherung](DATENBANK.md).

Der neue Code liegt in `cloudflare/public-beta/`; er verwendet eine **neue**
D1-Datenbank und andere Tabellen. Den bestehenden Einzelanlagen-Worker nicht
ersetzen und die bisherige Datenbank nicht für diese Migration verwenden.

1. Neue D1-Datenbank erstellen; `wrangler.example.jsonc` in eine private
   `wrangler.jsonc` kopieren und nur deren neue Datenbank-ID einsetzen.
2. `schema.sql` auf diese neue Datenbank anwenden. `ADMIN_TOKEN` und
   `OAUTH_CLIENT_SECRET` als zwei getrennte zufällige 32-Byte-Secrets setzen.
   Nicht committen. Vorhandene produktive Secrets nicht wiederverwenden.
3. In der separaten Alexa-Entwicklungsversion Account Linking konfigurieren:

   | Einstellung | Wert |
   | --- | --- |
   | Verfahren | Authorization Code Grant, PKCE mit SHA-256 |
   | Authorization URI | `https://NEUES-RELAY/oauth/authorize` |
   | Token URI | `https://NEUES-RELAY/oauth/token` |
   | Client ID | `solaranlage-public-beta` |
   | Client Secret | eigenes `OAUTH_CLIENT_SECRET` |
   | Client-Authentifizierung | HTTP Basic oder Credentials im POST-Body |
   | Scope | `solar:read` |

4. Ausschließlich die **exakten Alexa Redirect URLs aus dieser Skill-Konsole**
   in `OAUTH_REDIRECT_URIS` als JSON-Liste eintragen. Keine Wildcards. Bei leerer
   Liste bleibt OAuth gesperrt. Worker deployen. `LIMITER` muss gebunden sein;
   ohne dieses Binding verweigert die API Anfragen.
5. In `custom_components/solaranlage_echo/const.py` den neuen Relay-Origin
   prüfen. Die Voreinstellung bezeichnet den bestehenden Relay-Worker und ist
   keine Zusicherung, dass er bereits bereitgestellt wurde.
6. Separate Alexa-Konfiguration nach `alexa/relay_config.public.example.json`
   erstellen, `mode: public_beta` und die neue `/v1/pv`-Adresse verwenden.
   `python build_skill.py` erzeugt das Backend. Nur die neue Skill-Testversion
   damit bereitstellen; die eigene laufende Skill-Version bleibt unangetastet.
7. Eine private Admin-Datei mit `relay_url` und `admin_token` erstellen. Einladung:

   ```sh
   python cloudflare/public-beta/admin.py --config .private/beta-admin.json --out .private/einladung-1.json
   ```

   Die Einladung ist einmalig und sieben Tage gültig. Sie enthält ein Geheimnis,
   ist nur für den jeweiligen Tester bestimmt und gehört nicht in GitHub.
   Höchstens 20 Haushalte können sich registrieren.

## Trennung und Grenzen

```mermaid
flowchart LR
  HA[HA-Integration] -->|Haushalts-Schreibschlüssel| W[Gemeinsames Relay]
  W --> D[(D1: Datensatz je Haushalt)]
  A[Gemeinsamer Alexa-Skill] -->|OAuth-Lesetoken des Aufrufers| W
  HA -. einmaliger Verbindungscode .-> O[OAuth-Verknüpfung]
  O --> A
```

Tokens werden serverseitig nur gehasht gespeichert. Alexa bekommt ausschließlich
Lesezugriff auf den verknüpften Haushalt. Zugriffstokens gelten eine Stunde;
Refresh-Tokens rotieren und gelten maximal 90 Tage. Verknüpfungs- und
Autorisierungscodes sind einmalig. Löschung eines Haushalts widerruft alle Tokens.
IP-Limits und zeitliche Upload-Limits schützen vor einfachen Wiederholungen;
sie sind keine Garantie gegen verteilten Missbrauch oder gegen das Erreichen
der gemeinsamen Cloudflare-Kontolimits. Das Relay ist keine Steuer-API.

Es werden jeweils nur letzte Messwerte und aktuelle Tages-/Monats-/Jahresmengen
gespeichert, keine komplette Messwerthistorie. Ohne ausdrückliche Löschung
bleibt der letzte Haushaltsdatensatz bestehen. Abgelaufene Codes/Tokens räumt
ein täglicher Cron auf. Eine Datenschutzbeschreibung für den öffentlichen
Betrieb muss diese Speicherung, Betreiberkontakt und Löschmöglichkeit nennen.

## Stand der Prüfung und Freigabe

Automatisierte Tests prüfen Umrechnung, fehlende Werte, HA-Dialogübergänge,
Upload-Zeitsteuerung und Relay-Transport. Die HA-Framework-Grenzen verwenden
Test-Doubles; eine Installation in einer echten HA-Testinstanz steht noch aus.
Die Worker-Tests führen Registrierung, OAuth, PKCE, Token-Erneuerung und
Haushaltstrennung gegen eine echte lokale SQLite-Datenbank aus. Bestehende
Anzeige- und Sprachtests werden zusätzlich ausgeführt.

Das gemeinsame Relay wurde am 18. Oktober 2026 bereitgestellt. Installation
über HACS, minütliche Übertragung, iOS-Kontoverknüpfung und beide Anzeigeseiten
wurden mit einer echten Anlage geprüft. Die getestete Version wurde am
19. Oktober als v1.0.0 veröffentlicht. v1.0.1 aktualisiert Anleitungen,
Einrichtungstexte und die im Release enthaltenen Bildschirmaufnahmen.

## Anzeige in HACS aktualisieren

HACS liest Repository- und Release-Daten nicht immer sofort neu ein. Im
Repository-Menü **Informationen aktualisieren** verwenden, sofern angeboten,
und die Ansicht neu laden. Prüfe, ob **1.0.4** als aktuelle Version angezeigt wird.
**Herunterladen/Erneut herunterladen** aktualisiert die Integration; damit neue
Einrichtungsübersetzungen geladen werden, kann anschließend ein HA-Neustart
nötig sein. Die README in HACS und die installierte Integrationsversion sind
unterschiedliche Dinge. Bestehende Sensoren und die Kontoverknüpfung bleiben erhalten.

## Integrationssymbol und HACS-Platzhalter

Das weiße Logo auf schwarzem Hintergrund wird als lokale Brand-Datei unter
`custom_components/solaranlage_echo/brand/` mitgeliefert. Home Assistant unterstützt
diese Symbole ab Version 2026.3. Das Logo in der Beschreibung ist davon unabhängig.

Ältere HACS-Versionen laden das Listensymbol weiterhin von einem zentralen CDN
und zeigen für neue Integrationen deshalb „icon not available“. Erneutes Laden
der Beschreibung behebt diesen HACS-Fehler nicht. Laut den Entwicklern ist die
Korrektur im Marketplace von Home Assistant 2026.11 enthalten; dafür keine
Vorabversion auf einem produktiven System installieren.

Quellen: [Lokale Integrationssymbole](https://contributors.home-assistant.io/blog/2026/02/24/brands-proxy-api/),
[HACS-Fehlerbericht #5402](https://github.com/hacs/integration/issues/5402).

## Einreichung und verbleibende Freigabe

- Kontoverknüpfung mit zwei getrennten echten Testhaushalten prüfen.
- Datenschutz- und Kontaktseite sind erreichbar; die Store-Beschreibung ist ergänzt.
- Die automatische Amazon-Validierung hat keine Fehler gemeldet. Ein eigener,
  zeitlich begrenzter Demo-Zugang mit künstlichen Werten ist für das Prüfteam hinterlegt.
- Am 19. Oktober 2026 erfolgreich eingereicht. Amazons Entscheidung steht aus;
  automatische Veröffentlichung nach erfolgreicher Zertifizierung ist gewählt.
- Optional Aufnahme in den HACS-Standardkatalog; das öffentliche benutzerdefinierte
  Repository ist bereits nutzbar.

[Datenschutz](https://solaranlage-public-beta.kulmi84.workers.dev/privacy) ·
[Kontakt](https://solaranlage-public-beta.kulmi84.workers.dev/contact) ·
[Technische Einreichungsdokumentation](STORE-PUBLISHING.md)

Interne Namen wie `public-beta`, `public_beta` und ältere `pv_beta`-Dateien bleiben
für bestehende Verknüpfungen und Installationen erhalten. Sie sind keine
Versionsangabe. Private Konfigurationen bleiben außerhalb von Git.

Quellen: [HACS-Anforderungen](https://www.hacs.dev/docs/publish/integration/),
[Private Repositories](https://www.hacs.dev/docs/faq/private_repositories/),
[HA Config Flow](https://contributors.home-assistant.io/core/integrations/config-flow/),
[Amazon Account Linking](https://developer.amazon.com/docs/alexaplus/account-linking/configure-authorization-code-grant.html).
