# Bestätigter Referenzstand · 1.1.0 (Build 1811)

Am 20.11.2026 bestätigte der Nutzer am eigenen Echo: Alle Funktionen laufen. Live und DEV bleiben getrennt; kleine Kachel und Vollbild zeigen direkte Werte. Der Sprachstart öffnet die Store-Werteansicht ohne DEV-Zusatz.

Referenz: Hosted-Commit `00eaa8d9ea0644cf4317b358eda765fc4e1b6270`, Live-Promotion 21:49 Uhr (Europe/Berlin). DEV-Paket `Solaranlage1811`; bestehendes Store-Paket `SolarAccountImageBuild1211`. Keine neue Paketkennung oder Versionsnummer.

## Regeln für weitere Änderungen

- Angefordertes Darstellungsprofil und verifizierte Datenautorität getrennt halten. `cfg=resolved` machte den Store-Aufruf fälschlich zur DEV-Ansicht.
- DEV behält den instanzgebundenen Refresh und einen gemeinsamen DataStore-Schreibauftrag für dieselbe Messung samt Originalzeitstempel. Keine zusätzliche Haushaltsabfrage.
- Store-Start und Vollbildtimer verwenden den bestehenden, streng geprüften Konto-/Geräteleser. Widerrufene Bindungen bleiben gesperrt.
- Sprachstart, RefreshIntent und NavigateHome gehen vor historischen Handlern zum Werte-Renderer. Widget-URIs behalten ihre Berechtigungsprüfung.
- Fehlender accessToken bedeutet nicht Abmeldung. Testmodus und Kontoverknüpfung nicht als Reparaturversuch umschalten.
- Development und Live teilen das Hosted-Repository: master stellt Development bereit; erst die ausdrückliche Live-Promotion aktualisiert Live. Git-Refs und Builds ersetzen keinen Echo-Nachweis.
- Änderungen und Rücknahmen getrennt für DEV-Tipp/Refresh, Store-Tipp/Timer und Sprache prüfen. Ein unregistriertes synthetisches Gerät muss abgewiesen werden.

## Sicherung und Wiederherstellung

Lokal liegt der vollständige Rücksprungstand unter `Sicherungen/Solaranlage-1811-bestaetigt-2026-11-20/`: Quellen, private laufende Konfiguration, Git-Bundles, Widgetquellen, Tests und Nachweise mit SHA-256-Inventar. Private Dateien bleiben ausschließlich lokal.

Vor einem Rücksprung aktuellen Stand erneut sichern und Unterschiede prüfen. Die Originalkonfiguration nicht durch eine öffentliche Beispielvorlage ersetzen. Einen einzelnen Router gezielt zurücknehmen; ein pauschaler Rollback kann behobene Store-/DEV-Zuordnungen wieder einführen. Kein automatisches Deployment aus GitHub.

119 lokale Tests, drei getrennte bereitgestellte Development-Endpunkttests und danach Nutzerbestätigung am Echo. Keine Aussage über andere Haushalte oder die Ursache des Amazon-Supportfalls. Bilddienste bleiben bis zur belegten Ablösung aktiv.
