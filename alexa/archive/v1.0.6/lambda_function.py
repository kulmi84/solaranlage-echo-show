"""Read-only PV relay client, to be integrated into the Beta skill."""
import json
import math
from datetime import datetime, timezone
from urllib.request import Request, build_opener, HTTPRedirectHandler


class NoRelayRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def urlopen(request, timeout):
    return build_opener(NoRelayRedirect).open(request, timeout=timeout)


def read_pv(url, read_token):
    if not url.startswith('https://'):
        raise ValueError('HTTPS required')
    request = Request(url, headers={
        'Authorization': 'Bearer ' + read_token,
        'User-Agent': 'HomeAssistant-PV-Beta/1.0',
        'Accept': 'application/json',
    })
    with urlopen(request, timeout=3) as response:
        raw = response.read(4097)
    if len(raw) > 4096:
        raise ValueError('Response too large')
    data = json.loads(raw)
    power = data.get('power_w')
    if isinstance(power, bool) or not isinstance(power, (int, float)) or not math.isfinite(power) or power < 0:
        raise ValueError('Invalid power')
    received = datetime.fromisoformat(data['received_at'].replace('Z', '+00:00'))
    age = (datetime.now(timezone.utc) - received).total_seconds()
    if age < -60:
        raise ValueError('Invalid timestamp')
    metrics = {}
    for key in ['pv_dc_w', 'bkw_w', 'home_w', 'grid_import_w', 'grid_export_w', 'battery_soc', 'battery_charge_w', 'battery_discharge_w', 'today_pv_kwh', 'today_home_kwh', 'today_grid_import_kwh', 'today_grid_export_kwh', 'today_battery_charge_kwh', 'today_battery_discharge_kwh']:
        value = data.get(key)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or value > (100 if key == 'battery_soc' else 10000000)):
            raise ValueError('Invalid metric')
        metrics[key] = value
    metrics['power_w'] = power
    energy_date = data.get('energy_date')
    today = data.get('local_date')
    if energy_date != today:
        for key in metrics:
            if key.startswith('today_'): metrics[key] = None
    history = {}
    history_status = 'Noch keine Monats- und Jahreswerte'
    raw_history = data.get('history')
    if isinstance(raw_history, dict):
        try:
            if not isinstance(raw_history.get('received_at'), str):
                raise ValueError('Invalid history timestamp')
            h_received = datetime.fromisoformat(raw_history['received_at'].replace('Z', '+00:00'))
            h_age = (datetime.now(timezone.utc) - h_received).total_seconds()
            if h_age < -60:
                raise ValueError('Invalid history timestamp')
            for prefix, period in [('month', (today or '')[:7]), ('year', (today or '')[:4])]:
                valid_period = bool(period) and raw_history.get(prefix + '_id') == period
                for name in ['pv', 'home', 'grid_import', 'grid_export', 'battery_charge', 'battery_discharge']:
                    key = prefix + '_' + name + '_kwh'
                    value = raw_history.get(key)
                    if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or value > 10000000):
                        raise ValueError('Invalid history value')
                    history[key] = value if valid_period else None
            history_status = 'Stand ' + raw_history['received_at'][:16].replace('T', ' ') + ' UTC · alle 6 Stunden'
            if h_age > 6 * 3600 + 600:
                history_status = 'VERALTET · Monats-/Jahreswerte seit über 6 Stunden ohne Upload'
            if raw_history.get('month_id') != (today or '')[:7]:
                history_status = 'Neuer Monat · aktuelle Monatswerte stehen noch aus'
        except (ValueError, KeyError, TypeError):
            history = {}
            history_status = 'Monats- und Jahreswerte nicht verfügbar'
    return {
        'metrics': metrics,
        'history': history,
        'historyStatus': history_status,
        'monthLabel': (today or '')[:7],
        'yearLabel': (today or '')[:4],
        'energyDate': energy_date,
        'receivedText': data.get('received_local', '—'),
        'valueText': f'{power / 1000:.2f}'.replace('.', ',') + ' kW',
        'statusText': 'VERALTET · seit mehr als 3 Minuten kein Empfang' if age > 180 else 'PV-Leistung · zuletzt empfangener Wert',
        'stale': age > 180,
    }


"""Native Solaranlage display: live power above today's energy totals."""
import json
import time
from pathlib import Path

REFRESH_INTERVAL_MS = 60_000
DISPLAY_DURATION_MS = 60 * 60_000
HISTORY_INTERVAL_MS = 6 * 60 * 60_000
SPOKEN_METRICS = {
    'ProductionIntent': ('power_w', 'Die aktuelle Leistung inklusive Balkonkraftwerk', 'die aktuelle Leistung', 'power'),
    'BatteryIntent': ('battery_soc', 'Der Akkustand', 'den Akkustand', 'percent'),
    'ConsumptionIntent': ('home_w', 'Der aktuelle Hausverbrauch', 'den Hausverbrauch', 'power'),
    'TodayProductionIntent': ('today_pv_kwh', 'Die heutige Gesamtproduktion inklusive Balkonkraftwerk', 'die heutige Gesamtproduktion', 'energy'),
    'TodayExportIntent': ('today_grid_export_kwh', 'Die heutige Einspeisung', 'die heutige Einspeisung', 'energy'),
}


def number(value, unit, digits=2):
    if value is None:
        return '—'
    return f'{value:.{digits}f}'.replace('.', ',') + ' ' + unit


def power(value):
    if value is None:
        return '—'
    return number(value / 1000, 'kW') if value >= 1000 else number(value, 'W', 0)


def text(value, size, color='#F4F6FA', **extra):
    return dict(type='Text', text=value, fontSize=size, color=color, maxLines=1, **extra)


def spoken_reading(pv, intent):
    metrics = pv.get('metrics', {})
    key, label, missing_label, kind = SPOKEN_METRICS[intent]
    value = metrics.get(key)
    if value is None:
        return 'Für ' + missing_label + ' liegen keine Daten vor.'
    unit_value = (number(value, 'Kilowattstunden') if kind == 'energy' else
                  number(value, 'Prozent', 0) if kind == 'percent' else
                  number(value / 1000, 'Kilowatt') if value >= 1000 else number(value, 'Watt', 0))
    if pv.get('stale', True):
        return 'Achtung, die Daten sind veraltet. ' + label + ' lag zuletzt bei ' + unit_value + '.'
    return label + ' beträgt ' + unit_value + '.'


def card(label, value, detail, color, extra=''):
    return {
        'type': 'Frame', 'width': '23vw', 'height': '100%',
        'backgroundColor': '#172330', 'borderColor': '#2D3D4B', 'borderWidth': '1dp',
        'borderRadius': '14dp',
        'item': {'type': 'Container', 'paddingLeft': '1.5vw', 'paddingRight': '1vw',
                 'paddingTop': '2vh', 'items': [
                     text(label, '3.4vh', '#AFC1D1'),
                     text(value, '6.2vh', color, fontWeight='700', spacing='1vh'),
                     text(detail, '3vh', '#CED9E3', spacing='1vh'),
                     text(extra, '3vh', '#CED9E3', spacing='0.4vh'),
                 ]}
    }


def native_handler(event, context):
    request = event.get('request', {})
    intent = request.get('intent', {}).get('name', '')
    if request.get('type') == 'SessionEndedRequest':
        return {'version': '1.0', 'response': {}}
    if intent in ('AMAZON.StopIntent', 'AMAZON.CancelIntent'):
        return {'version': '1.0', 'response': {'shouldEndSession': True}}
    if intent == 'AMAZON.FallbackIntent':
        return {'version': '1.0', 'response': {}}
    if intent == 'AMAZON.HelpIntent':
        return {'version': '1.0', 'response': {
            'outputSpeech': {'type': 'PlainText', 'text':
                'Frage meine Solaranlage nach der aktuellen Leistung, dem Akkustand, dem aktuellen Verbrauch, der heutigen Gesamtproduktion oder der heutigen Einspeisung.'},
            'shouldEndSession': True}}
    now_ms = int(time.time() * 1000)
    expires_at = now_ms + DISPLAY_DURATION_MS
    page = 0
    if request.get('type') == 'Alexa.Presentation.APL.UserEvent':
        arguments = request.get('arguments', [])
        if arguments == ['refresh']:
            pass  # A deliberate touch starts a fresh display period.
        elif (isinstance(arguments, list) and len(arguments) in (2, 3) and arguments[0] == 'auto_refresh'
              and type(arguments[1]) is int
              and arguments[1] <= now_ms + DISPLAY_DURATION_MS
              and (len(arguments) == 2 or (type(arguments[2]) is int and arguments[2] in (0, 1)))):
            expires_at = arguments[1]
            page = arguments[2] if len(arguments) == 3 else 0
            if expires_at <= now_ms:
                return {'version': '1.0', 'response': {
                    'directives': [{'type': 'Alexa.Presentation.APL.ExecuteCommands',
                                    'token': 'solaranlage', 'commands': [{'type': 'Finish'}]}],
                    'shouldEndSession': True}}
        else:
            return {'version': '1.0', 'response': {}}
    try:
        config = json.loads(Path(__file__).with_name('relay_config.json').read_text())
        if config.get('mode') == 'public_beta':
            access_token = event.get('context', {}).get('System', {}).get('user', {}).get('accessToken')
            if not access_token:
                return {'version': '1.0', 'response': {
                    'outputSpeech': {'type': 'PlainText', 'text': 'Bitte verbinde deine Anlage zuerst in der Alexa-App mit dem Skill.'},
                    'card': {'type': 'LinkAccount'}, 'shouldEndSession': True}}
            try:
                pv = read_pv(config['url'], access_token)
            except Exception as error:
                if getattr(error, 'code', None) == 401:
                    return {'version': '1.0', 'response': {
                        'outputSpeech': {'type': 'PlainText', 'text': 'Bitte verbinde deine Anlage erneut in der Alexa-App.'},
                        'card': {'type': 'LinkAccount'}, 'shouldEndSession': True}}
                raise
        else:
            pv = read_pv(config['url'], config['read_token'])
    except Exception:
        pv = {'metrics': {}, 'valueText': '—', 'statusText': 'Keine aktuellen Daten · Verbindung prüfen', 'stale': True}
    m = pv.get('metrics', {})
    g = m.get
    interfaces = event.get('context', {}).get('System', {}).get('device', {}).get('supportedInterfaces', {})
    speech = spoken_reading(pv, intent) if intent in SPOKEN_METRICS else None
    if 'Alexa.Presentation.APL' not in interfaces:
        return {'version': '1.0', 'response': {
            'outputSpeech': {'type': 'PlainText', 'text': speech or 'Solaranlage. PV-Leistung: ' + pv['valueText'] + '. Hausverbrauch: ' + power(g('home_w')) + '. Akkustand: ' + number(g('battery_soc'), 'Prozent', 0) + '. ' + pv['statusText']},
            'shouldEndSession': True}}
    gold, blue, purple, teal = '#FFD166', '#8BCBFF', '#C3A0FF', '#51D3C5'
    live = [
        card('PV + BKW', power(g('power_w')), 'PV ' + power(g('pv_dc_w')), gold, 'BKW ' + power(g('bkw_w'))),
        card('Haus', power(g('home_w')), 'Verbrauch jetzt', blue),
        card('Netz', power(g('grid_export_w')), 'Einspeisung', purple, 'Bezug ' + power(g('grid_import_w'))),
        card('Akku', number(g('battery_soc'), '%', 0), 'Laden ' + power(g('battery_charge_w')), teal, 'Entladen ' + power(g('battery_discharge_w'))),
    ]
    energy = lambda key: number(g(key), 'kWh')
    daily = [
        card('PV + BKW', energy('today_pv_kwh'), 'Erzeugung', gold),
        card('Haus', energy('today_home_kwh'), 'Verbrauch', blue),
        card('Netz', energy('today_grid_export_kwh'), 'Einspeisung', purple, 'Bezug ' + energy('today_grid_import_kwh')),
        card('Akku', energy('today_battery_charge_kwh'), 'Geladen', teal, 'Entladen ' + energy('today_battery_discharge_kwh')),
    ]
    status = pv['statusText'] if pv['stale'] else 'Stand ' + pv.get('receivedText', '—') + ' Uhr · Auto alle 60 s · Tageswerte aus HA-Statistik'
    document = {
        'type': 'APL', 'version': '1.6', 'theme': 'dark',
        'settings': {'idleTimeout': max(1000, expires_at - now_ms)},
        'handleTick': [{
            'minimumDelay': REFRESH_INTERVAL_MS,
            'when': '${displayState == "foreground" && utcTime >= ' + str(now_ms + REFRESH_INTERVAL_MS) + ' && utcTime < ' + str(expires_at) + '}',
            'commands': [{'type': 'SendEvent', 'arguments': ['auto_refresh', expires_at],
                          'sequencer': 'solarRefresh'}],
        }],
        'mainTemplate': {'items': [{
            'type': 'Container', 'width': '100vw', 'height': '100vh',
            'backgroundColor': '#0C151F', 'paddingLeft': '3vw', 'paddingRight': '3vw',
            'paddingTop': '2vh', 'items': [
                {'type': 'Container', 'direction': 'row', 'height': '10vh', 'alignItems': 'center', 'justifyContent': 'spaceBetween', 'items': [
                    text('Solaranlage', '6vh', fontWeight='700'),
                    {'type': 'TouchWrapper', 'onPress': [{'type': 'SendEvent', 'arguments': ['refresh']}], 'item': text('Aktualisieren', '3.6vh', blue, padding='1.5vh')},
                ]},
                text('LIVE', '3vh', '#8FA8BC', spacing='1vh'),
                {'type': 'Container', 'direction': 'row', 'height': '30vh', 'justifyContent': 'spaceBetween', 'spacing': '1vh', 'items': live},
                text('HEUTE · seit Mitternacht', '3vh', '#8FA8BC', spacing='2vh'),
                {'type': 'Container', 'direction': 'row', 'height': '30vh', 'justifyContent': 'spaceBetween', 'spacing': '1vh', 'items': daily},
                text(status, '2.7vh', gold if pv['stale'] else '#8FA8BC', spacing='2vh'),
            ]
        }]}
    }
    # Wrap navigation allows a right swipe from the first page to the second.
    history = pv.get('history', {})
    def history_cards(prefix):
        def n(key):
            value = history.get(prefix + '_' + key + '_kwh')
            return '—' if value is None else f'{value:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')
        cards = [card('PV + BKW', n('pv'), 'kWh · Erzeugung', gold),
                 card('Haus', n('home'), 'kWh · Verbrauch', blue),
                 card('Netz', n('grid_export'), 'kWh · Einspeisung', purple, 'Bezug ' + n('grid_import') + ' kWh'),
                 card('Akku', n('battery_charge'), 'kWh · Geladen', teal, '↓ ' + n('battery_discharge') + ' kWh')]
        for item in cards:
            item['item']['items'][1]['fontSize'] = '5vh'
        return cards
    live_page = document['mainTemplate']['items'][0]
    live_page['id'] = 'livePage'
    live_page['items'][0]['items'].append({
        'type': 'TouchWrapper', 'onPress': [{'type': 'SetPage', 'componentId': 'solarPager',
                                           'position': 'absolute', 'value': 1}],
        'item': text('Monat/Jahr →', '3vh', blue, padding='1vh')})
    live_page['items'].append(text('1/2 · Nach rechts wischen: Monat/Jahr', '2.3vh', '#8FA8BC', spacing='1vh'))
    history_page = {
        'type': 'Container', 'id': 'historyPage', 'width': '100vw', 'height': '100vh',
        'backgroundColor': '#0C151F', 'paddingLeft': '3vw', 'paddingRight': '3vw', 'paddingTop': '2vh',
        'items': [
            {'type': 'Container', 'direction': 'row', 'height': '10vh', 'alignItems': 'center',
             'justifyContent': 'spaceBetween', 'items': [
                text('Monat & Jahr', '5.5vh', fontWeight='700'),
                {'type': 'TouchWrapper', 'onPress': [{'type': 'SetPage', 'componentId': 'solarPager',
                 'position': 'absolute', 'value': 0}], 'item': text('Live/Heute →', '3vh', blue, padding='1vh')}]},
            text('MONAT · ' + pv.get('monthLabel', '—'), '3vh', '#8FA8BC', spacing='1vh'),
            {'type': 'Container', 'direction': 'row', 'height': '30vh', 'justifyContent': 'spaceBetween',
             'spacing': '1vh', 'items': history_cards('month')},
            text('JAHR · ' + pv.get('yearLabel', '—'), '3vh', '#8FA8BC', spacing='2vh'),
            {'type': 'Container', 'direction': 'row', 'height': '30vh', 'justifyContent': 'spaceBetween',
             'spacing': '1vh', 'items': history_cards('year')},
            text(pv.get('historyStatus', 'Noch keine Monats- und Jahreswerte'), '2.5vh', '#8FA8BC', spacing='2vh'),
            text('2/2 · Nach links wischen: Live/Heute', '2.3vh', '#8FA8BC', spacing='1vh'),
        ]}
    document['mainTemplate']['items'] = [{
        'type': 'Container', 'id': 'solarRoot', 'width': '100vw', 'height': '100vh',
        'bind': [{'name': 'currentPage', 'value': page}],
        'items': [{'type': 'Pager', 'id': 'solarPager', 'width': '100vw', 'height': '100vh',
                   'navigation': 'wrap', 'pageDirection': 'horizontal', 'initialPage': page,
                   'onPageChanged': [{'type': 'SetValue', 'componentId': 'solarRoot',
                                      'property': 'currentPage', 'value': '${event.source.page}'}],
                   'items': [live_page, history_page]}]}]
    tick = document['handleTick'][0]
    tick['when'] = ('${displayState == "foreground" && utcTime < ' + str(expires_at) +
                    ' && ((currentPage == 0 && utcTime >= ' + str(now_ms + REFRESH_INTERVAL_MS) +
                    ') || (currentPage == 1 && utcTime >= ' + str(now_ms + HISTORY_INTERVAL_MS) + '))}')
    tick['commands'][0]['arguments'] = ['auto_refresh', expires_at, '${currentPage}']
    document['mainTemplate']['items'][0]['handleTick'] = document.pop('handleTick')
    # v1.0.5: render APL while ending voice on launch and touch/tick updates.
    # Do not Finish the document: the Echo may keep the dashboard visible.
    response = {'directives': [{'type': 'Alexa.Presentation.APL.RenderDocument', 'token': 'solaranlage', 'document': document}]}
    if request.get('type') in ('LaunchRequest', 'Alexa.Presentation.APL.UserEvent'):
        response['shouldEndSession'] = True
    if speech:
        response['outputSpeech'] = {'type': 'PlainText', 'text': speech}
    return {'version': '1.0', 'response': response}

"""Production image transport, promoted from the device-tested long-running beta."""
from urllib.request import Request, build_opener, HTTPRedirectHandler
import re

IMAGE_ORIGIN = 'https://solaranlage-display.kulmi84.workers.dev'
RELAY_URL = 'https://solaranlage-public-beta.kulmi84.workers.dev/v1/pv'


class NoImageRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def image_access_token(event):
    return (event.get('context', {}).get('System', {}).get('user', {}).get('accessToken')
            or event.get('session', {}).get('user', {}).get('accessToken'))


def image_config():
    return json.loads(Path(__file__).with_name('relay_config.json').read_text(encoding='utf-8'))


def create_image_session(access, config):
    if not re.fullmatch('[a-f0-9]{64}', access or ''):
        raise ValueError('Account linking required')
    if config.get('image_session_url') != IMAGE_ORIGIN + '/image/session':
        raise ValueError('Unexpected image origin')
    payload = json.dumps({'access_token': access}).encode('utf-8')
    request = Request(config['image_session_url'], data=payload, headers={
        'Authorization': 'Bearer ' + config['image_session_key'],
        'Content-Type': 'application/json', 'Accept': 'application/json',
        'User-Agent': 'Solaranlage-Echo-Show-Test/1.0'})
    with build_opener(NoImageRedirect()).open(request, timeout=8) as response:
        raw = response.read(4097)
    if len(raw) > 4096:
        raise ValueError('Unexpected image response')
    result = json.loads(raw)
    base = result.get('base_url', '')
    if not base.startswith(IMAGE_ORIGIN + '/dashboard.png?s=') or not re.fullmatch(
            re.escape(IMAGE_ORIGIN) + r'/dashboard\.png\?s=[A-Za-z0-9_-]{40,1000}', base):
        raise ValueError('Invalid image URL')
    if not isinstance(result.get('expires_in'), int) or not 1 <= result['expires_in'] <= 86400:
        raise ValueError('Invalid image lifetime')
    return result


def live_image_document(grant=None, message=None):
    root = {'type': 'Container', 'id': 'solarRoot', 'width': '100vw', 'height': '100vh',
        'backgroundColor': '#0C151F',
        'bind': [{'name':'currentPage','value':0}, {'name':'imageFailed','value':False},
                 {'name':'lastDashboardRefresh','value':0}],
        'handleTick': [{'minimumDelay':1000,'commands':[]}],
        'items': [{'type':'Pager','id':'solarPager','width':'100vw','height':'100vh',
            'navigation':'wrap','pageDirection':'horizontal','initialPage':0,
            'onPageChanged':[{'type':'SetValue','componentId':'solarRoot','property':'currentPage','value':'${event.source.page}'}],
            'items':[]}]}
    document={'type':'APL','version':'1.6','theme':'dark',
        'settings':{'idleTimeout':grant['expires_in']*1000 if grant else 120000},
        'mainTemplate':{'items':[root]}}
    if message:
        root['items']=[{'type':'Container','padding':'5vw','items':[
            text('Solaranlage','6vh',fontWeight='700'),
            {'type':'Text','text':message,'fontSize':'3vh','color':'#FFD166','spacing':'5vh','maxLines':4}]}]
    else:
        root['items'].append({'type':'Text','text':'Aktualisierung fehlgeschlagen. Bitte erneut versuchen.',
            'color':'#FF8080','fontSize':'2.3vh','position':'absolute','bottom':'0.5vh',
            'left':'3vw','width':'94vw','display':'${imageFailed ? "normal" : "none"}'})
    return {'version':'1.0','response':{'shouldEndSession':True,'directives':[
        {'type':'Alexa.Presentation.APL.RenderDocument','token':'solaranlage','document':document}]}}


def house_image_pilot(result, grant):
    """Native dashboard shell with independently refreshed value images."""
    root = result['response']['directives'][0]['document']['mainTemplate']['items'][0]
    base = grant['base_url'].replace('/dashboard.png?', '/tile.png?', 1)
    lifetime = grant['expires_in'] * 1000
    root['bind'] += [{'name': 'tileImageBase', 'value': base}, {'name': 'tileImageLoads', 'value': 0}]
    pages, timer = [], []
    for page_index, page_name in enumerate(('live', 'history')):
        refresh, rows = [], []
        for row in range(2):
            cards = []
            for col, label in enumerate(('PV + BKW', 'Haus', 'Netz', 'Akku')):
                image_id = 'tile_' + page_name + '_' + str(row) + '_' + str(col)
                suffix = '&page=' + page_name + '&row=' + str(row) + '&col=' + str(col)
                command = {'type': 'SetValue', 'componentId': image_id, 'property': 'source',
                           'value': '${tileImageBase + "' + suffix + '&layout=final&n=" + elapsedTime}'}
                refresh.append(command)
                cards.append({'type': 'Frame', 'width': '23vw', 'height': '100%',
                    'backgroundColor': '#172330', 'borderRadius': '14dp',
                    'borderColor': '#2D3D4B', 'borderWidth': '1dp',
                    'item': {'type': 'Container', 'paddingLeft': '1.5vw', 'paddingRight': '1vw',
                             'paddingTop': '2vh', 'items': [text(label, '3.4vh', '#AFC1D1'),
                        {'type': 'Image', 'id': image_id, 'width': '20.5vw', 'height': '19.25vh', 'spacing': '1vh',
                         'scale': 'best-fit', 'align': 'top-left', 'source': base + suffix + '&layout=final&n=initial',
                         'onLoad': [{'type': 'SetValue', 'componentId': 'solarRoot',
                                     'property': 'imageFailed', 'value': False},
                                    {'type': 'SetValue', 'componentId': 'solarRoot',
                                     'property': 'tileImageLoads', 'value': '${tileImageLoads + 1}'}],
                         'onFail': [{'type': 'SetValue', 'componentId': 'solarRoot',
                                     'property': 'imageFailed', 'value': True}]}]}})
            heading = ('LIVE' if row == 0 else 'HEUTE - seit Mitternacht') if page_index == 0 else ('MONAT' if row == 0 else 'JAHR')
            rows += [text(heading, '3vh', '#8FA8BC', spacing='1vh' if row == 0 else '2vh'),
                     {'type': 'Container', 'direction': 'row', 'height': '30vh', 'justifyContent': 'spaceBetween', 'spacing': '1vh', 'items': cards}]
        status_base = base.replace('/tile.png?', '/status.png?', 1)
        status_id = 'sharedStatus' + page_name
        refresh.append({'type': 'SetValue', 'componentId': status_id, 'property': 'source',
                        'value': '${"' + status_base + '&n=" + elapsedTime}'})
        date = grant.get('local_date') or ''
        if page_index == 1 and re.fullmatch(r'\d{4}-\d\d-\d\d', date):
            month_names = ['Januar','Februar','Maerz','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember']
            month = int(date[5:7])
            if 1 <= month <= 12:
                rows[0]['text'] = 'MONAT - ' + month_names[month-1] + ' ' + date[:4]
                rows[2]['text'] = 'JAHR - ' + date[:4]
        pages.append({'type': 'Container', 'width': '100vw', 'height': '100vh',
            'backgroundColor': '#0C151F', 'paddingLeft': '3vw', 'paddingRight': '3vw', 'paddingTop': '2vh',
            'items': [{'type': 'Container', 'direction': 'row', 'height': '10vh',
                       'alignItems': 'center', 'justifyContent': 'spaceBetween', 'items': [
                text('Solaranlage' if page_index == 0 else 'Monat & Jahr', '6vh' if page_index == 0 else '5.5vh', fontWeight='700'),
                {'type': 'TouchWrapper', 'onPress': refresh, 'item': text('Aktualisieren', '3.6vh', '#8BCBFF', padding='1.5vh')},
                {'type': 'TouchWrapper', 'onPress': [{'type': 'SetPage', 'componentId': 'solarPager',
                     'position': 'absolute', 'value': 1-page_index}],
                 'item': text('Monat/Jahr' if page_index == 0 else 'Live/Heute', '3vh', '#8BCBFF', padding='1vh')}]}] + rows + [
                {'type': 'Image', 'id': status_id, 'width': '94vw', 'height': '3vh', 'scale': 'best-fit',
                 'align': 'left', 'spacing': '2vh', 'source': status_base + '&n=initial'},
                text('1/2 - Nach rechts wischen: Monat/Jahr' if page_index == 0 else '2/2 - Nach links wischen: Live/Heute',
                     '2.3vh', '#8FA8BC', spacing='1vh')]})
        for step in refresh:
            command = dict(step)
            command['when'] = ('${displayState == "foreground" && currentPage == ' + str(page_index) +
                ' && elapsedTime < ' + str(lifetime) +
                ' && (elapsedTime - lastDashboardRefresh >= 60000 || (imageFailed && elapsedTime - lastDashboardRefresh >= 10000))}')
            timer.append(command)
    root['items'][0]['height'] = '100vh'
    root['items'][0]['items'] = pages
    timer += [
        {'type': 'SetValue', 'componentId': 'solarRoot', 'property': 'lastDashboardRefresh',
         'value': '${elapsedTime}', 'when': '${displayState == "foreground" && (elapsedTime - lastDashboardRefresh >= 60000 || (imageFailed && elapsedTime - lastDashboardRefresh >= 10000))}'},
        {'type': 'SetValue', 'componentId': 'solarRoot', 'property': 'imageFailed',
         'value': True, 'when': '${elapsedTime >= ' + str(lifetime) + '}'}]
    root['handleTick'][-1]['commands'] = timer
    return result


def lambda_handler(event, context):
    request=event.get('request',{})
    kind,intent=request.get('type'),request.get('intent',{}).get('name')
    access=image_access_token(event)
    if kind=='Alexa.Presentation.APL.UserEvent':
        return {'version':'1.0','response':{}}
    if kind=='IntentRequest' and intent in SPOKEN_METRICS:
        if not access:
            return {'version':'1.0','response':{'card':{'type':'LinkAccount'},
                'outputSpeech':{'type':'PlainText','text':'Bitte verbinde deine Anlage in der Alexa-App mit Solaranlage.'},'shouldEndSession':True}}
        try:
            speech=spoken_reading(read_pv(RELAY_URL,access),intent)
        except Exception:
            speech='Die Live-Werte sind gerade nicht verfügbar.'
        return {'version':'1.0','response':{'outputSpeech':{'type':'PlainText','text':speech},'shouldEndSession':True}}
    if kind!='LaunchRequest':
        return native_handler(event,context)
    try:
        legacy_config=image_config()
    except Exception:
        legacy_config={}
    if legacy_config.get('read_token') and not legacy_config.get('image_session_url'):
        return native_handler(event,context)
    interfaces=event.get('context',{}).get('System',{}).get('device',{}).get('supportedInterfaces',{})
    if 'Alexa.Presentation.APL' not in interfaces:
        return native_handler(event,context)
    if not access:
        result=live_image_document(message='Bitte verbinde deine Anlage in der Alexa-App mit Solaranlage.')
        result['response']['card']={'type':'LinkAccount'}
        return result
    try:
        grant=create_image_session(access,image_config())
    except Exception:
        return live_image_document(message='Die Live-Werte sind gerade nicht verfügbar. Bitte Solaranlage später erneut öffnen.')
    return house_image_pilot(live_image_document(grant=grant),grant)
