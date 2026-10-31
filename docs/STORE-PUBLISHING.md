# Alexa-Store: Vorbereitung und Betrieb

> Historische Einreichungsdokumentation. Aktuell: normaler Skill öffentlich, Bildwidget 2.0.1 im separaten Skill am Gerät bestätigt; sein allgemeiner Amazon-Rollout bleibt offen. Maßgeblich ist der [aktuelle Projektstatus](ALEXA-STATUS.md).

Stand: 19. Oktober 2026. Eine erfolgreiche automatische Validierung ist noch
keine Amazon-Zertifizierung und keine Zusage einer Store-Freigabe.

**Einreichung erfolgt:** Amazon bestätigt am 19. Oktober 2026 die Übermittlung;
der Skill-Status lautet „Wird überprüft“. Modus: Zertifizieren und veröffentlichen.
Die automatische Validierung meldet keine Fehler. 40 Python-Tests und 12 Worker-
Tests bestehen; der bereitgestellte Demo-OAuth-/PKCE-Ablauf, fünf Sprachabfragen
und ein stiller APL-Start wurden zusätzlich geprüft. Die Entscheidung von Amazon
steht aus. Der Demo-Zugang gilt bis zum 18. Dezember 2026 und muss bei einer
längeren Prüfung kontrolliert erneuert werden.

## Öffentliche Angaben

- Datenschutz: https://solaranlage-public-beta.kulmi84.workers.dev/privacy
- Kontakt: https://solaranlage-public-beta.kulmi84.workers.dev/contact
- Betreiber: Marcin Kulmaczewski, support@dorisundmarcin.de
- Auf diesen Projektseiten wird keine private Anschrift veröffentlicht.
  Daraus folgt keine rechtliche Zusicherung über Anbieterpflichten.
- Die Beschreibung nennt Home Assistant, die HACS-Integration, Kontoverknüpfung,
  persönliche Einladung und das anfängliche Limit von 20 Haushalten ausdrücklich.

## Getrennte Demo-Anlage für die Zertifizierung

`/review` ist nur mit vollständig gesetzten `REVIEW_TENANT_ID`,
`REVIEW_KEY_HASH` und `REVIEW_EXPIRES` aktiv. Eine normale Haushaltskennung kann
nicht als Demo-Ziel verwendet werden: die Kennung muss mit `review-` beginnen.
Der Betreiber legt ausschließlich einen leeren separaten Demo-Haushalt an.

Ein zufälliger 32-Byte-Prüfschlüssel wird privat erzeugt. Nur dessen SHA-256-Hash
gehört in die Worker-Konfiguration. Der Klartextschlüssel gehört ausschließlich
in Amazons nicht öffentliche Testhinweise und in eine lokale private Sicherung.
Er darf nicht in Git, öffentliche Screenshots, die Store-Beschreibung oder URLs.

Nach Eingabe des Schlüssels erzeugt die Seite einen einmaligen Verbindungscode.
Der reguläre OAuth-/PKCE-Ablauf bleibt unverändert; der Zugriff ist auf die
künstlichen Werte dieses Demo-Haushalts beschränkt. Die normalen Schreibrechte
werden dadurch nicht erweitert. Beim Lesen werden ausschließlich für diesen
separaten Demo-Haushalt synthetische Werte mit aktuellen Zeitstempeln erzeugt.
PV: 3,2 kW; Haus: 1,2 kW; Akku: 72 %; Tagesproduktion: 18 kWh;
Tageseinspeisung: 7 kWh. Keine Kundendaten werden für die Prüfung benötigt.

Die aktuelle Prüfkonfiguration läuft nach 60 Tagen ab. Danach verweigern sowohl
die Prüfseite als auch bereits ausgegebene Demo-Lesetoken den Zugriff. Bei einer
längeren Prüfung Zugang kontrolliert erneuern und Amazons Testhinweise anpassen.
Zum Abschalten die drei REVIEW-Variablen entfernen und neu deployen. Normale
Haushalte sind davon nicht betroffen.

## Prüfungen vor dem Einreichen

- Automatische Amazon-Validierung erneut ausführen und Ergebnis prüfen.
- Datenschutzseite und Store-Angaben im Browser prüfen.
- Getrennten Demo-OAuth-Fluss mit PKCE einschließlich Messwertabruf testen.
- Alle fünf Sprachabfragen und stillen APL-Start mit dem Demo-Relay prüfen.
- Export-Compliance-Erklärung durch den Betreiber persönlich prüfen/bestätigen.
- Nicht öffentliche Testhinweise müssen wiederholbares Verknüpfen erklären.
- Den tatsächlich gewählten Veröffentlichungsmodus vor Einreichung prüfen.

Die Erweiterung betrifft ausschließlich das Relay und die Einreichungsangaben.
Die bestehende HA-Sensorauswahl und der auf dem Echo installierte Anzeige-Code
werden nicht verändert. Lokale Rückkehrdateien und der vollständige
Projektstand sind außerhalb des öffentlichen Repositorys gesichert.
