# Solaranlage Echo Werte · Build 1811

Bestätigter Quellstand vom 20.11.2026: Live und separate DEV funktionieren am eigenen Echo. Kleine Kachel und Vollbild nutzen direkte Werte. Live-Tipp und Sprache öffnen Store ohne DEV, DEV-Tipp öffnet DEV.

`skill/` enthält den Hosted-Code zu `00eaa8d`; `worker.mjs` den laufenden Werte-Worker. Historische Bildfunktionen sind als Quellhistorie erhalten; der aktive Vollbild-Ausgabepfad verwendet Werte. Die Beispiele enthalten keine laufenden Zugangsdaten. `support_trace.py` ist ohne private Diagnosekonfiguration inaktiv.

`widget-template/` enthält das bestehende Store-Paket `SolarAccountImageBuild1211` mit `SolarAccountImagesV3/snapshot`; `dev-widget/` das separate DEV-Paket. Bestehende Kontoverknüpfungen und geprüfte Haushaltsbindungen bleiben erhalten. Keine allgemeine automatische Reaktivierung.

Prüfen: `python -m unittest discover -s . -p "test_*.py"` und `node --test worker.test.mjs`. Kein automatisches Deployment aus diesem Verzeichnis.

[Projektstatus](../../docs/ALEXA-STATUS.md) · [Referenz und Rücksprung](../../docs/ALEXA-BESTAETIGTER-STAND-1811.md)
