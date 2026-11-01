# Änderungsverlauf

Die ausführlichen Änderungen stehen hier. Die [Projektübersicht](README.md) beschreibt die Funktionen und zeigt die Ansichten.

## 1.0.11 – Einrichtung und Datenübertragung

- Die Datenübertragung wird über „Verbinden und übertragen“ bestätigt; eine zusätzliche Zustimmungs-Checkbox entfällt.
- Der Einrichtungstext erklärt die Speicherung: Für die Anzeige bleibt der letzte Datensatz erhalten. Ein erfolgreicher Live-/Tagesupload ersetzt ihn normalerweise alle 60 Sekunden. Bei einem fehlgeschlagenen Upload bleibt der bisherige Stand erhalten.
- Monats- und Jahresübersichten werden getrennt aktualisiert. Es wird keine fortlaufende Messwert-Zeitreihe beim Dienst angelegt.
- Bestehende Konten, Sensorzuordnungen und Alexa-Verknüpfungen bleiben erhalten.
- Die Neueinrichtung ohne Einladung wurde in einer separaten Home-Assistant-Testumgebung mit erfolgreichem Upload bestätigt.
- Geprüft: 28 Python-Tests; der zuvor geprüfte Backendstand umfasst 24 Tests.

## 1.0.10 – Hinweise zur Einrichtung

- Hinweise zur Speicherung und zur Übertragung ausgewählter Messwerte ergänzt.
- Feldhilfen unterscheiden Live-Leistung von kumulierten Energiezählern.
- Bestehende Energiezähler können weiterverwendet werden; optionale Felder dürfen leer bleiben.

## Bildwidget 2.0.1 – bestätigter Gerätestand

- Gemeinsame Kontoverknüpfung für Widget und Vollbild.
- Nachladen beim Sichtbarwerden und regelmäßige Aktualisierung.
- Automatische Erneuerung des Bildzugangs im verkürzten Ablauftest bestätigt.
- Der letzte vollständige Bildsatz einschließlich Zeitstand bleibt bei Ladefehlern erhalten, bis der neue vollständig geladen ist.
- Antippen öffnet die überprüfte Vollbildansicht.
- Versions- und Aktualisierungshinweis unter dem Datenstand in Weiß.
- Die allgemeine Amazon-Veröffentlichung und die verbleibenden Abnahmen werden getrennt in [#10](https://github.com/kulmi84/solaranlage-echo-show/issues/10) geführt.

## Hauptzweig – noch nicht als neue HACS-Version veröffentlicht

- Expertenoption umbenannt in „Eigenen Solaranlage-Dienst verwenden (Expertenoption)“.
- Projektbeschreibung mit Gerätefoto des kleinen Widgets und Bildern der Vollbildansicht überarbeitet.
- Ausführlicher Änderungsverlauf von der kurzen Projektbeschreibung getrennt.

## Frühere Versionen

Die folgenden Einträge beschreiben den jeweiligen damaligen Stand. Angaben zu privaten Prototypen und früheren Zugängen sind historische Informationen.

## Version 1.0.9: Einrichtung ohne Einladung

HACS einrichten, Sensoren auswählen und der Übertragung zustimmen. Ein Konto wird automatisch angelegt; Alexa wird anschließend wie bisher einmal verbunden. Begrenzung je Internetanschluss schützt den Dienst. Bestehende Konten und Verknüpfungen bleiben erhalten. Dieses HACS-Update veröffentlicht oder ersetzt kein Amazon-Widget.

[Einrichtung](docs/HACS.md) · [Änderungen und Rückkehr](docs/V1.0.9.md)

## Version 1.0.8: Bild-Widget mit scharfer Stand-Zeile

**Vom Betreiber auf dem Echo Show bestätigt:** transparente große Werte, tatsächliche Empfangszeit, Aktualisierung alle 60 Sekunden und Antippen zur normalen Vollbildansicht. Der separate widerrufbare Bildzugang benötigt kein tägliches Neuöffnen. Der Alexa Data Store wird für diese Werteanzeige nicht verwendet.

**GitHub/HACS und Amazon sind getrennt:** Diese Version sichert den funktionierenden Bildweg. Das private Betreiber-Widget läuft; eine allgemeine Store-Auslieferung benötigt noch eine individuelle Bildzugangsbereitstellung für jedes verknüpfte Konto. HACS allein installiert kein Widget. Vollbild und Sprachbefehle bleiben unverändert.

[Änderungen und Rücksprung](docs/V1.0.8.md) · [Widget-Quellcode und bebilderte Anleitung](experiments/widget-image/README.md)

## Version 1.0.7: Status der Solaranlage vorlesen

**„Alexa, frage meine Solaranlage nach dem Status.“** liest Leistung inklusive BKW, Hausverbrauch, Akkustand, heutige Produktion, aktuellen Netzbezug, aktuelle Einspeisung und das Alter der Werte vor. Fehlende Daten werden benannt; nach mehr als drei Minuten ohne Upload warnt die Ansage vor veralteten Werten.

**Der Start bleibt „Alexa, öffne meine Solaranlage.“** Die Echo-Show-Anzeige, Aktualisierung alle 60 Sekunden und der Anzeigezugang für bis zu 24 Stunden bleiben erhalten. Die Statusabfrage beendet die Sprachsitzung ohne erneutes Rendern der Anzeige.

Die Funktion wurde im separaten Test-Skill am Gerät bestätigt. Ihre Verfügbarkeit im gemeinsamen Skill hängt von der zentralen Bereitstellung und Amazons Modellfreigabe ab; ein HACS-Update allein aktiviert sie nicht. [Details zu v1.0.7](docs/V1.0.7.md).

**Festgelegter Rücksprungstand: [v1.0.6](https://github.com/kulmi84/solaranlage-echo-show/releases/tag/v1.0.6)**, zusätzlich im Archivzweig `codex/archive-v1.0.6`. Tag und damaliger Quellcode bleiben unverändert.

## Version 1.0.6: Solaranzeige bleibt sichtbar – Alexa kann wieder zuhören

**Die Solaranzeige bleibt sichtbar und aktualisiert ihre Werte alle 60 Sekunden, während die Sprachsitzung des Skills bereits geschlossen ist. Normale Alexa-Befehle benötigen dadurch kein vorheriges „Alexa, stopp“.** Alexa entscheidet über die Zuordnung der Anfrage; Wetter- oder Smart-Home-Karten können die Ansicht ersetzen. Keine automatische Rückkehr.

**Ausgangspunkt:** Die bisherige native Anzeige lieferte die Werte, gab im beobachteten Vollbildbetrieb normale Alexa-Anfragen aber nicht zuverlässig frei. Bei geschlossener Sprachsitzung funktionierte die bisherige SendEvent-Aktualisierung nicht zuverlässig. Die neue Version lädt deshalb nur die Wertebereiche als geschützte Bilder nach; Überschriften, Kacheln, Navigation und Schaltflächen bleiben nativ und behalten die bisherige Größe.

Der eigene Anzeige-Lesezugang gilt **bis zu 24 Stunden ab dem Öffnen**, unabhängig vom kürzeren Alexa-Token. Danach erneut öffnen. Die verlängerte Beta hat den Gerätetest und den vom Betreiber bestätigten Langzeittest bestanden. Alexa kann die Ansicht trotzdem früher ersetzen oder schließen.

**Update:** „Alexa, öffne meine Solaranlage.“ erneut starten. Keine neue Kontoverknüpfung und kein HA-Neustart für das zentrale Alexa-Update erforderlich. HACS 1.0.6 kennzeichnet denselben Release; es aktualisiert nicht selbst den zentralen Alexa-Code.

[Änderungen, Einrichtung des Bilddiensts und Rückkehr zu 1.0.5](docs/V1.0.6.md) · [v1.0.5 bleibt erhalten](https://github.com/kulmi84/solaranlage-echo-show/releases/tag/v1.0.5)



## Archiv und weiterführende Dokumentation

Die vollständige frühere Projektbeschreibung einschließlich der damaligen technischen Einrichtung bleibt im [README-Archiv](docs/ARCHIV-README-2026-10.md) erhalten. Aktuelle Einrichtung: [HACS](docs/HACS.md). Aktueller Entwicklungs- und Veröffentlichungsstand: [Projektstatus](docs/ALEXA-STATUS.md).
