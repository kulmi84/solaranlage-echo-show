# Projektstatus · 01.11.2026

- **HACS 1.0.11 veröffentlicht.** Neueinrichtung ohne Einladung und bestehende Einrichtung geprüft; Konten und Sensoren bleiben erhalten.
- **Bildwidget 2.0.1 am Echo bestätigt:** sofortiges Nachladen, Zugangserneuerung, Bildpuffer samt Zeitstand, Vollbild und weiße Fußzeile.
- **Haushaltstest bestanden:** Testhaushalt mit 123 W in Widget und Vollbild; nach Rückverknüpfung und einmaligem Antippen wieder echte Werte. Keine Neuinstallation nötig.
- **Vollbild-Sofortabruf bestätigt:** neue Bildadressen bei jedem Öffnen, sofortiger Abruf beim Zurückkehren; danach alle 60 Sekunden.
- **Runtime über PR #19 integriert**, 93 Python-Tests bestanden. Alter PR #9 als ersetzt geschlossen. Das öffentliche Paket enthält keine privaten Recovery-Zugänge.
- **Bei Amazon eingereicht:** Build 8 erfolgreich, Validierung ohne Fehler. Einstellung „Zertifizieren und veröffentlichen“; Amazon bestätigt **In review**. Getrenntes synthetisches Demokonto für das Prüfteam hinterlegt. Noch nicht öffentlich freigegeben.

## Skills

| Skill | Stand |
|---|---|
| Solaranlage (bisher Data Store Labor) | SolarAccountImage 2.0.1; neuer öffentlicher Entwurf in Amazon-Prüfung. |
| Solaranlage (bisheriger öffentlicher Skill) | Bleibt für bestehende Nutzer erhalten. |
| Mein Zuhause | Unverändert. |

## Offene Punkte

7. **Zurückgestellt:** externe HACS-Updates und vollständige Migration aller HA-/Alexa-/Bildzugriffe nachweisen, danach zwei Weiterleitungen entfernen.
8. **Amazon-Freigabe abwarten und tatsächlichen Live-Status prüfen.** Automatische Veröffentlichung nach bestandener Zertifizierung ausgewählt.

Cloudflare: sechs Worker und zwei Datenbanken. Die zwei alten Adressen bleiben vorerst als Weiterleitungen aktiv.

[Checkliste #10](https://github.com/kulmi84/solaranlage-echo-show/issues/10) · [Widgetquellen](../alexa/widget/README.md)
