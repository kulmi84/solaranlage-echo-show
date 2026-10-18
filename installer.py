"""Local setup assistant. No dependencies, deployment, or writes to Home Assistant."""
import argparse
import getpass
import json
import math
import re
import secrets
import uuid
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent
# key, label, original entity, kind. Only these exact template references are changed.
SENSORS = [
    ('power_w', 'PV-Gesamtleistung INKLUSIVE BKW', 'sensor.pv_gesamt', 'power'),
    ('pv_dc_w', 'PV-Leistung ohne BKW', 'sensor.total_dc_power', 'power'),
    ('bkw_w', 'BKW-Leistung', 'sensor.bkw_leistung', 'power'),
    ('home_w', 'Hausverbrauch', 'sensor.stromverbrauch_haus', 'power'),
    ('grid_import_w', 'Netzbezug', 'sensor.import_power', 'power'),
    ('grid_export_w', 'Einspeisung', 'sensor.export_power', 'power'),
    ('battery_soc', 'Akkustand', 'sensor.battery_level', 'percent'),
    ('battery_charge_w', 'Akku-Ladeleistung', 'sensor.battery_charging_power', 'power'),
    ('battery_discharge_w', 'Akku-Entladeleistung', 'sensor.battery_discharging_power', 'power'),
    ('energy_pv', 'PV-Energiezaehler OHNE BKW', 'sensor.total_pv_generation', 'energy'),
    ('energy_bkw', 'BKW-Energiezaehler', 'sensor.bkw_energie', 'energy'),
    ('energy_import', 'Netzbezug-Energiezaehler', 'sensor.bitshake_verbrauch', 'energy'),
    ('energy_export', 'Einspeisung-Energiezaehler', 'sensor.bitshake_einspeisung', 'energy'),
    ('energy_charge', 'Akku-Ladeenergiezaehler', 'sensor.total_battery_charge', 'energy'),
    ('energy_discharge', 'Akku-Entladeenergiezaehler', 'sensor.total_battery_discharge', 'energy'),
]


class SetupError(ValueError):
    """Safe, user-facing validation message without credentials."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # Never forward bearer tokens to another endpoint.


def endpoint(value, relay=False):
    if not isinstance(value, str):
        raise SetupError('Adresse muss als Text angegeben werden.')
    parts = urlsplit(value)
    if (parts.scheme not in (['https'] if relay else ['http', 'https'])
            or not parts.hostname or parts.username or parts.password
            or parts.query or parts.fragment):
        raise SetupError('Adresse muss eine gueltige URL ohne Zugangsdaten, Query oder Fragment sein.')
    if relay and parts.path != '/pv':
        raise SetupError('Relay-Adresse muss mit /pv enden und HTTPS verwenden.')
    return value.rstrip('/')


def get_json(url, token):
    request = Request(url, headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/json',
                                    'User-Agent': 'Solaranlage-Setup/1.0'})
    with build_opener(NoRedirect).open(request, timeout=10) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise SetupError('Antwort zu gross.')
    return json.loads(raw)


def load_states(url, token):
    result = get_json(endpoint(url) + '/api/states', token)
    if not isinstance(result, list):
        raise SetupError('HA lieferte keine Entitaetenliste.')
    return {item['entity_id']: item for item in result if isinstance(item, dict) and
            isinstance(item.get('entity_id'), str)}


def validate_mapping(mapping):
    if set(mapping) != {key for key, *_ in SENSORS}:
        raise SetupError('Die Sensorauswahl muss alle 15 Felder enthalten.')
    for key, _, _, _ in SENSORS:
        value = mapping[key]
        if not isinstance(value, str) or (value and not re.fullmatch(r'sensor\.[a-z0-9_]+', value)):
            raise SetupError('Ungueltige Sensor-ID fuer ' + key)
    if not mapping['power_w']:
        raise SetupError('PV-Gesamtleistung ist erforderlich.')
    energy = [mapping[key] for key, _, _, kind in SENSORS if kind == 'energy' and mapping[key]]
    if len(energy) != len(set(energy)):
        raise SetupError('Energiezaehler duerfen nicht doppelt verwendet werden (Doppelzaehlung).')


def issues(mapping, states):
    validate_mapping(mapping)
    result = []
    for key, label, _, kind in SENSORS:
        entity = mapping[key]
        if not entity:
            result.append(('WARN', label + ': nicht zugeordnet; betreffende Werte fehlen.'))
            continue
        item = states.get(entity)
        if item is None:
            result.append(('FEHLER', label + ': Entitaet nicht gefunden.'))
            continue
        attrs = item.get('attributes', {})
        units = {'power': ['W', 'kW'], 'percent': ['%'], 'energy': ['Wh', 'kWh', 'MWh']}
        if attrs.get('unit_of_measurement') not in units[kind]:
            result.append(('FEHLER', label + ': Einheit muss ' + '/'.join(units[kind]) + ' sein.'))
        try:
            value = float(item['state'])
            if not math.isfinite(value) or value < 0 or (kind == 'percent' and value > 100):
                raise SetupError()
        except (ValueError, TypeError, KeyError):
            result.append(('FEHLER', label + ': kein gueltiger nichtnegativer Messwert.'))
        if kind == 'energy' and attrs.get('state_class') not in ('total', 'total_increasing'):
            result.append(('WARN', label + ': kumulierter Zaehler mit state_class total/total_increasing erwartet.'))
    return result


def render_package(mapping):
    validate_mapping(mapping)
    source = (ROOT / 'home-assistant/pv_beta.yaml').read_text(encoding='utf-8')
    source = source.replace('# Existing package: /config/integrations/pv_beta.yaml',
                            '# Generated package: use a separate HA test installation first.')
    # Single-pass substitution prevents a chosen entity matching another old ID being remapped again.
    lookup = {old: mapping[key] for key, _, old, _ in SENSORS}
    pattern = '|'.join(re.escape(old) for old in sorted(lookup, key=len, reverse=True))
    source = re.sub(pattern, lambda match: lookup[match.group()], source)
    # Empty optional statistic IDs must not be passed to recorder.get_statistics.
    source = '\n'.join(line for line in source.splitlines() if not re.fullmatch(r'\s+-\s*', line)) + '\n'
    if not any(mapping[key] for key, _, _, kind in SENSORS if kind == 'energy'):
        start = source.index('      - action: recorder.get_statistics')
        end = source.index('      - action: rest_command.pv_beta_upload', start)
        source = source[:start] + source[end:]
    return source


def blueprint():
    source = (ROOT / 'home-assistant/pv_beta.yaml').read_text(encoding='utf-8')
    automation = source.split('    triggers:', 1)[1]
    automation = 'triggers:' + '\n'.join(line[4:] if line.startswith('    ') else line
                                         for line in automation.splitlines())
    for key, _, old, _ in SENSORS:
        automation = automation.replace("'" + old + "'", key)
        automation = automation.replace('- ' + old, '- "{{ ' + key + ' }}"')
    header = ['blueprint:', '  name: Solaranlage - Messwerte fuer Echo',
              '  description: Sensoren auswaehlen. Benoetigt vorbereiteten rest_command.pv_beta_upload und secrets.yaml; siehe Schnellstart.',
              '  domain: automation', '  input:']
    for key, label, _, kind in SENSORS:
        header += ['    ' + key + ':', '      name: ' + label,
                   '      selector:', '        entity:', '          filter:', '            - domain: sensor']
    header += ['variables:']
    header += ['  ' + key + ': !input ' + key for key, *_ in SENSORS]
    return '\n'.join(header) + '\n' + automation


def generate(out, mapping, relay_url, worker_name, db_id):
    validate_mapping(mapping)
    endpoint(relay_url, relay=True)
    if not re.fullmatch(r'[a-z][a-z0-9-]{2,50}', worker_name):
        raise SetupError('Workername: 3-51 Kleinbuchstaben, Zahlen oder Bindestriche.')
    try:
        if str(uuid.UUID(db_id)) != db_id.lower():
            raise SetupError()
    except (ValueError, AttributeError):
        raise SetupError('D1-Datenbank-ID muss eine UUID sein.')
    out = Path(out)
    # Refuse to merge with, or overwrite, an existing installation directory.
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    read_token, write_token = secrets.token_hex(32), secrets.token_hex(32)
    for folder in ['home-assistant', 'alexa', 'relay']:
        (out / folder).mkdir()
    def write(path, value):
        (out / path).write_text(value, encoding='utf-8')
    write('sensoren.json', json.dumps(mapping, ensure_ascii=False, indent=2))
    write('home-assistant/pv_beta.yaml', render_package(mapping))
    history = (ROOT / 'home-assistant/pv_history.yaml').read_text(encoding='utf-8')
    lookup = {old: mapping[key] for key, _, old, _ in SENSORS}
    pattern = '|'.join(re.escape(old) for old in sorted(lookup, key=len, reverse=True))
    history = re.sub(pattern, lambda match: lookup[match.group()], history)
    history = '\n'.join(line for line in history.splitlines() if not re.fullmatch(r'\s+-\s*', line)) + '\n'
    if any(mapping[key] for key, _, _, kind in SENSORS if kind == 'energy'):
        write('home-assistant/pv_history.yaml', history)
    write('home-assistant/solaranlage-blueprint.yaml', blueprint())
    rest = render_package(mapping).split('\nautomation:', 1)[0] + '\n'
    write('home-assistant/rest-only.yaml', rest)
    write('home-assistant/secrets-ergaenzen.yaml',
          'pv_beta_url: ' + json.dumps(relay_url) + '\npv_beta_write_authorization: ' + json.dumps('Bearer ' + write_token) + '\n')
    write('alexa/relay_config.json', json.dumps({'url': relay_url, 'read_token': read_token}, indent=2))
    from build_skill import build
    write('alexa/lambda_function.py', build())
    write('alexa/interaction-model.de-DE.json', (ROOT / 'alexa/interaction-model.de-DE.json').read_text(encoding='utf-8'))
    write('relay/worker.mjs', (ROOT / 'cloudflare/worker.mjs').read_text(encoding='utf-8'))
    write('relay/schema.sql', (ROOT / 'cloudflare/schema.sql').read_text(encoding='utf-8'))
    write('relay/secrets.json', json.dumps({'READ_TOKEN': read_token, 'WRITE_TOKEN': write_token}))
    manifest = json.loads((ROOT / 'cloudflare/wrangler.example.jsonc').read_text(encoding='utf-8'))
    manifest.update(name=worker_name)
    manifest['d1_databases'][0].update(database_name=worker_name, database_id=db_id)
    write('relay/wrangler.jsonc', json.dumps(manifest, indent=2))
    write('NICHT-VEROEFFENTLICHEN.txt', 'Dieser Ordner enthaelt geheime Schluessel. Nicht auf GitHub oder in Screenshots teilen.\n')
    write('NAECHSTE-SCHRITTE.md', '''# Installation vorbereiten

Dieser Ordner ist vertraulich. Erzeugung allein hat nichts bereitgestellt.
Nutze ausschliesslich einen neuen Worker und eine neue D1-Datenbank.

1. Im Unterordner `relay`: `npx wrangler deploy`.
2. Dort: `npx wrangler secret bulk secrets.json`.
3. Dort: `npx wrangler d1 execute ''' + worker_name + ''' --remote --file schema.sql`.
4. In HA pv_beta.yaml und gegebenenfalls pv_history.yaml als Packages verwenden.
   Alternativ nur fuer Live/Heute: rest-only.yaml plus Blueprint verwenden,
   nicht beide Automationen. secrets-ergaenzen.yaml in bestehende secrets.yaml einfuegen.
5. Konfiguration in der HA-Testinstanz pruefen, neu starten, ersten Upload abwarten.
6. Im Projekt: `python installer.py check --config "''' + str(out / 'alexa/relay_config.json') + '''"`.
7. Neuen Alexa-Entwickler-Skill anlegen. Dateien aus alexa/ verwenden,
   Interaktionsmodell bauen und Backend deployen. Bestehenden Skill nicht ersetzen.

Ausfuehrliche Anleitung: docs/EINFACH-EINRICHTEN.md im Projekt.
''')
    return out


def choose_mapping(states=None):
    mapping = {}
    for key, label, _, kind in SENSORS:
        candidates = []
        if states:
            candidates = sorted(entity for entity, item in states.items() if entity.startswith('sensor.') and
                                item.get('attributes', {}).get('unit_of_measurement') in
                                {'power': ['W', 'kW'], 'percent': ['%'], 'energy': ['Wh', 'kWh', 'MWh']}[kind])
        print('\n' + label + (' (Pflicht)' if key == 'power_w' else ' (optional: Enter fuer nicht vorhanden)'))
        for index, entity in enumerate(candidates, 1):
            # Do not print state values, friendly names, tokens or other HA data.
            print('  ' + str(index) + ': ' + entity)
        while True:
            selected = input('Nummer oder sensor.entity_id: ').strip()
            if selected.isdigit() and 1 <= int(selected) <= len(candidates):
                selected = candidates[int(selected) - 1]
            if (selected or key != 'power_w') and (not selected or re.fullmatch(r'sensor\.[a-z0-9_]+', selected)):
                mapping[key] = selected
                break
            print('Bitte gueltige sensor.entity_id oder eine der angezeigten Nummern eingeben.')
    validate_mapping(mapping)
    return mapping


def check_relay(config):
    from beta_live_reader import read_pv
    config = json.loads(Path(config).read_text(encoding='utf-8'))
    endpoint(config['url'], relay=True)
    # Same non-redirecting transport for this check as for HA discovery.
    data = get_json(config['url'], config['read_token'])
    if not isinstance(data, dict) or 'received_at' not in data:
        raise SetupError('Relay-Antwort enthaelt keinen Empfangszeitpunkt.')
    # Validate without a second request, using the production parser with an isolated response.
    from unittest.mock import patch
    from io import BytesIO
    with patch('beta_live_reader.urlopen', return_value=BytesIO(json.dumps(data).encode())):
        result = read_pv(config['url'], config['read_token'])
    print('WARN: HA-Upload seit mehr als drei Minuten ausgeblieben.' if result['stale'] else 'OK: Relay erreichbar und HA-Upload aktuell.')
    missing = [key for key, value in result['metrics'].items() if value is None]
    if missing:
        print('WARN: Fehlende optionale Werte: ' + ', '.join(missing))
    return 1 if result['stale'] else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description='Solaranlage lokal einrichten (keine Aenderung an bestehenden Diensten).')
    sub = parser.add_subparsers(dest='command', required=True)
    wizard = sub.add_parser('wizard', help='Sensoren auswaehlen und neue Dateien erzeugen')
    wizard.add_argument('--out', required=True, help='Neuer, noch nicht vorhandener privater Ausgabeordner')
    wizard.add_argument('--ha-url', help='Optional: HA-Entitaeten nur lesen; Token wird verdeckt abgefragt')
    check = sub.add_parser('check', help='Relay und letzten HA-Upload nur lesen')
    check.add_argument('--config', required=True)
    verify = sub.add_parser('check-ha', help='Sensorzuordnung gegen HA pruefen, ohne etwas zu aendern')
    verify.add_argument('--ha-url', required=True)
    verify.add_argument('--mapping', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'check':
            return check_relay(args.config)
        states = None
        if args.ha_url:
            if args.ha_url.startswith('http:'):
                print('HTTP uebertraegt den HA-Token unverschluesselt. Nur im vertrauenswuerdigen Heimnetz verwenden.')
                if input('HTTP bewusst verwenden? ja/NEIN: ') != 'ja':
                    return 1
            states = load_states(args.ha_url, getpass.getpass('HA Long-Lived Access Token (nur im Arbeitsspeicher): '))
        if args.command == 'check-ha':
            problems = issues(json.loads(Path(args.mapping).read_text(encoding='utf-8')), states)
            for level, message in problems:
                print(level + ': ' + message)
            print('Sensorpruefung abgeschlossen. Recorder-Tagesstatistik muss separat in HA geprueft werden.')
            return int(any(level == 'FEHLER' for level, _ in problems))
        print('PV-Gesamtleistung muss BKW bereits enthalten. Energiezaehler sind kumulierte Zaehler, keine Tages-/Leistungssensoren.')
        mapping = choose_mapping(states)
        if states is not None:
            problems = issues(mapping, states)
            for level, message in problems:
                print(level + ': ' + message)
            if any(level == 'FEHLER' for level, _ in problems):
                raise SetupError('Sensorfehler zuerst korrigieren; es wurden keine Dateien erzeugt.')
        relay_url = input('Neue Worker-HTTPS-Adresse inklusive /pv: ').strip()
        worker_name = input('Name des NEUEN Workers und seiner D1-Datenbank: ').strip()
        db_id = input('ID der NEUEN D1-Datenbank: ').strip()
        generate(args.out, mapping, relay_url, worker_name, db_id)
        print('Dateien erzeugt. Naechste Schritte: docs/EINFACH-EINRICHTEN.md. Noch nichts bereitgestellt.')
        return 0
    except HTTPError as error:
        print({401: 'FEHLER: Zugriff verweigert. Passenden Token pruefen.',
               403: 'FEHLER: Keine Berechtigung.', 404: 'FEHLER: Adresse falsch oder noch kein erster HA-Upload.',
               503: 'FEHLER: Relay-Datenbank nicht erreichbar.'}.get(error.code, 'FEHLER: HTTP ' + str(error.code)))
    except FileExistsError:
        print('FEHLER: Ausgabeordner existiert bereits. Einen neuen Ordnernamen verwenden; nichts wird ueberschrieben.')
    except SetupError as error:
        print('FEHLER: ' + str(error))
    except (KeyboardInterrupt, EOFError):
        print('\nEinrichtung abgebrochen; keine Bereitstellung ausgefuehrt.')
    except (URLError, OSError):
        print('FEHLER: Verbindung/Dateizugriff fehlgeschlagen. Adresse, Netzwerk und gueltiges TLS-Zertifikat pruefen.')
    except (ValueError, KeyError, TypeError):
        print('FEHLER: Ungueltige Konfiguration oder Daten. IDs, Einheiten und JSON-Format pruefen.')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
