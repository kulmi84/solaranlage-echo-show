# Store-Kachel: Verbindungshinweis und begrenzte Wiederholungen

Implementierter Folgestand vom 22.11.2026, noch nicht bereitgestellt. Build2111 wurde auf Nutzerauftrag zurückgezogen; Store2211 wird vorbereitet. Kein Testmodus-/Kontowechsel und keine Registrierung reaktiviert.

- Voraussetzung ist eine eigene Home-Assistant-Installation mit der Integration und Kontoverknüpfung. Die Aktivierung allein liefert keine Anlagendaten.
- Ohne Messwerte nutzt die vorhandene Standzeile den neutralen Hinweis „Verbindung prüfen: Alexa-App“. Eine fehlende Kontoverknüpfung wird aus401 nicht behauptet.
- Die Kachel plant bereits vor dem Senden den nächsten Versuch:1,2,4,8,maximal15Minuten Abstand. So wirkt die Begrenzung auch, wenn überhaupt keine Antwort zurückkommt. Wiederholtes Einblenden umgeht eine laufende Fehlerfrist nicht. Ein manueller Tipp öffnet weiterhin unverändert das Vollbild.
- Erfolgreiche Antwort oder ein neuer gültiger Datenspeicher-Snapshot stellt den normalen60-Sekunden-Takt wieder her. Bei gesunder Verbindung bleibt der Einblend-/Aufwachabruf erhalten. Alte Werte und Originalzeit bleiben bei Fehlern stehen.
- Diese Begrenzung gilt pro geladener Kachelinstanz. Ein vollständiger Neuaufbau der Kachel beginnt mit einem sofortigen Abruf; es wurde kein persistenter Datenspeicher für den Retry-Zustand eingeführt.
- Opt-in über connectionVersion1. Paket und Backend müssen gemeinsam ausgeliefert werden. DEV, Worker, Datenbank und Vollbild bleiben unverändert. Alte installierte Store-Dokumente sparen dadurch noch keine Anfragen.
- Bei dauerhaft fehlerhafter, kontinuierlich geladener Instanz sinkt der Maximalrhythmus auf4Versuche/Stunde statt60. Keine Aussage über die Zahl betroffener Nutzer oder tatsächliche Gesamtersparnis.

Zusätzlicher Alexa+-Hinweis (bestehender Sprachaufruf und Aufrufbeispiel bleiben): **„Alexa, öffne meine Solaranlage Skill.“** Dies ändert weder den eigentlichen Aufrufnamen noch das Sprachmodell.

Auslieferung bleibt offen: laufende Amazon-Zertifizierung nur nach ausdrücklicher Freigabe zurückziehen oder deren Abschluss abwarten; keine neue Paketkennung/Versionsnummer eigenmächtig vergeben. Lokale Ausdruckstests sind kein Echo-Nachweis.

## Bestätigter Abrufstopp und automatischer Wiederanlauf

Freigegebene Erweiterung für Build2211, lokal umgesetzt; noch nicht bereitgestellt.

- Nur eine explizit bestätigte Trennung (`SkillDisabled`) stoppt die automatischen Minuten- und Einblendabrufe der geladenen Store-Kachel. Der Hinweis lautet „Bitte Konto in der Alexa-App verknüpfen“. Ein fehlender Token,401,fehlende Registrierung oder abgelaufener Grant beweist keine Trennung. Für nie eindeutig beobachtete Konten bleibt der Status unbekannt und der begrenzte Fehler-Backoff erhalten.
- Die Kachel beobachtet lokal einen Steuerobjektschlüssel, der exakt an Konto,Gerät,Paket und Instanz gebunden ist. Das ist kein Cloudflare-Polling. Nach frischer erfolgreicher Kontoverknüpfung wird dieses Objekt aktualisiert. Der Hinweis allein berechtigt zu keinen Haushaltswerten.
- Erst ein frischer echter Kachelabruf darf mithilfe des aktuellen verifizierten Link-Ereignisses und weiterhin gültiger Grants/Generation neu registrieren. Alte Widerrufe werden nicht gelöscht; entfernte Instanzen bleiben ausgeschlossen. Andere Konten/Geräte/DEV bleiben getrennt.
- Verlorene Zustellaufträge werden über eine begrenzte,fair sortierte Warteschlange beim bestehenden Cron erneut versucht. Es gibt keinen weiteren Worker oder Zeitplan. Normale Minutenabrufe schreiben den Beobachterstatus nicht jedes Mal neu.
- Alte Messwerte behalten ihren Originalzeitstempel. Eine bloß eintreffende Messung hebt einen bestätigten Stopp nicht auf. Nach dem Aufwecksignal wird zuerst frisch geprüft; danach gilt wieder der60-Sekunden-Takt. Bei komplettem Neuladen der Kachel erfolgt eine initiale Statusprüfung, weil der lokale Pausenzustand dann neu aufgebaut werden muss.
- Layout bei gesunder Verbindung,Sprache,Vollbild,DEV und Paketkennungen bleiben erhalten. Der zusätzliche Hinweis nutzt die vorhandene Standzeile.

Auslieferung: zuerst `cloudflare/echo-values/connection-schema.sql` additiv anwenden,dann Worker inklusive `account_connection.mjs` bereitstellen. `CONNECTION_STATUS_ENABLED=true` aktiviert ausschließlich das Store-Protokoll2. Dazu gehören Handler und Store-Dokument aus demselben Stand. Keine Datenzuordnungen migrieren oder reaktivieren. Vor Rücknahme zuerst das Flag deaktivieren; Tabellen nicht aus einer alten Sicherung über aktuelle Kontozugänge zurückspielen.

Der vorherige Satz „Worker und Datenbank unverändert“ bezieht sich auf die erste Backoff-Fassung; die oben beschriebene Erweiterung wurde danach ausdrücklich genehmigt. Lokale Tests sind kein Echo-Nachweis. Beim späteren Gerätetest müssen bestätigte Trennung,neue Verknüpfung und drei normale Folgerunden separat beobachtet werden; den funktionierenden DEV-Zugang dafür nicht blind umschalten.


## Bereitstellungsstand22.11.

Worker (`ef69b6a5`), additive Tabellen und Aktivierungsflag sind aktiv. Handler15:09 Berlin und vollständiges Store-Paket2211 sind in Development bereitgestellt; Amazon-Pflichtvalidierung erfolgreich. Kein Testmodus- oder Kontowechsel. Sprachmodell und DEV-Paket wurden nach Export bytegleich geprüft. Die direkte Live-Übernahme ist durch die automatische Freigabeprüfung blockiert und wurde abgebrochen; dafür wird eine ausdrückliche aktuelle Produktionsfreigabe benötigt. Store-Einreichung und Echo-Abnahme stehen weiterhin aus. Die Funktion ist deshalb noch nicht bei bestehenden Store-Kacheln wirksam.
