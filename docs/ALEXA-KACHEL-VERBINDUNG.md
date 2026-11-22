# Store-Kachel: Verbindungshinweis und begrenzte Wiederholungen

Store1.1.0(Build2211) wurde am22.11.2026 eingereicht und ist in Prüfung. Handler und Worker sind bereitgestellt; neue Store-Dokumente werden erst nach Amazon-Freigabe verteilt. Kein Testmodus-/Kontowechsel und keine manuelle Registrierungsreaktivierung.

- Voraussetzung ist eine eigene Home-Assistant-Installation mit der Integration und Kontoverknüpfung. Die Aktivierung allein liefert keine Anlagendaten.
- Ohne Messwerte nutzt die vorhandene Standzeile den neutralen Hinweis „Verbindung prüfen: Alexa-App“. Eine fehlende Kontoverknüpfung wird aus401 nicht behauptet.
- Die Kachel plant bereits vor dem Senden den nächsten Versuch:1,2,4,8,maximal15Minuten Abstand. So wirkt die Begrenzung auch, wenn überhaupt keine Antwort zurückkommt. Wiederholtes Einblenden umgeht eine laufende Fehlerfrist nicht. Ein manueller Tipp öffnet weiterhin unverändert das Vollbild.
- Erfolgreiche Antwort oder ein neuer gültiger Datenspeicher-Snapshot stellt den normalen60-Sekunden-Takt wieder her. Bei gesunder Verbindung bleibt der Einblend-/Aufwachabruf erhalten. Alte Werte und Originalzeit bleiben bei Fehlern stehen.
- Diese Begrenzung gilt pro geladener Kachelinstanz. Ein vollständiger Neuaufbau der Kachel beginnt mit einem sofortigen Abruf; es wurde kein persistenter Datenspeicher für den Retry-Zustand eingeführt.
- Der neue Store-Client verwendet connectionVersion2; vorherige Protokolle bleiben kompatibel. Paket und Backend gehören zusammen. DEV und Vollbild bleiben unverändert. Alte installierte Store-Dokumente sparen dadurch noch keine Anfragen.
- Bei dauerhaft fehlerhafter, kontinuierlich geladener Instanz sinkt der Maximalrhythmus auf4Versuche/Stunde statt60. Keine Aussage über die Zahl betroffener Nutzer oder tatsächliche Gesamtersparnis.

Zusätzlicher Alexa+-Hinweis (bestehender Sprachaufruf und Aufrufbeispiel bleiben): **„Alexa, öffne meine Solaranlage Skill.“** Dies ändert weder den eigentlichen Aufrufnamen noch das Sprachmodell.

Amazon-Zertifizierung und anschließende Veröffentlichung stehen aus. Keine weitere Paketkennung/Versionsnummer vergeben. Lokale Ausdruckstests und Bereitstellung sind kein Echo-Nachweis.

## Bestätigter Abrufstopp und automatischer Wiederanlauf

Freigegebene Erweiterung für Build2211; Backend bereitgestellt, Store-Paket in Zertifizierung.

- Nur eine explizit bestätigte Trennung (`SkillDisabled`) stoppt die automatischen Minuten- und Einblendabrufe der geladenen Store-Kachel. Der Hinweis lautet „Bitte Konto in der Alexa-App verknüpfen“. Ein fehlender Token,401,fehlende Registrierung oder abgelaufener Grant beweist keine Trennung. Für nie eindeutig beobachtete Konten bleibt der Status unbekannt und der begrenzte Fehler-Backoff erhalten.
- Die Kachel beobachtet lokal einen Steuerobjektschlüssel, der exakt an Konto,Gerät,Paket und Instanz gebunden ist. Das ist kein Cloudflare-Polling. Nach frischer erfolgreicher Kontoverknüpfung wird dieses Objekt aktualisiert. Der Hinweis allein berechtigt zu keinen Haushaltswerten.
- Erst ein frischer echter Kachelabruf darf mithilfe des aktuellen verifizierten Link-Ereignisses und weiterhin gültiger Grants/Generation neu registrieren. Alte Widerrufe werden nicht gelöscht; entfernte Instanzen bleiben ausgeschlossen. Andere Konten/Geräte/DEV bleiben getrennt.
- Verlorene Zustellaufträge werden über eine begrenzte,fair sortierte Warteschlange beim bestehenden Cron erneut versucht. Es gibt keinen weiteren Worker oder Zeitplan. Normale Minutenabrufe schreiben den Beobachterstatus nicht jedes Mal neu.
- Alte Messwerte behalten ihren Originalzeitstempel. Eine bloß eintreffende Messung hebt einen bestätigten Stopp nicht auf. Nach dem Aufwecksignal wird zuerst frisch geprüft; danach gilt wieder der60-Sekunden-Takt. Bei komplettem Neuladen der Kachel erfolgt eine initiale Statusprüfung, weil der lokale Pausenzustand dann neu aufgebaut werden muss.
- Layout bei gesunder Verbindung,Sprache,Vollbild,DEV und Paketkennungen bleiben erhalten. Der zusätzliche Hinweis nutzt die vorhandene Standzeile.

Auslieferung: zuerst `cloudflare/echo-values/connection-schema.sql` additiv anwenden,dann Worker inklusive `account_connection.mjs` bereitstellen. `CONNECTION_STATUS_ENABLED=true` aktiviert ausschließlich das Store-Protokoll2. Dazu gehören Handler und Store-Dokument aus demselben Stand. Keine Datenzuordnungen migrieren oder reaktivieren. Vor Rücknahme zuerst das Flag deaktivieren; Tabellen nicht aus einer alten Sicherung über aktuelle Kontozugänge zurückspielen.

Der vorherige Satz „Worker und Datenbank unverändert“ bezieht sich auf die erste Backoff-Fassung; die oben beschriebene Erweiterung wurde danach ausdrücklich genehmigt. Lokale Tests sind kein Echo-Nachweis. Beim späteren Gerätetest müssen bestätigte Trennung,neue Verknüpfung und drei normale Folgerunden separat beobachtet werden; den funktionierenden DEV-Zugang dafür nicht blind umschalten.


## Bereitstellungsstand22.11.

Worker (`ef69b6a5`), additive Tabellen und Aktivierungsflag sind aktiv. Handler15:09 Berlin in Development und15:23 nach Live übernommen. Vollständiges Store-Paket2211 um15:24:25.448 zur Prüfung mit automatischer Veröffentlichung eingereicht (HTTP202, CERTIFICATION). Amazon-Pflichtvalidierung erfolgreich. Nach Einreichung sind DEV-Paket,Sprachmodell und Store-Dokument bytegleich bestätigt. Kein Testmodus- oder Kontowechsel. Veröffentlichung und Echo-Abnahme stehen aus; bisherige Store-Dokumente erhalten den neuen Clientweg erst durch das veröffentlichte Update.


## Vorbereiteter Ruhemodus nach wiederholter fehlender Registrierung

Diese nachträglich beauftragte Erweiterung ist noch nicht in der laufenden2211-Prüfung und noch nicht ausgerollt.

- Protokoll3 zählt nur vom Server bestätigte erfolglose Registrierungen der exakten Instanz. Nach sechs Versuchen mit den bisherigen Abständen (sofort,1,3,7,15,30Minuten) pausiert die leere Kachel und zeigt „Keine Verbindung. Bitte Skill öffnen.“ Das erklärt den Zustand als Verbindungsproblem, nicht als angeblich fehlende Kontoverknüpfung.
- Der Zähler bleibt über einen vollständigen Neuaufbau der Kachel erhalten. Beim Neuaufbau bleibt eine initiale Statusprüfung erforderlich. Bereits registrierte Kacheln und Kacheln mit gültigen vorhandenen Werten werden nicht in diese zusätzliche Ruhepause versetzt. Vorübergehende Messdatenfehler verbrauchen kein Registrierungsbudget.
- Eine erfolgreiche Verknüpfung weckt über den bestehenden Steuerweg. Ein erfolgreicher authentifizierter Store-Vollbildstart kann zusätzlich ausschließlich fehlgeschlagene Protokoll3-Instanzen desselben Kontos und Geräts wecken. Automatische Vollbildtimer tun das nicht. Weckfehler unterbrechen das Vollbild nicht; der bestehende Cron versucht die Zustellung erneut.
- Eine Wecknachricht gibt keine Daten frei. Erst ein frischer Kachelabruf prüft Quellinstanz,aktive Bindung,Haushalt,Generation,aktuelle Grants und Widerrufe erneut. Entfernte Ziel-/Quellinstanzen,anderes Konto/anderes Gerät,gesperrter Haushalt und geänderte Zugangsgeneration bleiben ausgeschlossen. Eine explizite Trennung wird durch einen DEV-gestützten Vollbildstart nicht aufgehoben.
- Bei vollständig ausbleibenden Antworten ohne bestätigten instanzgenauen Weckkanal bleibt der begrenzte Backoff erhalten. So wird keine Kachel dauerhaft ohne erreichbaren Wiederanlauf stillgelegt.
- Opt-in: `connectionVersion:3` plus `CONNECTION_RETRY_PAUSE_ENABLED=true`; vorher additiv `retry-schema.sql` anwenden. Bestehende Protokolle1/2 bleiben erhalten. Gesunde Anzeige,Sprache,Vollbild,DEV-Paket und Paketkennungen bleiben unverändert. Die lokale Anzeigeversion bleibt vorerst2211; kein weiterer Versionswechsel beauftragt.

Lokal:215 Python-/73 Worker-Tests, bereitstellbares Bündel73 Tests bestanden. Geräteprüfung und Auslieferung noch offen.
