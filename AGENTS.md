# Verbindlich: Funktionsbestand erhalten, Aenderungen vorher abstimmen

Explizite Nutzervorgabe vom 21.11.2026:
Bei jeder neuen Version bleiben alle bisher umgesetzten Funktionen und das
bestehende Verhalten erhalten. Nur den konkret beauftragten Umfang aendern.
Eine Datenumstellung, Layoutaenderung, Versionsanhebung oder Fehlerkorrektur
ist KEINE Freigabe fuer weitere funktionale oder technische Seitenaenderungen.

Insbesondere Sprachbefehle, Aufrufname, Sprachmodell, Sprachrouting,
Sprachsitzung, shouldEndSession, Fallback, Rueckfragen und Ansagen weder in
DEV noch in Live nebenbei aendern. Die Anzeige bleibt ohne unaufgeforderte
Rueckfragen/Ansagen; normale Alexa-Nutzung und bestehende ausdrueckliche
Solar-Sprachabfragen muessen erhalten bleiben.

Wenn eine nicht beauftragte Verhaltensaenderung erforderlich erscheint:
vor der Umsetzung konkret erklaeren, welche Funktion sich dadurch aendert,
warum und welche Folgen das hat; ausdrueckliche Zustimmung abwarten.
Nicht eigenmaechtig umsetzen, entfernen, ersetzen, deaktivieren oder aus
einer Versions-/Veroeffentlichungsfreigabe eine solche Zustimmung ableiten.
Bereits ausdruecklich beauftragte Korrekturen innerhalb ihres Umfangs ohne
wiederholte Freigabefragen erledigen.

Vor jeder Aenderung den gesicherten Referenzstand und die bestehenden
Funktionen abgleichen. Danach gezielt auf unbeabsichtigte Aenderungen pruefen:
kleine Kachel, Vollbild, Live-/DEV-Trennung, Sprache, automatische Updates,
Einblend-/Aufwachabruf, Navigation, Fehlerverhalten und Kontozuordnung.
Lokale Tests und erfolgreiche Bereitstellung ersetzen keine Echo-Abnahme.

Die folgenden historischen Fehlerbehebungen und technischen Empfehlungen
sind Referenzwissen, KEIN Auftrag, diese Bereiche bei spaeteren Aufgaben
erneut anzufassen. Ohne konkreten Auftrag keinen vorsorglichen Umbau und
keinen automatischen Rueckbau vornehmen.

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

Sprachfreigabe beachten: Der bestaetigte Build1811 hatte spaeter eine gemeldete
Sprachsitzungsregression. Bei Werte-Vollbildantworten shouldEndSession:true
setzen, keinen reprompt und kein Finish; auch Fehler/Fallback duerfen die
Sprachsitzung nicht offenhalten. Historische v1.0.5-Korrektur18116ec als Referenz.
Neuer Fix21.11.2026 lokal129Tests, Bereitstellung/Geraetenachweis separat pruefen.

Sprachfix229b549 am21.11.2026 in Development10:15 und Live10:18 bereitgestellt.
129Tests und drei Development-Antworten bestaetigt. Echo-Sprachfreigabe und
Minutentakt nach diesem Fix noch NICHT bestaetigt; nicht vom Backend ableiten.

Store-Update1.1.0 (Build2311) am21.11.2026 eingereicht, Amazon-StatusCERTIFICATION.
Hosted-Developmentf9c477c enthaelt Sprachfix229b549 plus Store-Versionszeile2311.
Store-PaketkennungSolarAccountImageBuild1211 bleibt gleich, technische Version1.1.1.
DEV-Paket/Anzeige1811 unveraendert, kein Testmodus-/Kontowechsel. Noch keine
Freigabe oder Echo-Abnahme des Sprachfixes behaupten. Details lokal unter
.private/solar-v3/store-build2311-20261121/.

21.11.2026, nachfolgender DEV-Vollbild-Refresh-Fix (noch KEINE Echo-Abnahme):
Nutzer genehmigte ausdruecklich die Umstellung der Vollbildaktualisierung auf
den Datenspeicher, die Ruecknahme der laufenden Zertifizierung und Build2111
fuer DEV UND Store. Amazon bestaetigte die Ruecknahme; 2311 ist damit nicht
mehr in Zertifizierung. Neue Einreichung erst nach dem vereinbarten Echo-Test.
DEV-Code wurde um12:27 Berlin bereitgestellt; Paketimport mit den Anzeigen
Build2111 ist SUCCEEDED. Technische Paketkennungen bleiben Solaranlage1811
und SolarAccountImageBuild1211; der Anzeigen-Build ist KEINE Paketkennung.
Nur DEV1811 nutzt den neuen Vollbild-Datenspeicher; Live wurde nicht promoted.
Sprachabschluss shouldEndSession:true bleibt unveraendert. Worker01369555
enthaelt die DEV-Erweiterung, FULLSCREEN_DATASTORE_ENABLED=true und einen
Minuten-Cron. Dieser ist ein zusaetzlicher Worker-Aufruf pro Minute; die
vorhandenen Inline-Abrufe der kleinen Kachel bleiben erhalten. Keine Bilder.
141 lokale Python- und48 Worker-Tests bestanden, einschliesslich materialisiertem
Layout-/Textvergleich und exaktem Zahlenformat. Dies beweist NICHT das Echo.
Aktueller Befund: Testmodus ist Off; DEV-Bindungen sind inaktiv. Erste echte
Cron-Runde12:33 Berlin: enabled=true,accepted=0,households=0. Nicht als
erfolgreiche Geraetezustellung ausgeben und keine alten Bindungen reaktivieren.
Freigabe fuer Development-Wiedereinschalten wurde angefragt; vor einer solchen
Aenderung den neuesten Nutzerentscheid beachten und danach FRISCHEN Aufruf
zuordnen. Quellen, Originale, Freigaben und Status:
.private/solar-v3/fullscreen-datastore-fix-20261121/STATE.json.

21.11.2026: Nutzer gab mit "Mache mal" und "weiter" das Wiedereinschalten
von Development frei. Testmodus danach in Amazon-Konsole auf Development
gestellt und sichtbarer Aktivstatus gesichert (testmode-development.png).
Keine alte Bindung reaktiviert, keine Kontoverknuepfung geaendert. Frischer
DEV-Aufruf und Echo-Abnahme weiterhin offen. Nicht erneut umschalten.

21.11.2026 17:02 Berlin: DEV-Vollbild Build2111 Scope-Fix bereitgestellt.
Frischer aktiver DEV1811-Zugang und wiederholte Cron-Schreibantworten
accepted=1,failed=0,households=1 bestaetigt. Nutzer meldete dennoch nur
Anfangswerte. Ursache im Dokument: Extension-Handler im Dokumentkontext
referenzierte komponentenlokales fsSampleTime. Jetzt liest der vorhandene
Root-Tick die lebende FullscreenSnapshot-Datenbindung direkt mit denselben
Bindungs-/Schema-/Zeit-/Vollstaendigkeitspruefungen. Kein Sitzungsumbau.
Nur fullscreen_store.py ersetzt; aktiver Vorherstand gegen Sicherung und
eingesetzter Quelltext per Kopie exakt geprueft. Amazon Last Deployed17:02.
142 lokale Tests bestanden, einschliesslich drei simulierten Datenwechseln
im generierten Ausdruck. Das ist KEIN APL-Laufzeit- oder Echo-Nachweis.
Vollbild muss einmal neu geoeffnet werden, um das neue Dokument zu laden.
Live, Worker, Konten, Testmodus, Pakete, Optik und Sprache nicht geaendert.
Echo-Abnahme und Store-Wiedereinreichung bleiben offen. Sicherung/Details:
.private/solar-v3/fullscreen-datastore-fix-20261121/STATE.json.

21.11.2026: Nutzer meldet nach DEV-Scope-Fix: Er scheint so funktionieren.
Store-Uebernahme desselben Weges ausdruecklich beauftragt. Store-Integration
mit Namespace aus gepruefter Datenautoritaet und unveraendertem angeforderten
Darstellungsprofil in Development17:37 bereitgestellt. Worker d1317e3a plus
FULLSCREEN_STORE_ENABLED=true aktiv; vorhandener Cron bedient DEV und Live
getrennt. Keine Bindungsreaktivierung/Kontenumstellung.142Python/49Worker/49Bundle
bestanden. Live-Promotion automatisch abgelehnt, Dialog abgebrochen; Live-Code
bleibt unveraendert und Store-Wiedereinreichung offen. Nicht als Live-Abnahme
ausgeben. Vollstaendiger Quellen-/Ruecksprung-/Statusnachweis:
.private/solar-v3/store-fullscreen-datastore-2111-20261121/WIEDERHERSTELLUNG.txt.

21.11.2026 17:43 Berlin: Nutzer gab nach vorheriger Freigabeablehnung explizit
Ja uebernehmen. Live-Promotion der vorbereiteten Store-Vollbildkorrektur
erfolgreich abgeschlossen; Konsole Last Updated17:43, Promote-Button wieder
freigegeben. Live nutzt nun dieselbe direkte Datenspeicherbindung im Root-Tick.
Keine weiteren Code-/Paket-/Konto-/Sprachaenderungen in diesem Schritt.
Dies ist der Bereitstellungsnachweis, keine Live-Echo-Abnahme. Paket-/Store-
Wiedereinreichung2111 wird durch Code-Promotion nicht ersetzt und bleibt offen.
Aktueller Status: .private/solar-v3/store-fullscreen-datastore-2111-20261121/STORE-STATE.json.
Historische Angaben Live unveraendert in bisherigen Sicherungen sind damit ueberholt.

21.11.2026 17:53:49 Berlin: Store-Update1.1.0(Build2111) vollstaendig
eingereicht, HTTP202. Amazon-Skilluebersicht bestaetigt Development-Status
CERTIFICATION mit exakt diesem Zeitstempel. AUTO_PUBLISHING gewaehlt:
Veroeffentlichung nach Amazon-Freigabe. Pflichtvalidierung SUCCESSFUL; nur
Instant-Update-Eignung nicht gegeben (RECOMMENDED, keine Pflichtverletzung).
Veralteter Beschreibungssatz zum Bildsatz auf letzte gueltige Werte mit
Originalzeitstempel korrigiert; sonst Manifest unveraendert. DEV bleibt
erhalten. Neue Zertifizierungs-ID noch nicht in Historie erschienen; alte
CANCELLED-/SUCCEEDED-Pruefungen nicht als aktuelle Freigabe ausgeben.
Status und private API-Belege: .private/solar-v3/store-fullscreen-datastore-2111-20261121/.
Noch nicht zertifiziert/veroeffentlicht; Echo-Nachweis separat.

# Aktuelle Referenz Build2111 vom21.11.2026
Dieser Abschnitt ist aktueller als historische Statusnotizen oben.
DEV-Scope-Fix vom Nutzer funktional bestaetigt. Gemeinsamer Vollbild-Renderer
liest FullscreenSnapshot im Root-Komponenten-Tick, niemals komponentenlokale
Variablen aus dokumentweiten Extension-Handlern lesen. Binding/Schema/Originalzeit
und komplette Felder pruefen; bei Fehler letzte gueltige Werte behalten.
Store-Datenautoritaet/Namespace bleiben vom angeforderten Footer/Token getrennt.
DEV und Store verwenden Anzeige1.1.0(Build2111), technische IDs unveraendert.
shouldEndSession:true, kein reprompt/Finish; keine Sprachsitzung fuer Timer oeffnen.
Worker hat FULLSCREEN_DATASTORE_ENABLED=true und FULLSCREEN_STORE_ENABLED=true;
vorhandener Minuten-Cron bedient DEV und Live getrennt mit bestehenden Sperren.
Kleine Kachel behaelt Inline plus gemeinsames PUT_OBJECT. Keine Bilder.
Live-Code17:43 bereitgestellt, Store-Update17:53:49 in CERTIFICATION mit
AUTO_PUBLISHING. Keine abgeschlossene Store-Freigabe/Live-Echo-Abnahme behaupten.
155 Tests der GitHub-Quellen und49 Worker-Tests bestanden.
Quellen und Ruecksprung: docs/ALEXA-WIEDERHERSTELLUNG-2111.md;
lokale vollstaendige private Sicherung: Sicherungen/Gesamtstand-Build2111-2026-11-21/.
Vor Ruecknahme frische genaue Konto/Geraet/Paket/Instanz/Generation pruefen,
Widerrufe nicht zuruecksetzen, keinen Testmoduswechsel als Reparaturversuch.
Nur bestehenden PR22 aktualisieren; kein main-Push/kein Merge in diesem Auftrag.

22.11.2026: Beauftragter Folgestand, NOCH NICHT bereitgestellt/eingereicht.
Kleine Store-Kachel: neutraler Verbindungshinweis statt leerer Standzeile,
Anfrageabstaende bei Fehler/fehlender Antwort 1/2/4/8/max15 Minuten.
Erfolgreiche Antwort oder neuer Snapshot stellt60Sekunden wieder her.
Letzte Werte/Originalzeit unveraendert. Neue Verbindungsversion1 als streng
geprueftes Opt-in; alte Clients und DEV erhalten ihre bisherigen Antworten.
DEV-Dokument, Worker, Datenbank, Zuordnungen, Vollbild und Sprachlogik unveraendert.
Nutzer-Aufrufbeispiel fuer Alexa+ ausdruecklich: Alexa, oeffne meine Solaranlage Skill.
Nur Beispiel/Anleitung/Store-Text; NICHT den Aufrufnamen oder das Sprachmodell aendern.
Aktuelle Zertifizierung2111 nicht eigenmaechtig zurueckziehen. Fuer Ausrollen
Paket UND Backend notwendig, danach Echo-Abnahme. Keine Cloudflare-Ersparnis
vor Auslieferung behaupten. Fallquellen .private/solar-v3/connection-backoff-20261122/.


22.11.2026, freigegebener Kontostatus-Folgestand fuer Store Build2211:
Nutzer genehmigte gezielt Handler, Worker und gespeicherten Status fuer
Abrufstopp und automatischen Wiederanlauf. connectionVersion2 ist nur fuer
SolarAccountImageBuild1211 vorgesehen; CONNECTION_STATUS_ENABLED bleibt ohne
explizite Aktivierung aus. Neue Tabellen in connection-schema.sql zuerst anwenden.
Nur ein explizites SkillDisabled-Ereignis bestaetigt hier unlinked. Fehlender Token,
401, fehlende Registrierung, Grant-Ablauf und nie beobachtete Verknuepfung bleiben
UNKNOWN; solche Kacheln werden NICHT dauerhaft gestoppt. Keine Kontoverluste erfinden.
Ein gestoppter Client beobachtet einen exakten Konto/Geraet/Paket/Instanz-Steuerschluessel.
Ein frisches authentifiziertes SkillAccountLinked-Ereignis sendet nur einen Weckhinweis.
Erst ein neuer echter Kachelabruf mit aktueller Link-Ereignisautoritaet, gueltigem
Haushaltsgrant und unveraenderter Generation darf neu registrieren. Widerrufe bleiben
historisch erhalten; explizit entfernte Instanzen bleiben gesperrt. Keine blinde
Wiederaktivierung alter Bindungen. Steuerobjekte enthalten keine Messwerte/Token.
Zustellfehler bleiben in einer begrenzten Warteschlange fuer den bestehenden Cron;
kein weiterer Cron/Worker. Keine dauerhafte Statusabfrage bei bestaetigtem Stopp.
Bei komplettem Neuladen ist eine initiale Statuspruefung weiterhin erforderlich.
Antworten setzen nur literale Steuerdaten. Komponentenlokale Revisions-/Pausepruefung
IM ROOT-TICK, nicht in ExecuteCommands-/dokumentweiten Handler-Ausdruecken!
Sprache, DEV-Paket, Vollbild, gesunde60s/Einblendabrufe und Messwertformat bleiben.
Dieser Folgestand ist lokal umgesetzt/getestet, NICHT ausgerollt oder Echo-abgenommen.
Vorherige Development-Bereitstellung2211 enthaelt erst das alte v1-Backoff-Protokoll;
Live bleibt2111. Zertifizierung2111 wurde auf Nutzerauftrag zurueckgezogen (HTTP204);
2211 wurde noch nicht neu eingereicht. Keine aktuelle Zertifizierung behaupten.
Importfalle: Paketversion liegt unter manifest.version. Ein im vollstaendigen
Skill-Paket fehlendes InteractionModel wird bei Amazon GELOESCHT, nicht bewahrt.
Originalmodell immer mitliefern und nach Import bytegleich pruefen; bei2211 bereits
zwischenzeitlich geloeschtes Development-Modell wurde exakt wiederhergestellt.
Quellen/Tests/Ruecksprung: .private/solar-v3/connection-backoff-20261122/account-link-stop/.
