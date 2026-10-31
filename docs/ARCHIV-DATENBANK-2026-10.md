# Relay-Datenbank und Sicherung

## Betriebsstand vom 19. Oktober 2026

| Bestandteil | Aktueller Name |
| --- | --- |
| Cloudflare D1 | `solaranlage` (EU-Jurisdiktion) |
| Worker-Binding im Code | `DB` |
| Worker | `solaranlage-public-beta` |
| OAuth-Client-ID | `solaranlage-public-beta` |

Der bisherige Name in Worker-URL und OAuth-Konfiguration ist eine technische
Kennung, keine Versionsangabe. Diese Kennungen bleiben bestehen, damit bestehende
Home-Assistant-Installationen und Alexa-Kontoverknüpfungen weiter funktionieren.
Nur das D1-Binding wurde auf die neue Datenbank umgestellt. Die Beispielkonfiguration
unter `cloudflare/public-beta/wrangler.example.jsonc` verwendet bereits `solaranlage`;
für eine eigene Installation die eigene Datenbank-ID einsetzen.

## Abgeschlossener Datenumzug

D1 wurde nicht direkt umbenannt. Stattdessen wurde eine neue Datenbank angelegt.
Während des Umzugs waren schreibende Relay-Anfragen kurz pausiert. Alle sechs
Tabellen wurden übertragen: `households`, `invites`, `pair_codes`, `oauth_codes`,
`access_tokens` und `refresh_tokens`.

Vor der Umschaltung wurden Schema, Spalten und sämtliche Zeileninhalte beider
Stände verglichen und die Fremdschlüssel geprüft. Nach der Umschaltung wurden
neue echte HA-Uploads sowie OAuth/PKCE und authentifizierte Messwertabrufe geprüft.
Bestehende Nutzer benötigen keine neue Einladung oder Kontoverknüpfung.

Die alte Datenbank `solaranlage-public-beta` wurde anschließend gelöscht.
Der unabhängige ältere Einzelanlagen-Dienst ist von diesem Umzug nicht betroffen.

## Sicherung und Wiederherstellung

Eine vollständige SQL-Sicherung des alten Stands und das private Prüfprotokoll
liegen beim Betreiber lokal. SQL-Dumps, private Wrangler-Konfigurationen und
Schlüssel gehören nicht in dieses öffentliche Repository.

Die alte D1-ID ist nach der Löschung ungültig. Eine frühere Worker-Version oder
eine alte Konfigurationsdatei darf deshalb nicht einfach als Rollback aktiviert
werden: Sie würde auf eine gelöschte Datenbank zeigen.

Für eine Wiederherstellung muss eine neue D1-Datenbank angelegt, die lokale
SQL-Sicherung importiert und deren neue ID im Binding `DB` eingetragen werden.
Vor dem Umschalten müssen außerdem alle seit der Sicherung neu entstandenen
Messwerte und OAuth-Tokens berücksichtigt werden. Dafür Schreibzugriffe kurz
pausieren, aktuellen Stand sichern und die Daten erneut vergleichen.

## Neue eigene Installation

Eine eigene Datenbank `solaranlage` anlegen, die ausgegebene ID in einer privaten
Wrangler-Konfiguration einsetzen und `cloudflare/public-beta/schema.sql` nur für
die neue leere Datenbank anwenden. Bestehende Datenbanken nicht zurücksetzen.
Die übrigen Schritte stehen in der [HACS-Anleitung](HACS.md#betreiber-gemeinsames-relay).
