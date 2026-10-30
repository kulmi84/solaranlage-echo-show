# Solaranlage: kontogebundenes Bildwidget

## Bestätigter Stand

Version **2.0.0** zeigt nach einmaliger Kontoverknüpfung echte Werte und automatische Minutenaktualisierungen auf dem Echo. Das allgemeine Paket enthält keinen fest eingebauten persönlichen Bildzugang. Die zusätzliche manuelle Widget-Einrichtung entfällt für diesen getesteten Weg.

Der Erfolg gilt für eine **neue separate Skill-Variante** auf Basis des funktionierenden Data-Store-Labors. Er ist keine Reparatur des bisherigen normalen Skills, keine allgemeine Store-Freigabe und kein abgeschlossener HACS-Rollout.

Version **2.0.1** korrigiert das Nachladen beim Einblenden: `onDisplayStateChange` gehört auf Dokumentebene und markiert den nächsten Bild-Tick sofort als fällig. Das Minutenintervall bleibt erhalten. Build und Installationsauftrag sind bestätigt; tatsächliche Geräteankunft und Wiederaufnahme-Verhalten sind noch offen.

## Ablauf des neuen Kandidaten

1. Der verknüpfte Kontozugang erzeugt über denselben Bildzugangsdienst wie Vollbild eine individuelle Bildfreigabe.
2. Die Bildadressen werden zur Laufzeit im Data Store bereitgestellt und vom Widget gelesen. Sie sind nicht Bestandteil des gemeinsamen Pakets.
3. Drei transparente Wertebilder und die Stand-Zeile werden im Minutenabstand nachgeladen, solange Alexa das Widget ausführt.
4. Der vollständige bisherige Bildsatz soll sichtbar bleiben, bis alle vier Ersatzbilder geladen sind; Fehler und Timeout lösen Wiederholungen aus.
5. Die zeitlich begrenzte Bildfreigabe soll automatisch vor Ablauf erneuert werden, ohne weitere Kontoverknüpfung.

Punkte 4 und 5 sind implementiert, ihre vollständige reale Geräteabnahme steht noch aus. Der frühere INLINE-Antwortweg und frühere Simulatorerfolge sind keine Abnahme des neuen Pakets.

## Nummerierte offene Punkte

1. [ ] **Nachladen beim Einblenden:** Version 2.0.1 muss beim erneuten Anzeigen direkt neue Bilder anfordern. Der korrigierte Handler liegt jetzt auf Dokumentebene; tatsächlicher Echo-Test noch offen.
2. [ ] **Automatische Zugangserneuerung:** Nach tatsächlichem Ablauf des Bildzugangs ohne erneute Kontoverknüpfung weiterladen. Erneuerung ist implementiert, der reale Ablauf-/Langzeittest fehlt.
3. [ ] **Ladefehler und vollständiger Bildpuffer:** Den letzten vollständigen Bildsatz einschließlich Stand bei Fehler, Timeout und verspäteter Antwort behalten, bis alle vier Ersatzbilder geladen sind.
4. [ ] **Vollbild öffnen:** Antippen des neuen Kontowidgets öffnet die passende Vollbildansicht; bestehende Vollbild-/Sprachfunktion bleibt intakt.
5. [ ] **Frische Einrichtung mit anderem Konto:** Eine Kontoverknüpfung für beide Ansichten, ausschließlich die eigenen Daten; reale Mehrkonto-Abnahme noch offen.
6. [ ] **Einrichtung ohne Einladung:** Öffentlichen Einrichtungsweg vereinfachen und vollständig prüfen. Das erfolgreiche Widget allein entfernt die bisherige Einladungspflicht nicht.
7. [ ] **Codeübernahme und Veröffentlichung:** Tatsächlichen allgemeinen Kandidaten ohne private Konfigurationen in GitHub übernehmen, Tests/Dokumentation/Paketstand synchronisieren; danach PRs/Issues abschließen, passende Version bei Amazon zertifizieren/veröffentlichen und GitHub/HACS aktualisieren. HACS installiert kein Echo-Widget.

## Quellcode und Veröffentlichung

Dieser Draft-PR enthält noch den früheren **1.1.3-Code**, nicht den tatsächlich getesteten 2.0.x-Kandidaten. Vor Merge müssen allgemeiner Code, Tests, Dokumentation und Amazon-Paketstand synchronisiert werden. Keine private Gesamt-Lambda, Konfiguration, Zugangsdaten oder persönliche Bildadressen übernehmen.

Die privaten funktionierenden Rücksprungstände bleiben getrennt. Bestehende Releases bleiben erhalten. Ein HACS-Update installiert kein Echo-Widget; die zentrale Amazon-Auslieferung wird separat geprüft und veröffentlicht.

Zentrale aktuelle Abnahmeübersicht: [Issue #10](https://github.com/kulmi84/solaranlage-echo-show/issues/10#issuecomment-6532539414).
Separater wiederverwendbarer Data-Store-Einwert-Test: [PR #11](https://github.com/kulmi84/solaranlage-echo-show/pull/11).
