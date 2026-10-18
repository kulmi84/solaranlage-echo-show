# Einrichtung mit Fenster statt Terminalbefehlen

Die neue Einrichtung läuft lokal auf deinem PC. Die bestehende Anlage wird
nicht umgestellt. Für die neue Installation werden ein eigener Worker und eine
eigene Datenbank mit zufälligem Namen erstellt.

## Einmal vorbereiten

Installiere Python 3.8 oder neuer **mit Tcl/Tk** und Node.js LTS mit npm.
Lade das Projekt herunter und entpacke es. Ein kostenloses Cloudflare-Konto
und ein Amazon-Entwicklerkonto werden benötigt.

## Drei Schritte im Assistenten

1. Unter Windows **Einrichtung-starten.bat doppelklicken**. Alternativ
   `python setup_app.py` ausführen. HA-Adresse und persönlichen HA-Zugangstoken
   eingeben, **Sensoren laden** anklicken. Der Token bleibt nur im Speicher und
   wird nach dem Lesen aus dem Eingabefeld gelöscht. HTTPS muss ein gültiges
   Zertifikat haben; HTTP im Heimnetz verlangt eine ausdrückliche Bestätigung.
2. Sensoren in den Auswahllisten auswählen. Vorschläge anhand vorhandener
   Entitäts-IDs bitte prüfen. Nur PV-Gesamtleistung ist Pflicht. Optionale Felder
   dürfen leer bleiben. Für Tages-, Monats- und Jahresmengen die kumulierten
   Energiezähler wählen, die auch HA für seine Statistik verwendet. PV-Energie
   ohne das separat ausgewählte BKW verwenden. Fehlende Quellen bleiben unbekannt.
3. **Neues Relay erstellen und Dateien erzeugen** anklicken. Nach Bestätigung
   bei Cloudflare im Browser anmelden. Der Assistent erstellt Datenbank,
   Schema, Worker und getrennte Schlüssel. Namen, Datenbank-ID und Relay-Adresse
   werden automatisch übernommen. Keine Befehle oder Schlüssel kopieren.

Wrangler 4 wird über npm ausgeführt. Die Einrichtung bucht keinen Tarif;
die Cloudflare-Kontolimits gelten. Bei mehreren Cloudflare-Konten kann eine
eindeutige Kontoauswahl außerhalb des Assistenten nötig sein. Fehlt die
Workers-Subdomain im Konto, diese zuerst im Cloudflare-Dashboard einrichten.

## Was noch in HA und Amazon erforderlich ist

**Dateien und Checkliste öffnen** zeigt den privaten Ausgabeordner. Die
Checkliste enthält die konkreten nächsten Schritte:

- Zwei fertige HA-Packages und ergänzende Secrets übernehmen, Konfiguration
  prüfen und laden. Bestehende Dateien und Secrets nicht ersetzen. Beim
  erstmaligen Einbinden von Packages ist ein HA-Neustart nötig.
- **Verbindung prüfen** anklicken, sobald HA den ersten Upload gesendet hat.
- Bei Amazon einen Custom-Skill mit Alexa-hosted Python anlegen, das fertige
  Sprachmodell importieren, APL einschalten und die zwei erzeugten Dateien
  hochladen. Anschließend Development aktivieren und testen.

Damit entfallen die manuelle Worker-Konfiguration, Datenbank-ID, Schlüsselerzeugung,
Relay-URL und das Zusammenbauen des Alexa-Codes. Die Anmeldung, das HA-Package
und das Anlegen des eigenen Entwickler-Skills bleiben erforderlich. Das ist
noch keine vollständig automatische Installation und kein öffentlicher Skill.

## Fehler und Abbruch

Ein bestehender Ausgabeordner wird abgewiesen. Bei einem Fehler können neue
Cloudflare-Teilressourcen bestehen bleiben. Der Name beginnt mit `solaranlage-`
und wird bei einem Cloudflare-Fehler angezeigt; diese im Konto prüfen, bevor du
neu startest. Es erfolgt kein automatisches Löschen. Dateien und Schlüssel im
privaten Ausgabeordner aufbewahren und niemals veröffentlichen.

Die Bereitstellung wurde mit simulierten Cloudflare-Antworten getestet.
Eine vollständige Neuinstallation auf einem frischen Konto ist noch ausstehend.
Die laufende Anlage wurde dafür nicht verändert.
