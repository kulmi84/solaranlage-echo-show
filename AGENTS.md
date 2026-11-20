# Solaranlage: bekannte Widget-Auslieferungsfalle

Vor Änderungen an Alexa-Widgets `docs/ALEXA-WIDGET-AUSLIEFERUNG.txt` lesen.
Am 28.10.2026 und 10.11.2026 blieb auf dem Echo trotz geändertem Dokument,
erfolgreichem Build und bestätigtem Installationsauftrag der alte Stand sichtbar.
Der am Gerät bestätigte Ausweg war eine neue Paketkennung im selben Skill.
Nicht wieder stundenlang dieselbe Paketkennung bauen/installieren oder dafür
vorschnell ein Amazon-Ticket eröffnen. Vor einem neuen Paket alte Quellen und
Development-Code sichern; neue Paketkennung mit dem Nutzer abstimmen.
Versandbestätigungen sind kein Gerätebeweis. Live nicht nebenbei ändern.

# Solaranlage: bestätigte DEV-Wiederherstellung vom 20.11.2026

DEV 1.1.0 (Build 1811), Paket Solaranlage1811: Nutzer bestätigte nach dem Fix
wieder funktionierende Werteaktualisierung UND Vollbild per Tipp am Echo.
Der tokenlose DEV-Refresh hatte den bisherigen DataStore-Schreibschritt
ausgelassen. Eine ExecuteCommands-Antwort allein reichte in diesem Fehlerfall
nicht. Funktionierender Stand: dieselbe verifizierte Messung als Antwort UND
ein gemeinsames PUT_OBJECT mit Solar, Hausverbrauch, Akku und Originalzeitstempel
in Solaranlage1811/snapshot. Keine Zahlenbilder, kein zweiter Haushaltsabruf.
Bei erneutem Stillstand ZUERST diesen Schreibweg und die exakte aktive
Konto/Gerät/Paket/Instanz-Bindung mit dem gesicherten Stand vergleichen.
Fehlender accessToken ist kein Beweis einer fehlenden Kontoverknüpfung;
Tokenablauf ist keine Abmeldung. Widerruf/Entfernung weiter strikt beachten.
Nicht erneut Testmodus/Kontoverknüpfung blind umschalten oder den Nutzer in
eine Tipp-/Neustart-/Neuinstallationsschleife schicken. Änderungen schrittweise
gegen den bestätigten Stand prüfen. Details und Sicherungspfade stehen in
docs/ALEXA-WIDGET-AUSLIEFERUNG.txt. Live-Erfolg daraus nicht ableiten.

Beim Supporttest am 20.11. änderten sich nach Off/Development die Amazon-
Konto- UND Gerätekennungen bei identischer installierter DEV-Instanz erneut.
Eine Wiederherstellung nur mit Kennungen aus der Sicherung war deshalb falsch.
Vor jeder solchen Wiederherstellung einen FRISCHEN echten Abruf derselben
Instanz zuordnen. Alte DataStore-Zielkennungen können noch sichtbar zustellen,
belegen aber nicht die Identität der aktuellen automatischen Abrufe.
Nur den ausdrücklich beauftragten eigenen Teststand unter strengen Instanz-,
Haushalts-, Generations- und Widerrufsprüfungen wiederherstellen; keine allgemeine
automatische Reaktivierung oder beliebige Haushaltszuordnung einbauen.
Auch RefreshIntent / NavigateHome und alte Vollbild-Refresh-Ereignisse müssen
den Werte-Renderer verwenden. Alter Button/fehlender Footer oder Aufblinken
allein sind kein Beweis für tatsächliche Bildabrufe.

# Solaranlage: bestaetigter Gesamtstand vom 20.11.2026

Nutzer bestaetigte nach Live-Promotion21:49 Berlin: Alle Sachen funktionieren.
Referenz ist Hosted-Commit00eaa8d9ea0644cf4317b358eda765fc4e1b6270,
Version1.1.0 (Build1811), Development und Live; separate DEV-Kachel erhalten.
Live-Tipp und Sprachstart oeffnen Store-Werte-Vollbild OHNE DEV-Zusatz.
DEV-Tipp oeffnet DEV-Werte-Vollbild MIT DEV-Zusatz. Beide ohne Zahlenbilder.

Vor JEDER Aenderung diese Trennung gegen den Referenzstand pruefen:
- Darstellungsprofil vom angeforderten Paket/URI/Token waehlen. Die vom
  gebundenen Datenleser bestaetigte Datenautoritaet ist KEIN Darstellungsprofil.
  Insbesondere NICHT cfg=resolved setzen: Das machte Live zu DEV-Vollbild.
- Tokenlose Store-Vollbildstarts und -Timer nutzen den streng geprueften
  bestehenden Konto/Geraet-Leser. Keine widerrufene Bindung reaktivieren.
- DEV1811 behaelt refresh der exakten Instanz und gemeinsames PUT_OBJECT
  fuer dieselbe Messung plus Antwort. Keine zweite Haushaltsabfrage.
- Echter Sprach-Launch/RefreshIntent/NavigateHome geht VOR historischen
  Handlern in den Werte-Renderer. Widget-URIs nicht in Voice umschreiben.
- Live/DEV werden im SELBEN Hosted-Code bereitgestellt. Ein master-Deploy
  betrifft DEV, explizite Promote-to-live betrifft Live; prod-Ref/Build allein
  sind kein Laufzeit-/Geraetenachweis. Nicht Testmodus oder Konten umschalten.
- Vor Rollback beruecksichtigen: Rueckbau205f4e9 brachte auch den falschen
  Live->DEV-Renderer zurueck. Nur fachlich abgegrenzte Ruecknahmen vornehmen.
- Regressionen getrennt pruefen: DEV-Tipp/Refresh, Store-Tipp/Timer und
  Sprachstart; Footer/Token sowie Bildfreiheit kontrollieren. Unregistrierte
  synthetische Instanz muss abgewiesen werden, das ist kein Kontoverlust.

119 lokale Tests plus drei bereitgestellte Development-Endpunktpruefungen
bestanden; anschliessend Nutzer-Gesamtabnahme am Echo. Das ist eine Abnahme
an diesem Haushalt, keine allgemeine Amazon-Ursachen- oder Mehrhaushaltsaussage.
Ruecksprung und Sicherungsnachweis: docs/ALEXA-BESTAETIGTER-STAND-1811.md.

GitHub-Aktualisierungen fuer diesen Stand ausschliesslich im bestehenden Werte-Pull-Request #22 (codex/dev-text-values-1611-7). Kein direkter Push nach main und keine weiteren Issue-Aenderungen ohne ausdruecklichen Auftrag.
