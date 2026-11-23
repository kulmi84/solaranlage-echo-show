# Projektstatus · 23.11.2026

- **1.1.0 (Build 2211)** ist veröffentlicht; Amazon meldet Live/PUBLISHED seit23.11.10:59 Berlin.
- Live-Vollbildkorrektur bereitgestellt: Ein authentifizierter Store-Start bindet jetzt den verifizierten Datenspeicher an, statt nur einmal aktuelle Werte zu laden. Token-Haushalt und bestehende Gerätebindung müssen übereinstimmen. Hosted `dc8d519`, Worker `b23725e6`.
- **216 Python-/74 Worker-/74 Bündeltests erfolgreich. Echo-Nachtest: weiterhin keine automatische Aktualisierung; erster Fix reicht nicht.** Ein neues Vollbilddokument muss durch erneutes Öffnen geladen werden.
- Kleine Live-Kachel des Entwicklers noch nicht als repariert bestätigt. Frische Live-Instanzen sind aktiv; während der begrenzten Kontodiagnose kam bisher kein neuer eigener Abruf an. Andere Haushalte erhalten weiterhin von Amazon akzeptierte Zustellungen; das beweist keine sichtbare Anzeige.
- DEV-Paket, Sprache, Sprachsitzung, Layout, Testmodus und Kontoverknüpfung in diesem Schritt unverändert. Kein Widerruf zurückgesetzt. DEV ist aktuell für das Entwicklerkonto nicht aktiviert; Wiederherstellung separat offen.
- Ruhemodus2211 bleibt erhalten. Nur PR22 aktualisiert, kein Merge. Quellen und Rücksprung lokal gesichert.

[Grundlage und Rücksprung2111](ALEXA-WIEDERHERSTELLUNG-2111.md)


## Folgekorrektur Live-Vollbild

Bei ausbleibenden Datenspeicher-Updates nutzt nur das Live-Vollbild den vorhandenen verifizierten Abruf alle60Sekunden. Pro sichtbarer Vollbildrunde kommt dann ein Worker-Aufruf hinzu; keine Zahlenbilder. Monats-/Jahresseite bleibt bei6Stunden. Ausblenden pausiert, Aufwachen aktualisiert; Fehler erhalten die letzten Werte. DEV, Sprache und Layout bleiben erhalten.

219 Python-Tests erfolgreich. Hosted `867658c` nach erfolgreichem Development-Deploy nach Live übergeben. Echo-Nachweis noch offen; kleine Store-Kachel weiterhin leer gemeldet.


## Kleine Kachel: belegte Sperrkollision

Eine eigene automatische Minute wurde mit503 `delivery_busy` abgewiesen, der folgende Einblendabruf erfolgreich beantwortet und zugestellt. Der Live-Adapter behandelt jetzt nur diesen vorübergehenden Sperrfall mit erneutem Versuch nach5Sekunden. Die Sperre, Kontoprüfungen, andere Fehlerabstände und der Ruhemodus bleiben erhalten; DEV unverändert. Hosted `494b3e0` ist bereitgestellt,226 Python-Tests bestanden. **Sichtbare Werte und automatische Vollbildrunden am Echo noch nicht bestätigt.**
