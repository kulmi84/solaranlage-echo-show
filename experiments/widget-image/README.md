> **Historischer Ansatz, nicht der aktuelle Release-Kandidat.** Der frühere Inline-Bootstrap ist abgelöst. Aktuelle kontoneutrale Quellen: [Kontobildwidget 2.0.1](../widget-account-image/README.md). [Offene Freigabe #10](https://github.com/kulmi84/solaranlage-echo-show/issues/10).

# Solaranlage: Kontobildwidget 2.0.1

Nach einmaliger Kontoverknüpfung werden individuelle Bildadressen zur Laufzeit über den Data Store bereitgestellt. Das Paket enthält keinen persönlichen Bildzugang. Der Erfolg gilt für den neuen separaten Skill, nicht als Reparatur des ursprünglichen Skills.

## Widget 2.0.1 – Abnahme

**Punkte 1–4 sind am Gerät bestätigt.** Punkte 5–7 bleiben offen; noch keine öffentliche Freigabe.

1. [x] ~~**Nachladen beim Einblenden:** Neue Werte werden direkt geladen.~~
2. [x] ~~**Zugangserneuerung:** Echter Testzugang abgelaufen; automatische Aktualisierung danach ohne Eingriff bestätigt.~~
3. [x] ~~**Ladefehler:** Alter vollständiger Bildsatz samt Stand bleibt während eines gezielten Bildfehlers sichtbar.~~
4. [x] ~~**Vollbild:** Richtige neue Vollbildansicht durch vorübergehende Testkennung bestätigt; Kennung wieder entfernt.~~
5. [ ] **Anderes Konto:** Eine Einrichtung für beide Ansichten; ausschließlich eigene Daten.
6. [ ] **Ohne Einladung:** Öffentlichen Einrichtungsweg umsetzen und prüfen.
7. [ ] **Veröffentlichung:** 2.0.1-Code übernehmen, Tests abschließen, PRs/Issues abschließen und Amazon sowie GitHub/HACS aktualisieren.

Der beschleunigte echte Ablauf-Test bestätigt die Erneuerungsfunktion; ein Langzeitbetrieb bleibt ergänzende Beobachtung. Der neue Skill ersetzt keine nachgewiesene Reparatur der alten Skill-Zuordnung.

**Codeumfang:** Dieser Draft-PR enthält weiterhin den älteren Laufzeitcode. Vor Freigabe muss der tatsächlich getestete 2.0.1-Kandidat ohne private Konfigurationen übernommen werden. Bestehende Releases bleiben erhalten; HACS installiert kein Echo-Widget.

Zentraler Status: [Issue #10](https://github.com/kulmi84/solaranlage-echo-show/issues/10).