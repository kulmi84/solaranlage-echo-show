# Projektstatus · 31.10.2026

- **HACS 1.0.11 veröffentlicht:** Einrichtung ohne Einladung, abschließend **Verbinden und übertragen** statt Zustimmungscheckbox; Hinweis zum jeweils letzten gespeicherten Datensatz.
- **Bildwidget 2.0.1 am Echo bestätigt:** Nachladen beim Einblenden, automatische Zugangserneuerung, kompletter Bildpuffer, passende Vollbildansicht und weiße Fußzeile. Gerätefoto ohne erkennbaren Hintergrund; Vollbild-Übersichtsbild beibehalten.
- **Punkt 6 teilweise bestanden:** Bestandsupdate ohne Neuverknüpfung und echte HA-Neueinrichtung ohne Einladung samt Upload bestätigt. Der Testhaushalt ist separat angelegt; fünf Haushalte vorhanden. Datentrennung am Echo noch offen.
- 28 Python-Tests einschließlich HTTP-Durchlauf bestanden; Backend unverändert seit den 24 erfolgreichen Backendtests. Die zwei früheren automatisierten Testkonten wurden gelöscht; der jetzige HA-Testhaushalt bleibt erhalten.
- Die Beschriftung **Eigenen Solaranlage-Dienst verwenden (Expertenoption)** ist im Hauptzweig vorbereitet und noch nicht Teil des Releases 1.0.11.

## Erhaltene Skills

| Skill | Aufgabe |
|---|---|
| Data Store Labor | Enthält das funktionierende Bildwidget SolarAccountImage 2.0.1; historischer Name. |
| Solaranlage | Öffentlicher Skill samt Development für bestehende Nutzer. |
| Mein Zuhause | Separates Projekt, unverändert. |

## Noch offen

6. Datentrennung der Haushalte am Echo; Updates der externen Bestandsinstallationen nachhalten.
7. Zwei Weiterleitungen nach vollständiger HA-/Alexa-/Bildmigration entfernen.
8. Widget-Runtime integrieren, abschließend prüfen und bei Amazon veröffentlichen.

Cloudflare: weiterhin **6 Worker / 2 Datenbanken**. Zwei Worker sind Übergangsweiterleitungen, einer ist der separate Tageslimit-Warner. Keine weitere Löschung im Rahmen dieser Aktualisierung.

[Checkliste #10](https://github.com/kulmi84/solaranlage-echo-show/issues/10) · [Widget-Entwurf PR #9](https://github.com/kulmi84/solaranlage-echo-show/pull/9)
