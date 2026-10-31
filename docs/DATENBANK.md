# Dienste, Datenbank und Sicherung

Stand: 31.10.2026. Keine Zugangsdaten oder Sicherungsinhalte in GitHub ablegen.

| Bestandteil | Aufgabe |
|---|---|
| D1 `solaranlage` | Konten, Verknüpfungen, jeweils letzte Messwert-/Summenstände und Registrierungsschutz. |
| D1 `mein-zuhause` | Eigenständiges Projekt; unverändert. |
| `solaranlage-kontodienst` | Kontoanlage, HA-Uploads und Alexa-Kontoverknüpfung. |
| `solaranlage-bilder` | Wertebilder für Vollbild und kleines Widget. |
| `solaranlage-public-beta` | Alte Adresse, interne Weiterleitung zum Kontodienst. |
| `solaranlage-display` | Alte Adresse, interne Weiterleitung zum Bilddienst. |
| `mein-zuhause` | Separater Dienst. |
| `cloudflare-tageslimit-warnung-50-prozent` | Separater Tageslimit-Warner. |

Insgesamt **6 Worker und 2 Datenbanken**. Die beiden alten Adressen bleiben erhalten, bis alle bestehenden HA-, Alexa- und Bildverbindungen umgestellt und geprüft sind. Danach verbleiben vier Worker einschließlich Warn-Worker.

Der Kontodienst verwendet das Binding `DB`. Technische OAuth-Kennungen und vorhandene Zugangsdaten werden nicht allein wegen der Umbenennung geändert.

Vor produktiven Änderungen Quelle und Einstellungen privat sichern und einen D1-Wiederherstellungspunkt festhalten. Bei einem Fehler bevorzugt die gezielte Worker-Konfiguration zurücksetzen; eine Datenbank-Wiederherstellung kann neuere Kundenänderungen verlieren und ist kein routinemäßiger Rücksprung.

[Registrierungsschutz und Speicherung](PUBLIC-ENROLLMENT.md) · [Aktueller Projektstatus](ALEXA-STATUS.md)
