# Projektstatus · 01.11.2026

- **HACS 1.0.11 veröffentlicht.** Neueinrichtung ohne Einladung und bestehende Einrichtung geprüft; Konten und Sensoren bleiben erhalten.
- **Bildwidget 2.0.1 am Echo bestätigt:** sofortiges Nachladen, Zugangserneuerung, Bildpuffer samt Zeitstand, Vollbild und weiße Fußzeile.
- **Haushaltstest bestanden:** neuer Testhaushalt zeigte 123 W in Widget und Vollbild. Nach Rückverknüpfung und einmaligem Antippen zeigen beide die echten Werte des bisherigen Haushalts (207 W, 2,48 kW, 17 %). Keine Widget-Neuinstallation nötig. Nach einem Haushaltswechsel ist einmaliges Antippen vorgesehen.
- **Vollbild-Sofortabruf bereitgestellt:** neue Bildadressen bei jedem Öffnen, sofortiger Abruf beim Zurückkehren; danach alle 60 Sekunden. Am Gerät nach Antippen übereinstimmende Werte bestätigt.
- Allgemeine, zugangsfreie Widgetquellen und heutige Korrekturen werden für die Veröffentlichung zusammengeführt. Keine privaten Recovery-Zugänge im Paket. Die öffentliche Amazon-Freigabe steht weiterhin aus.

## Skills

| Skill | Stand |
|---|---|
| Data Store Labor | Funktionierender Skill mit SolarAccountImage 2.0.1; öffentliche Namen und Einreichung werden vorbereitet. |
| Solaranlage | Bisheriger öffentlicher Skill bleibt für bestehende Nutzer erhalten. |
| Mein Zuhause | Unverändert. |

## Offene Punkte

7. **Zurückgestellt:** externe HACS-Updates und vollständige Migration aller HA-/Alexa-/Bildzugriffe nachweisen, danach zwei Weiterleitungen entfernen. Aktuelle Uploads allein beweisen die verwendete Adresse nicht.
8. Allgemeine Runtime zusammenführen, Amazon-Angaben und Widget-Metadaten bereinigen, validieren, zertifizieren und veröffentlichen. Erst den tatsächlichen Live-Status als Veröffentlichung melden.

Cloudflare: sechs Worker und zwei Datenbanken bleiben erhalten. Die zwei alten Adressen bleiben vorerst als Weiterleitungen aktiv.

[Checkliste #10](https://github.com/kulmi84/solaranlage-echo-show/issues/10) · [Widgetquellen](../alexa/widget/README.md)
