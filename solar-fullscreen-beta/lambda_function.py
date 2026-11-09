"""Launch and refresh the native Betasolaranlage fullscreen display."""

import json
import re
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from uuid import uuid4

from relay_reader import read_pv


APL = 'Alexa.Presentation.APL'
ROOT = 'betaSolarRoot'
PAGER = 'betaSolarPager'
TOKEN_PREFIX = 'betasolaranlage-'
VERSION = '4.0.0'
BUILD = '0911'
INTERVALS = {'live': 60_000, 'history': 21_600_000}
MONTHS = ('Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli',
          'August', 'September', 'Oktober', 'November', 'Dezember')
LABELS = ('PV + BKW', 'Haus', 'Netz', 'Akku')
COLORS = ('#FFD166', '#8BCBFF', '#C3A0FF', '#51D3C5')
BACKGROUND = '#751C28'
MUTED = '#AFC1D1'
WHITE = '#F4F6FA'
DASH = '—'


def number(value, digits=2):
    if value is None:
        return DASH
    return f'{value:,.{digits}f}'.translate(str.maketrans(',.', '.,'))


def with_unit(value, unit, digits=2):
    return DASH if value is None else f'{number(value, digits)} {unit}'


def power(value):
    if value is not None and value >= 1000:
        return with_unit(value / 1000, 'kW')
    return with_unit(value, 'W', 0)


def readings(snapshot, page):
    metrics = snapshot.get('metrics', {}).get
    if page == 'live':
        first = (
            (power(metrics('power_w')), 'PV ' + power(metrics('pv_dc_w')), 'BKW ' + power(metrics('bkw_w'))),
            (power(metrics('home_w')), 'Verbrauch jetzt', ''),
            (power(metrics('grid_export_w')), 'Einspeisung', 'Bezug ' + power(metrics('grid_import_w'))),
            (with_unit(metrics('battery_soc'), '%', 0), 'Laden ' + power(metrics('battery_charge_w')),
             'Entladen ' + power(metrics('battery_discharge_w'))),
        )
        stamp = snapshot.get('receivedText', DASH)
        prefix = 'Veraltete Daten · Stand' if snapshot.get('stale', True) else 'Stand'
        status = snapshot.get('displayStatus', f'{prefix} {stamp} Uhr · Auto alle 60 s')
        return ('LIVE', 'HEUTE · seit Mitternacht'), (first, energy_row(metrics, 'today', True)), status

    history = snapshot.get('history', {}).get
    period = re.fullmatch(r'(\d{4})-(0[1-9]|1[0-2])', snapshot.get('monthLabel', ''))
    headings = ('MONAT', 'JAHR')
    if period:
        year, month = period.groups()
        headings = (f'MONAT · {MONTHS[int(month) - 1]} {year}', f'JAHR · {year}')
    stamp = snapshot.get('historyReceivedText')
    status = f'Stand {stamp} Uhr · Auto alle 6 h' if stamp else 'Monat/Jahr · kein Upload-Stand'
    return headings, (energy_row(history, 'month', False), energy_row(history, 'year', False)), status


def energy_row(get, period, inline_unit):
    def amount(key):
        value = get(f'{period}_{key}_kwh')
        return with_unit(value, 'kWh') if inline_unit else number(value)

    unit = '' if inline_unit else 'kWh · '
    trailing_unit = '' if inline_unit else ' kWh'
    return (
        (amount('pv'), unit + 'Erzeugung', ''),
        (amount('home'), unit + 'Verbrauch', ''),
        (amount('grid_export'), unit + 'Einspeisung', 'Bezug ' + amount('grid_import') + trailing_unit),
        (amount('battery_charge'), unit + 'Geladen', 'Entladen ' + amount('battery_discharge') + trailing_unit),
    )


def text(value, size, color=WHITE, **properties):
    return dict(type='Text', text=value, fontSize=size, color=color, maxLines=1, **properties)


def set_value(component, property_name, value):
    return dict(type='SetValue', componentId=component, property=property_name, value=value)


def refresh_commands(page):
    return [
        set_value(ROOT, page + 'Due', '${utcTime + ' + str(INTERVALS[page]) + '}'),
        {'type': 'SendEvent', 'arguments': ['betaRefresh', page], 'sequencer': 'betaSolarRefresh'},
    ]


def card(label, color, parts, component, page):
    sizes = ('6.2vh' if page == 'live' else '5vh', '3vh', '3vh')
    values = [text(part, size, color if index == 0 else '#CED9E3', id=f'{component}_{index}',
                   fontWeight='700' if index == 0 else '400', spacing='0.4vh' if index == 2 else '1vh')
              for index, (part, size) in enumerate(zip(parts, sizes))]
    return {'type': 'Frame', 'width': '23vw', 'height': '100%', 'backgroundColor': '#172330',
            'borderColor': '#2D3D4B', 'borderWidth': '1dp', 'borderRadius': '14dp',
            'item': {'type': 'Container', 'paddingLeft': '1.5vw', 'paddingRight': '1vw', 'paddingTop': '2vh',
                     'items': [text(label, '3.4vh', MUTED), *values]}}


def build_page(snapshot, page, index):
    headings, rows, status = readings(snapshot, page)
    button = 'Monat/Jahr' if index == 0 else 'Live/Heute'
    direction = 'rechts' if index == 0 else 'links'
    header = {'type': 'Container', 'direction': 'row', 'height': '10vh',
              'alignItems': 'center', 'justifyContent': 'spaceBetween', 'items': [
                  text('Betasolaranlage' if index == 0 else 'Monat & Jahr',
                       '6vh' if index == 0 else '5.5vh', fontWeight='700'),
                  {'type': 'TouchWrapper', 'onPress': refresh_commands(page),
                   'item': text('Aktualisieren', '3.6vh', COLORS[1], padding='1.5vh')},
                  {'type': 'TouchWrapper', 'onPress': [{'type': 'SetPage', 'componentId': PAGER,
                                                       'position': 'absolute', 'value': 1 - index}],
                   'item': text(button, '3vh', COLORS[1], padding='1vh')},
              ]}
    items = [header]
    for row, parts in enumerate(rows):
        items.append(text(headings[row], '3vh', MUTED, id=f'{page}Heading{row}',
                          spacing='1vh' if row == 0 else '2vh'))
        items.append({'type': 'Container', 'direction': 'row', 'height': '30vh',
                      'justifyContent': 'spaceBetween', 'spacing': '1vh',
                      'items': [card(label, color, values, f'{page}_{row}_{col}', page)
                                for col, (label, color, values) in enumerate(zip(LABELS, COLORS, parts))]})
    items.extend([text(status, '2.5vh', MUTED, id=page + 'Status', spacing='2vh'),
                  text(f'{index + 1}/2 · Nach {direction} wischen: {button} · {VERSION} (Build {BUILD})',
                       '2.3vh', MUTED, spacing='1vh')])
    return {'type': 'Container', 'width': '100vw', 'height': '100vh', 'backgroundColor': BACKGROUND,
            'paddingLeft': '3vw', 'paddingRight': '3vw', 'paddingTop': '2vh', 'items': items}


def render(snapshot):
    pages = [build_page(snapshot, page, index) for index, page in enumerate(INTERVALS)]
    root = {'type': 'Container', 'id': ROOT, 'width': '100vw', 'height': '100vh',
            'backgroundColor': BACKGROUND, 'bind': [{'name': 'currentPage', 'value': 0}],
            'handleTick': [], 'items': [{'type': 'Pager', 'id': PAGER, 'width': '100vw', 'height': '100vh',
                                        'navigation': 'wrap', 'pageDirection': 'horizontal',
                                        'onPageChanged': [set_value(ROOT, 'currentPage', '${event.source.page}')],
                                        'items': pages}]}
    for index, (page, interval) in enumerate(INTERVALS.items()):
        due = page + 'Due'
        root['bind'].append({'name': due, 'value': '${utcTime + ' + str(interval) + '}'})
        root['handleTick'].append({'minimumDelay': 1000,
                                   'when': '${displayState == "foreground" && currentPage == '
                                           + str(index) + ' && utcTime >= ' + due + '}',
                                   'commands': refresh_commands(page)})
    return {'type': 'APL', 'version': '1.6', 'theme': 'dark',
            'settings': {'idleTimeout': 86_400_000}, 'mainTemplate': {'items': [root]}}


def update_commands(snapshot, page):
    headings, rows, status = readings(snapshot, page)
    commands = [set_value(page + 'Status', 'text', status)]
    for row, parts in enumerate(rows):
        commands.append(set_value(f'{page}Heading{row}', 'text', headings[row]))
        commands.extend(set_value(f'{page}_{row}_{col}_{index}', 'text', value)
                        for col, values in enumerate(parts) for index, value in enumerate(values))
    return commands


def relay_url():
    url = json.loads(Path(__file__).with_name('relay_config.json').read_text(encoding='utf-8'))['url']
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path != '/v1/pv' or parsed.query or parsed.fragment):
        raise ValueError('Expected an HTTPS account-service read endpoint')
    return url


def reply(**response):
    return {'version': '1.0', 'response': {'shouldEndSession': True, **response}}


def lambda_handler(event, context):
    request = event.get('request', {})
    kind = request.get('type')
    if kind not in ('LaunchRequest', APL + '.UserEvent'):
        return reply()

    system = event.get('context', {}).get('System', {})
    page = None
    token = TOKEN_PREFIX + uuid4().hex
    if kind == APL + '.UserEvent':
        token = request.get('token', '')
        args = request.get('arguments', [])
        if (not isinstance(token, str) or not re.fullmatch(TOKEN_PREFIX + r'[a-f0-9]{32}', token)
                or 'presentationUri' in request or args not in (['betaRefresh', 'live'], ['betaRefresh', 'history'])):
            return reply()
        page = args[1]
    elif APL not in system.get('device', {}).get('supportedInterfaces', {}):
        return reply()

    access = system.get('user', {}).get('accessToken')
    if not access and page is None:
        return reply(card={'type': 'LinkAccount'})

    try:
        if not access:
            raise ValueError('Missing read access')
        snapshot = read_pv(relay_url(), access)
    except (OSError, ValueError, KeyError, TypeError) as error:
        if page:
            commands = [set_value(page + 'Status', 'text', 'Abruf fehlgeschlagen · letzte Werte bleiben sichtbar'),
                        set_value(ROOT, page + 'Due', '${utcTime + 60000}')]
            return reply(directives=[dict(type=APL + '.ExecuteCommands', token=token, commands=commands)])
        if isinstance(error, HTTPError) and error.code == 401:
            return reply(card={'type': 'LinkAccount'})
        document = render({'displayStatus': 'Keine aktuellen Daten · Verbindung prüfen'})
        return reply(directives=[dict(type=APL + '.RenderDocument', token=token, document=document)])

    if page:
        return reply(directives=[dict(type=APL + '.ExecuteCommands', token=token,
                                      commands=update_commands(snapshot, page))])
    return reply(directives=[dict(type=APL + '.RenderDocument', token=token, document=render(snapshot))])
