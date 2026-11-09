# Betasolaranlage

**Version 4.0.0 (Build 0911)**

Die Buildnummer verwendet das Datum im Format `TTMM`. Der erste Build am 9. November ist `0911`. Weitere Builds am selben Tag erhalten eine fortlaufende Endung, also `0911.1`, `0911.2` und so weiter. Version und Build stehen im Vollbild und werden in `lambda_function.py` gepflegt.

Separater Alexa-Entwurf für den Vergleich mit der bestehenden Vollbildanzeige. Der deutsche Aufruf lautet **„Alexa, öffne Betasolaranlage“**. Das Vollbild hat einen dunkelroten Hintergrund. Beide Seiten behalten ihre Kacheln, Farben, Wisch-Navigation, „Aktualisieren“ und „Stand“-Zeile. Die Messwerte erscheinen als native APL-Texte. „Live / Heute“ fragt bei sichtbarer Seite alle 60 Sekunden ab. „Monat & Jahr“ fragt alle sechs Stunden ab und zeigt die lokale Uhrzeit des letzten Uploads der Monats- und Jahressummen.

Der Backend-Code schließt die Sprachsitzung nach dem Öffnen. Für die Aktualisierung sendet die sichtbare Ansicht ein APL-Ereignis. Die Antwort aktualisiert nur die Texte der betreffenden Seite. Bei einem vorübergehenden Abruffehler bleiben die zuletzt angezeigten Zahlen sichtbar.

Für den späteren Test einen separaten Custom Skill namens **Betasolaranlage** mit `de-DE` und der APL-Schnittstelle vorbereiten. Das JSON-Sprachmodell importieren. `lambda_function.py`, `relay_reader.py` und `relay_config.example.json` unter dem Namen `relay_config.json` in die Python-Laufzeit übernehmen. Die getrennte Alexa-Kontoverknüpfung verwendet eine passende OAuth-Konfiguration mit `solar:read` für den Kontodienst. Die OAuth-Weiterleitungs-URLs des Beta-Skills vor dem Verknüpfen abgleichen. Echte Zugangsdaten gehören ausschließlich in die private Alexa-Konfiguration.

Beim Gerätetest die Erkennung des Aufrufnamens, beide Ansichten und eine automatische Aktualisierung prüfen. Besonders relevant ist, ob der Echo den APL-Abruf nach dem Ende der Sprachsitzung zustellt und auf normale Alexa-Befehle reagiert.
