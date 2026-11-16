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

            history_status = 'Stand ' + raw_history['received_at'][:16].replace('T', ' ') + ' UTC Â· alle 6 Stunden'

            if h_age > 6 * 3600 + 600:

                history_status = 'VERALTET Â· Monats-/Jahreswerte seit Ã¼ber 6 Stunden ohne Upload'

            if raw_history.get('month_id') != (today or '')[:7]:

                history_status = 'Neuer Monat Â· aktuelle Monatswerte stehen noch aus'

        except (ValueError, KeyError, TypeError):

            history = {}

            history_status = 'Monats- und Jahreswerte nicht verfÃ¼gbar'

    return {

        'metrics': metrics,

        'history': history,

        'historyStatus': history_status,

        'monthLabel': (today or '')[:7],

        'yearLabel': (today or '')[:4],

        'energyDate': energy_date,

        'receivedText': data.get('received_local', 'â€”'),

        'valueText': f'{power / 1000:.2f}'.replace('.', ',') + ' kW',

        'statusText': 'VERALTET Â· seit mehr als 3 Minuten kein Empfang' if age > 180 else 'PV-Leistung Â· zuletzt empfangener Wert',

        'ageSeconds': max(0, int(age)),
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

        return 'â€”'

    return f'{value:.{digits}f}'.replace('.', ',') + ' ' + unit





def power(value):

    if value is None:

        return 'â€”'

    return number(value / 1000, 'kW') if value >= 1000 else number(value, 'W', 0)





def text(value, size, color='#F4F6FA', **extra):

    return dict(type='Text', text=value, fontSize=size, color=color, maxLines=1, **extra)





def spoken_reading(pv, intent):

    metrics = pv.get('metrics', {})

    key, label, missing_label, kind = SPOKEN_METRICS[intent]

    value = metrics.get(key)

    if value is None:

        return 'FÃ¼r ' + missing_label + ' liegen keine Daten vor.'

    unit_value = (number(value, 'Kilowattstunden') if kind == 'energy' else

                  number(value, 'Prozent', 0) if kind == 'percent' else

                  number(value / 1000, 'Kilowatt') if value >= 1000 else number(value, 'Watt', 0))

    if pv.get('stale', True):

        return 'Achtung, die Daten sind veraltet. ' + label + ' lag zuletzt bei ' + unit_value + '.'

    return label + ' betrÃ¤gt ' + unit_value + '.'





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





def native_handler(event, context, *, dev_text=False):

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

    duration = 24 * 60 * 60 * 1000 if dev_text else DISPLAY_DURATION_MS
    expires_at = now_ms + duration

    page = 0

    if request.get('type') == 'Alexa.Presentation.APL.UserEvent':

        arguments = request.get('arguments', [])

        if arguments == ['refresh']:

            pass  # A deliberate touch starts a fresh display period.
        elif dev_text and isinstance(arguments, list) and len(arguments) == 2 and arguments[0] == 'refresh' and type(arguments[1]) is int and arguments[1] in (0, 1):
            page = arguments[1]

        elif (isinstance(arguments, list) and len(arguments) in (2, 3) and arguments[0] == 'auto_refresh'

              and type(arguments[1]) is int

              and arguments[1] <= now_ms + duration

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

            access_token = image_access_token(event) if dev_text else event.get('context', {}).get('System', {}).get('user', {}).get('accessToken')

            if not access_token:

                return {'version': '1.0', 'response': {

                    'outputSpeech': {'type': 'PlainText', 'text': 'Bitte verbinde deine Anlage zuerst in der Alexa-App mit dem Skill.'},

                    'card': {'type': 'LinkAccount'}, 'shouldEndSession': True}}

            try:

                source_url = config['url']
                if dev_text:
                    source_url = config.get('direct_widget_test', {}).get('relay_url')
                    if source_url != 'https://solaranlage-dev-text-publisher.kulmi84.workers.dev/v1/pv':
                        raise ValueError('Scoped DEV relay required')
                pv = read_pv(source_url, access_token)

            except Exception as error:

                if dev_text and request.get('type') == 'Alexa.Presentation.APL.UserEvent':
                    return {'version': '1.0', 'response': {'shouldEndSession': True}}
                if getattr(error, 'code', None) == 401:

                    return {'version': '1.0', 'response': {

                        'outputSpeech': {'type': 'PlainText', 'text': 'Bitte verbinde deine Anlage erneut in der Alexa-App.'},

                        'card': {'type': 'LinkAccount'}, 'shouldEndSession': True}}

                raise

        else:

            pv = read_pv(config['url'], config['read_token'])

    except Exception:
        if dev_text and request.get('type') == 'Alexa.Presentation.APL.UserEvent':
            return {'version': '1.0', 'response': {'shouldEndSession': True}}

        pv = {'metrics': {}, 'valueText': 'â€”', 'statusText': 'Keine aktuellen Daten Â· Verbindung prÃ¼fen', 'stale': True}

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

        card('Solar', power(g('power_w')), 'PV ' + power(g('pv_dc_w')), gold, 'BKW ' + power(g('bkw_w'))),

        card('Haus', power(g('home_w')), 'Verbrauch jetzt', blue),

        card('Netz', power(g('grid_export_w')), 'Einspeisung', purple, 'Bezug ' + power(g('grid_import_w'))),

        card('Akku', number(g('battery_soc'), '%', 0), 'Laden ' + power(g('battery_charge_w')), teal, 'Entladen ' + power(g('battery_discharge_w'))),

    ]

    energy = lambda key: number(g(key), 'kWh')

    daily = [

        card('Solar', energy('today_pv_kwh'), 'Erzeugung', gold),

        card('Haus', energy('today_home_kwh'), 'Verbrauch', blue),

        card('Netz', energy('today_grid_export_kwh'), 'Einspeisung', purple, 'Bezug ' + energy('today_grid_import_kwh')),

        card('Akku', energy('today_battery_charge_kwh'), 'Geladen', teal, 'Entladen ' + energy('today_battery_discharge_kwh')),

    ]

    status = pv['statusText'] if pv['stale'] else 'Stand ' + pv.get('receivedText', 'â€”') + ' Uhr Â· Auto alle 60 s Â· Tageswerte aus HA-Statistik'

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

                text('HEUTE Â· seit Mitternacht', '3vh', '#8FA8BC', spacing='2vh'),

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

            return 'â€”' if value is None else f'{value:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')

        cards = [card('Solar', n('pv'), 'kWh Â· Erzeugung', gold),

                 card('Haus', n('home'), 'kWh Â· Verbrauch', blue),

                 card('Netz', n('grid_export'), 'kWh Â· Einspeisung', purple, 'Bezug ' + n('grid_import') + ' kWh'),

                 card('Akku', n('battery_charge'), 'kWh Â· Geladen', teal, 'â†“ ' + n('battery_discharge') + ' kWh')]

        for item in cards:

            item['item']['items'][1]['fontSize'] = '5vh'

        return cards

    live_page = document['mainTemplate']['items'][0]

    live_page['id'] = 'livePage'

    live_page['items'][0]['items'].append({

        'type': 'TouchWrapper', 'onPress': [{'type': 'SetPage', 'componentId': 'solarPager',

                                           'position': 'absolute', 'value': 1}],

        'item': text('Monat/Jahr â†’', '3vh', blue, padding='1vh')})

    live_page['items'].append(text('1/2 Â· Nach rechts wischen: Monat/Jahr', '2.3vh', '#8FA8BC', spacing='1vh'))

    history_page = {

        'type': 'Container', 'id': 'historyPage', 'width': '100vw', 'height': '100vh',

        'backgroundColor': '#0C151F', 'paddingLeft': '3vw', 'paddingRight': '3vw', 'paddingTop': '2vh',

        'items': [

            {'type': 'Container', 'direction': 'row', 'height': '10vh', 'alignItems': 'center',

             'justifyContent': 'spaceBetween', 'items': [

                text('Monat & Jahr', '5.5vh', fontWeight='700'),

                {'type': 'TouchWrapper', 'onPress': [{'type': 'SetPage', 'componentId': 'solarPager',

                 'position': 'absolute', 'value': 0}], 'item': text('Live/Heute â†’', '3vh', blue, padding='1vh')}]},

            text('MONAT Â· ' + pv.get('monthLabel', 'â€”'), '3vh', '#8FA8BC', spacing='1vh'),

            {'type': 'Container', 'direction': 'row', 'height': '30vh', 'justifyContent': 'spaceBetween',

             'spacing': '1vh', 'items': history_cards('month')},

            text('JAHR Â· ' + pv.get('yearLabel', 'â€”'), '3vh', '#8FA8BC', spacing='2vh'),

            {'type': 'Container', 'direction': 'row', 'height': '30vh', 'justifyContent': 'spaceBetween',

             'spacing': '1vh', 'items': history_cards('year')},

            text(pv.get('historyStatus', 'Noch keine Monats- und Jahreswerte'), '2.5vh', '#8FA8BC', spacing='2vh'),

            text('2/2 Â· Nach links wischen: Live/Heute', '2.3vh', '#8FA8BC', spacing='1vh'),

        ]}

    document['mainTemplate']['items'] = [{

        'type': 'Container', 'id': 'solarRoot', 'width': '100vw', 'height': '100vh',

        'bind': [{'name': 'currentPage', 'value': page}],

        'items': [{'type': 'Pager', 'id': 'solarPager', 'width': '100vw', 'height': '100vh',

                   'navigation': 'wrap', 'pageDirection': 'horizontal', 'initialPage': page,

                   'onPageChanged': [{'type': 'SetValue', 'componentId': 'solarRoot',

                                      'property': 'currentPage', 'value': '${event.source.page}'}],

                   'items': [live_page, history_page]}]}]

    if dev_text:
        # Keep existing header geometry; remove only the manual refresh control.
        live_page['items'][0]['items'].pop(1)
    tick = document['handleTick'][0]

    tick['when'] = ('${displayState == "foreground" && utcTime < ' + str(expires_at) +

                    ' && ((currentPage == 0 && utcTime >= ' + str(now_ms + REFRESH_INTERVAL_MS) +

                    ') || (currentPage == 1 && utcTime >= ' + str(now_ms + HISTORY_INTERVAL_MS) + '))}')

    tick['commands'][0]['arguments'] = ['auto_refresh', expires_at, '${currentPage}']

    if dev_text:
        document['mainTemplate']['items'][0]['items'].append({
            'type': 'Text', 'text': 'DEV Â· 1.1.0 (Build 1611.8)',
            'fontSize': '1.8vh', 'color': '#8FA8BC', 'maxLines': 1,
            'position': 'absolute', 'right': '1vw', 'bottom': '0.5vh',
            'textAlign': 'right'})
        # Relative time is independent of device/server wall-clock differences.
        # A failed read retains this document and retries at most once a minute.
        tick['when'] = ('${displayState != "hidden" && elapsedTime >= '
                        '(currentPage == 1 ? ' + str(HISTORY_INTERVAL_MS) + ' : '
                        + str(REFRESH_INTERVAL_MS) + ')}')
        tick['commands'][0]['arguments'] = [
            'solar.fullscreen.text.auto.v1', expires_at, '${currentPage == 1 ? 1 : 0}']
        tick['commands'][0]['sequencer'] = 'solarDevFullscreenRefresh'
        pager = document['mainTemplate']['items'][0]['items'][0]
        pager['onPageChanged'][0]['value'] = '${event.source.page == 1 || event.source.value == 1 ? 1 : 0}' 
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

                 {'name':'lastDashboardRefresh','value':0}, {'name':'lastHistoryRefresh','value':0}],

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

    import uuid
    render_nonce = uuid.uuid4().hex
    root = result['response']['directives'][0]['document']['mainTemplate']['items'][0]

    base = grant['base_url'].replace('/dashboard.png?', '/tile.png?', 1)

    lifetime = grant['expires_in'] * 1000

    root['bind'] += [{'name': 'tileImageBase', 'value': base}, {'name': 'tileRenderNonce', 'value': render_nonce}, {'name': 'tileImageLoads', 'value': 0}]

    pages, timer = [], []

    for page_index, page_name in enumerate(('live', 'history')):
        clock = 'lastDashboardRefresh' if page_name == 'live' else 'lastHistoryRefresh'
        interval = REFRESH_INTERVAL_MS if page_name == 'live' else HISTORY_INTERVAL_MS

        refresh, rows = [], []

        for row in range(2):

            cards = []

            for col, label in enumerate(('Solar', 'Haus', 'Netz', 'Akku')):

                image_id = 'tile_' + page_name + '_' + str(row) + '_' + str(col)

                suffix = '&page=' + page_name + '&row=' + str(row) + '&col=' + str(col)

                command = {'type': 'SetValue', 'componentId': image_id, 'property': 'source',

                           'value': '${tileImageBase + "' + suffix + '&layout=final&n=" + tileRenderNonce + "-" + elapsedTime}'}

                refresh.append(command)

                cards.append({'type': 'Frame', 'width': '23vw', 'height': '100%',

                    'backgroundColor': '#172330', 'borderRadius': '14dp',

                    'borderColor': '#2D3D4B', 'borderWidth': '1dp',

                    'item': {'type': 'Container', 'paddingLeft': '1.5vw', 'paddingRight': '1vw',

                             'paddingTop': '2vh', 'items': [text(label, '3.4vh', '#AFC1D1'),

                        {'type': 'Image', 'id': image_id, 'width': '20.5vw', 'height': '19.25vh', 'spacing': '1vh',

                         'scale': 'best-fit', 'align': 'top-left', 'source': base + suffix + '&layout=final&n=' + render_nonce,

                         'onLoad': [{'type': 'SetValue', 'componentId': 'solarRoot',

                                     'property': 'imageFailed', 'value': False},

                                    {'type': 'SetValue', 'componentId': 'solarRoot',

                                     'property': 'tileImageLoads', 'value': '${tileImageLoads + 1}'}],

                         'onFail': [{'type': 'SetValue', 'componentId': 'solarRoot',

                                     'property': 'imageFailed', 'value': True}]}]}})

            heading = ('LIVE' if row == 0 else 'HEUTE - seit Mitternacht') if page_index == 0 else ('MONAT' if row == 0 else 'JAHR')

            rows += [text(heading, '3vh', '#8FA8BC', spacing='1vh' if row == 0 else '2vh'),

                     {'type': 'Container', 'direction': 'row', 'height': '30vh', 'justifyContent': 'spaceBetween', 'spacing': '1vh', 'items': cards}]

        status_base = base.replace('/tile.png?', '/status.png?', 1) + '&page=' + page_name

        status_id = 'sharedStatus' + page_name

        refresh.append({'type': 'SetValue', 'componentId': status_id, 'property': 'source',

                        'value': '${"' + status_base + '&n=" + tileRenderNonce + "-" + elapsedTime}'})

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

                 'align': 'left', 'spacing': '2vh', 'source': status_base + '&n=' + render_nonce},

                text('1/2 - Nach rechts wischen: Monat/Jahr' if page_index == 0 else '2/2 - Nach links wischen: Live/Heute',

                     '2.3vh', '#8FA8BC', spacing='1vh')]})

        due = ('${displayState == "foreground" && currentPage == ' + str(page_index) +
               ' && elapsedTime < ' + str(lifetime) +
               ' && (elapsedTime - ' + clock + ' >= ' + str(interval) +
               ' || (imageFailed && elapsedTime - ' + clock + ' >= 10000))}')
        timer.extend(dict(step, when=due) for step in refresh)
        timer.append({'type': 'SetValue', 'componentId': 'solarRoot', 'property': clock,
                      'value': '${elapsedTime}', 'when': due})
    root['items'][0]['height'] = '100vh'
    root['items'][0]['items'] = pages
    timer += [
        {'type': 'SetValue', 'componentId': 'solarRoot', 'property': 'imageFailed',

         'value': True, 'when': '${elapsedTime >= ' + str(lifetime) + '}'}]

    root['handleTick'][-1]['commands'] = timer
    document = result['response']['directives'][0]['document']
    document['onDisplayStateChange'] = [{'type': 'SetValue', 'componentId': 'solarRoot', 'property': 'lastDashboardRefresh', 'value': -60000, 'when': '${event.displayState == "foreground"}'}]

    return result






def lambda_handler(event, context):

    request=event.get('request',{})

    kind,intent=request.get('type'),request.get('intent',{}).get('name')

    access=image_access_token(event)

    if kind=='Alexa.Presentation.APL.UserEvent':

        return {'version':'1.0','response':{}}

    if kind=='IntentRequest' and (intent in SPOKEN_METRICS or intent=='StatusIntent'):

        if not access:

            return {'version':'1.0','response':{'card':{'type':'LinkAccount'},

                'outputSpeech':{'type':'PlainText','text':'Bitte verbinde deine Anlage in der Alexa-App mit Solaranlage.'},'shouldEndSession':True}}

        try:

            pv=read_pv(RELAY_URL,access)
            speech=spoken_status(pv) if intent=='StatusIntent' else spoken_reading(pv,intent)

        except Exception:

            speech='Die Live-Werte sind gerade nicht verfÃ¼gbar.'

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

        return live_image_document(message='Die Live-Werte sind gerade nicht verfÃ¼gbar. Bitte Solaranlage spÃ¤ter erneut Ã¶ffnen.')

    return house_image_pilot(live_image_document(grant=grant),grant)



"""Spoken status for the isolated test skill; uses validated relay readings."""

STATUS_METRICS = (
    ('power_w', 'Leistung inklusive Balkonkraftwerk', 'power'),
    ('home_w', 'Hausverbrauch', 'power'),
    ('battery_soc', 'Akkustand', 'percent'),
    ('today_pv_kwh', 'Heutige Produktion inklusive Balkonkraftwerk', 'energy'),
    ('grid_import_w', 'Netzbezug', 'power'),
    ('grid_export_w', 'Einspeisung', 'power'),
)


def spoken_status_age(age):
    if type(age) is not int or age < 0:
        return 'Das Alter der Werte ist nicht bekannt.'
    remaining = age
    parts = []
    for seconds, singular, plural in ((86400, 'Tag', 'Tage'),
            (3600, 'Stunde', 'Stunden'), (60, 'Minute', 'Minuten'),
            (1, 'Sekunde', 'Sekunden')):
        count, remaining = divmod(remaining, seconds)
        if count:
            parts.append(str(count) + ' ' + (singular if count == 1 else plural))
    duration = ' und '.join(parts) if parts else '0 Sekunden'
    return 'Die Werte sind ' + duration + ' alt.'


def spoken_status(pv):
    metrics = pv.get('metrics', {})
    sentences = ['Achtung, die Daten sind veraltet. Zuletzt gemeldeter Status.'
                 if pv.get('stale', True) else 'Status der Solaranlage.']
    for key, label, kind in STATUS_METRICS:
        value = metrics.get(key)
        if value is None:
            sentences.append(label + ': keine Daten vorhanden.')
            continue
        if kind == 'energy':
            formatted = number(value, 'Kilowattstunden')
        elif kind == 'percent':
            formatted = number(value, 'Prozent', 0)
        elif value >= 1000:
            formatted = number(value / 1000, 'Kilowatt')
        else:
            formatted = number(value, 'Watt', 0)
        sentences.append(label + ': ' + formatted + '.')
    sentences.append(spoken_status_age(pv.get('ageSeconds')))
    return ' '.join(sentences)


dashboard_handler = lambda_handler

"""Explicit widget tap routing, to wrap the unchanged v1.0.6 handler."""
from copy import deepcopy

OPEN = 'solar.widget.open.v1'


def route_widget(event, context, dashboard_handler, registration_handler=None):
    request = event.get('request', {})
    kind = request.get('type', '')
    package = request.get('payload', {}).get('packageId') or request.get('packageId')
    lifecycle = {'Alexa.DataStore.PackageManager.UsagesInstalled': 'install',
                 'Alexa.DataStore.PackageManager.UpdateRequest': 'install',
                 'Alexa.DataStore.PackageManager.UsagesRemoved': 'remove'}
    if kind in lifecycle and package in ('SolarWidget', 'SolarWidgetLive'):
        if registration_handler:
            access = event.get('context', {}).get('System', {}).get('user', {}).get('accessToken')
            if lifecycle[kind] == 'remove' or access:
                registration_handler(event, lifecycle[kind])
        return {'version': '1.0', 'response': {'shouldEndSession': True}}
    if (request.get('type') == 'Alexa.Presentation.APL.UserEvent'
            and request.get('arguments') == [OPEN]):
        if registration_handler and event.get('context', {}).get('System', {}).get('user', {}).get('accessToken'):
            try:
                registration_handler(event, 'install')
            except Exception:
                # Registration failure must never prevent opening the existing dashboard.
                pass
        launch = deepcopy(event)
        launch['request'] = {**request, 'type': 'LaunchRequest'}
        launch['request'].pop('arguments', None)
        return dashboard_handler(launch, context)
    return dashboard_handler(event, context)



def register_widget(event, action):
    config = image_config()
    if config.get('widget_registration_url') != 'https://solaranlage-widget.kulmi84.workers.dev/registrations':
        raise ValueError('Widget publisher not configured')
    system = event.get('context', {}).get('System', {})
    payload = {'action': action, 'user': system.get('user', {}).get('userId'),
               'device': system.get('device', {}).get('deviceId')}
    if action == 'install':
        payload['access'] = image_access_token(event)
    request = Request(config['widget_registration_url'], data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'User-Agent': 'Solaranlage-Widget/1.0',
                 'Authorization': 'Bearer ' + config['widget_registration_key']})
    with build_opener(NoImageRedirect()).open(request, timeout=2) as response:
        if response.status != 200:
            raise ValueError('Widget registration failed')

def lambda_handler(event, context):
    return route_widget(event, context, dashboard_handler, register_widget)


# Temporary widget-only diagnostics: never log tokens, identities or measurements.
_widget_handler_before_diagnostics = lambda_handler

def lambda_handler(event, context):
    request = event.get('request', {})
    kind = request.get('type', '')
    if kind.startswith('Alexa.DataStore.'):
        error = request.get('error', {})
        error_type = error.get('type', '')
        allowed = {'STORAGE_LIMIT_EXCEEDED', 'DATASTORE_INTERNAL_ERROR',
                   'DEVICE_UNAVAILABLE', 'DEVICE_PERMANENTLY_UNAVAILABLE'}
        print(json.dumps({'widgetDiagnostic': 1, 'requestType': kind[:100],
              'errorType': error_type if error_type in allowed else 'NONE_OR_OTHER'}))
        if kind in ('Alexa.DataStore.Error', 'Alexa.DataStore.DataStoreError'):
            return {'version': '1.0', 'response': {'shouldEndSession': True}}
    return _widget_handler_before_diagnostics(event, context)


widget_account_next_handler = lambda_handler

"""Silent per-instance widget initialization using normal account linking.

Appended to the existing deployed handler. Fullscreen functions stay unchanged.
"""
import copy
import re

WIDGET_ACCOUNT_EVENT='solar.widget.images.v1'
WIDGET_ACCOUNT_SKILL='amzn1.ask.skill.ac1da0c3-87cc-416e-a898-54033b6f0551'
WIDGET_ACCOUNT_PACKAGES=('SolarImageStatus102', 'SolarImageLive112', 'SolarImageCheck114', 'SolarRecovery20261029', 'SolarImageSharedAccount', 'SolarPrivateImage130')


def route_widget_account(event, context, handler, session_factory, config_factory, access_factory):
    request=event.get('request',{})
    arguments=request.get('arguments',[])
    handshake=(isinstance(arguments,list) and len(arguments)==2 and arguments[0]==WIDGET_ACCOUNT_EVENT and isinstance(arguments[1],dict) and set(arguments[1])=={'targetUid'} and isinstance(arguments[1]['targetUid'],str) and re.fullmatch(r':[0-9]{1,16}',arguments[1]['targetUid']))
    ready=(arguments==['solar.widget.images.ready.v1',{'version':'1.2.0','complete':True}])
    applied=(isinstance(arguments,list) and len(arguments)==2 and arguments[0]=='solar.widget.images.applied.v1' and isinstance(arguments[1],dict) and set(arguments[1])=={'grantReady','hasImage'} and all(v is None or type(v) is bool for v in arguments[1].values()))
    diagnostic_system=event.get('context',{}).get('System',{})
    diagnostic_uri=request.get('presentationUri','')
    diagnostic_payload=request.get('payload')
    diagnostic_payload=diagnostic_payload if isinstance(diagnostic_payload,dict) else {}
    diagnostic_source=request.get('source')
    diagnostic_source=diagnostic_source if isinstance(diagnostic_source,dict) else {}
    diagnostic_package=diagnostic_payload.get('packageId') or request.get('packageId')
    diagnostic_shared=(diagnostic_system.get('application',{}).get('applicationId')==WIDGET_ACCOUNT_SKILL
        and ((isinstance(diagnostic_uri,str) and '/SolarImageSharedAccount/' in diagnostic_uri)
             or diagnostic_package=='SolarImageSharedAccount'))
    if diagnostic_shared and not ready and not applied:
        kinds={'Alexa.Presentation.APL.UserEvent','Alexa.DataStore.PackageManager.UsagesInstalled',
               'Alexa.DataStore.PackageManager.UpdateRequest','Alexa.DataStore.PackageManager.UsagesRemoved'}
        print('WIDGET_SHARED_DIAG '+json.dumps({
            'kind':request.get('type') if request.get('type') in kinds else 'OTHER',
            'arguments':'UID' if handshake else ('LEGACY' if arguments==[WIDGET_ACCOUNT_EVENT]
                else ('OPEN' if arguments==['solar.widget.open.v1'] else 'OTHER')),
            'source':diagnostic_source.get('handler') if diagnostic_source.get('handler')
                in ('Mount','Tick','Press') else 'OTHER',
            'uriSegments':min(20,len(diagnostic_uri.split('/'))) if isinstance(diagnostic_uri,str) else 0,
        },sort_keys=True))
    if request.get('type')!='Alexa.Presentation.APL.UserEvent' or (arguments not in ([WIDGET_ACCOUNT_EVENT], ['solar.widget.open.v1']) and not handshake and not ready and not applied):
        return handler(event,context)
    system=event.get('context',{}).get('System',{})
    uri=request.get('presentationUri','')
    packages='|'.join(re.escape(p) for p in WIDGET_ACCOUNT_PACKAGES)
    pattern=r'widget://'+re.escape(WIDGET_ACCOUNT_SKILL)+r'(?:_development)?/(?:'+packages+r')/[A-Za-z0-9_.:-]{1,300}'
    response={'shouldEndSession':True}
    if system.get('application',{}).get('applicationId')!=WIDGET_ACCOUNT_SKILL or not re.fullmatch(pattern,uri):
        return {'version':'1.0','response':response}
    if applied:
        if diagnostic_shared:
            print('WIDGET_SHARED_APPLIED '+json.dumps(arguments[1],sort_keys=True))
        return {'version':'1.0','response':response}
    if ready:
        if '/SolarImageSharedAccount/' in uri:
            print('WIDGET_SHARED_FRAME_READY 1.2.0')
        return {'version':'1.0','response':response}
    if request.get('arguments')==['solar.widget.open.v1']:
        launch=copy.deepcopy(event)
        launch['request']={**request,'type':'LaunchRequest'}
        launch['request'].pop('arguments',None)
        return handler(launch,context)
    target=arguments[1]['targetUid'] if handshake else 'imageWidget'
    commands=[]
    access=access_factory(event)
    if diagnostic_shared:
        print('WIDGET_SHARED_ACCESS '+('present' if access else 'missing'))
    if not access:
        commands=[{'type':'SetValue','componentId':target,'property':'accountMessage',
                   'value':'Bitte Solaranlage in der Alexa-App verknÃ¼pfen.'}]
    else:
        try:
            grant=session_factory(access,config_factory())
            base=grant['base_url']
            prefix='https://solaranlage-display.kulmi84.workers.dev/dashboard.png?s='
            if not base.startswith(prefix) or not re.fullmatch(r'[A-Za-z0-9_-]{40,1000}',base[len(prefix):]):
                raise ValueError('Invalid image grant')
            lifetime=grant.get('expires_in')
            if type(lifetime) is not int or not 60<=lifetime<=86400:
                raise ValueError('Invalid image lifetime')
            origin='https://solaranlage-display.kulmi84.workers.dev/widget/'
            token=base[len(prefix):]
            values=[('imageBase',origin+'value.png?s='+token),
                    ('statusImageBase',origin+'status.png?s='+token),
                    ('grantReady',True),('accountMessage',''),
                    ('grantRefreshAt','${elapsedTime + '+str(max(30000,min(43200000,lifetime*1000-30000)))+'}'),
                    ('imageNonce','${elapsedTime}')]
            commands=[{'type':'SetValue','componentId':target,'property':name,'value':value} for name,value in values]
            if diagnostic_shared:
                print('WIDGET_SHARED_GRANT issued')
        except Exception:
            if diagnostic_shared:
                print('WIDGET_SHARED_GRANT error')
            # Keep last URLs/values through transient errors. Do not log the grant.
            commands=[{'type':'SetValue','componentId':target,'property':'accountMessage',
                       'value':'Verbindung wird erneut versucht.'}]
    if diagnostic_shared and handshake:
        commands=[{'type':'Sequential','sequencer':'widgetAccountReply','commands':commands+[
            {'type':'SendEvent','componentId':target,'flags':{'interactionMode':'INLINE'},
             'arguments':['solar.widget.images.applied.v1',{'grantReady':'${grantReady}','hasImage':'${hasImage}'}]}]}]
    reply_uri=uri
    if diagnostic_shared and handshake:
        reply_uri=uri.replace('widget://'+WIDGET_ACCOUNT_SKILL+'_development/', 'widget://'+WIDGET_ACCOUNT_SKILL+'/', 1)
    response['directives']=[{'type':'Alexa.Presentation.APL.ExecuteCommands','presentationUri':reply_uri,'commands':commands}]
    return {'version':'1.0','response':response}






def lambda_handler(event, context):
    observe_widget_context(event)
    return route_widget_account(event, context, widget_account_next_handler, create_image_session, image_config, image_access_token)

"""Log only comparisons for the shared widget; never log request values."""
def observe_widget_context(event):
    try:
        request = event.get('request', {})
        context = event.get('context', {})
        system = context.get('System', {})
        uri = request.get('presentationUri')
        if (system.get('application', {}).get('applicationId') != WIDGET_ACCOUNT_SKILL
                or request.get('type') != 'Alexa.Presentation.APL.UserEvent'
                or not isinstance(uri, str)
                or not re.fullmatch(r'widget://' + re.escape(WIDGET_ACCOUNT_SKILL)
                    + r'(?:_development)?/SolarImageSharedAccount/[A-Za-z0-9_.:-]{1,300}', uri)):
            return
        presentation = context.get('Alexa.Presentation', {})
        contexts = presentation.get('contexts', []) if isinstance(presentation, dict) else []
        contexts = contexts if isinstance(contexts, list) else []
        visible = [c for c in contexts[:50] if isinstance(c, dict)
                   and isinstance(c.get('presentationUri'), str)]
        direct = context.get('Alexa.Presentation.APL', {})
        direct = direct if isinstance(direct, dict) else {}
        args = request.get('arguments')
        uid = args[1].get('targetUid') if (isinstance(args, list) and len(args) == 2
                and isinstance(args[1], dict)) else None
        source = request.get('source', {})
        source = source if isinstance(source, dict) else {}
        runtime = system.get('device', {}).get('supportedInterfaces', {}).get(
            'Alexa.Presentation.APL', {}).get('runtime', {}).get('maxVersion')
        # Only booleans/counts and a finite, documented version enum leave the request.
        report = {
            'visibleWidgetCount': min(50, len(visible)),
            'requestUriInVisibleContext': any(c['presentationUri'] == uri for c in visible),
            'stageOnlyDifference': any(c['presentationUri'] != uri and
                c['presentationUri'].replace(WIDGET_ACCOUNT_SKILL + '_development/', WIDGET_ACCOUNT_SKILL + '/')
                == uri.replace(WIDGET_ACCOUNT_SKILL + '_development/', WIDGET_ACCOUNT_SKILL + '/') for c in visible),
            'directAplContextPresent': bool(direct),
            'sourceIsAuthoredRoot': source.get('id') == 'imageWidget',
            'sourceUidReported': isinstance(source.get('uid'), str),
            'sourceUidMatchesArgument': isinstance(uid, str) and source.get('uid') == uid,
            'runtime': runtime if runtime in ('1.6', '1.7', '1.8', '1.9', '2022.1', '2022.2',
                '2023.1', '2023.2', '2023.3', '2024.1', '2024.2', '2024.3') else 'OTHER_OR_MISSING'
        }
        print('WIDGET_SHARED_CONTEXT ' + json.dumps(report, sort_keys=True))
    except Exception:
        # Optional observation must not alter routing or prevent the normal response.
        return

"""Bounded Data Store publisher for a single current widget device."""
import json
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler

class NoPublisherRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def publish_image_access(device, commands, credentials, http_open=None, *, scope=("SolarAccountImagesV3", "access")):
    if not isinstance(device,str) or not device.startswith("amzn1.ask.device."):
        raise ValueError("Invalid device")
    if (len(commands)!=1 or commands[0].get("type")!="PUT_OBJECT"
            or (commands[0].get("namespace"), commands[0].get("key")) != scope):
        raise ValueError("Unexpected write scope")
    open_request=http_open or build_opener(NoPublisherRedirect()).open
    payload=urlencode({"grant_type":"client_credentials",
                       "client_id":credentials["ALEXA_CLIENT_ID"],
                       "client_secret":credentials["ALEXA_CLIENT_SECRET"],
                       "scope":"alexa::datastore"}).encode()
    req=Request("https://api.amazon.com/auth/o2/token",data=payload,method="POST",
                headers={"Content-Type":"application/x-www-form-urlencoded"})
    with open_request(req,timeout=4) as response:
        raw=response.read(16385)
    if len(raw)>16384:raise ValueError("Oversize auth response")
    token=json.loads(raw)["access_token"]
    body={"commands":commands,"target":{"type":"DEVICES","items":[device]}}
    req=Request("https://api.eu.amazonalexa.com/v1/datastore/commands",
                data=json.dumps(body).encode(),method="POST",
                headers={"Content-Type":"application/json","Authorization":"Bearer "+token})
    with open_request(req,timeout=4) as response:
        raw=response.read(16385)
        status=response.status
    if len(raw)>16384:raise ValueError("Oversize write response")
    rows=json.loads(raw).get("results",[])
    if status!=200 or len(rows)!=1 or rows[0].get("deviceId")!=device or rows[0].get("type")!="SUCCESS":
        raise ValueError("Write not confirmed")
    return True

"""Account-neutral Data Store image bootstrap; no credentials embedded."""
import copy
import re

NAMESPACE = "SolarAccountImagesV3"
KEY = "access"

# Diagnostic-session-only opaque tags correlate concurrent Lambda workers.
# The key has no access permissions and is never logged or published.
import hashlib as _diag_hashlib
import hmac as _diag_hmac
_DIAG_CORRELATION_KEY = bytes.fromhex("00" * 32)  # Public example; configure a private diagnostic salt when needed.

def widget_diagnostic_group(device, uri):
    if not isinstance(device, str) or not device.startswith("amzn1.ask.device."):
        return "UNAVAILABLE"
    payload = json.dumps([device, uri], separators=(",", ":")).encode("utf-8")
    return "W" + _diag_hmac.new(_DIAG_CORRELATION_KEY, payload, _diag_hashlib.sha256).hexdigest()[:16]

def widget_target_diagnostics(event, target_uid):
    request = event.get("request", {})
    source = request.get("source", {})
    source = source if isinstance(source, dict) else {}
    roots = []
    context = event.get("context", {})
    direct = context.get("Alexa.Presentation.APL", {})
    if isinstance(direct, dict):
        direct_roots = direct.get("componentsVisibleOnScreen", [])
        if isinstance(direct_roots, list):
            roots.extend(direct_roots[:256])
    presentation = context.get("Alexa.Presentation", {})
    if isinstance(presentation, dict):
        contexts = presentation.get("contexts", [])
        contexts = contexts if isinstance(contexts, list) else []
        for item in contexts[:32]:
            if isinstance(item, dict):
                visible = item.get("componentsVisibleOnScreen", [])
                if isinstance(visible, list):
                    roots.extend(visible[:256])
    own_roots = []
    examined = 0
    while roots and examined < 256:
        item = roots.pop()
        examined += 1
        if not isinstance(item, dict):
            continue
        if item.get("id") == "imageWidget":
            own_roots.append(item.get("uid"))
        children = item.get("children", [])
        if isinstance(children, list):
            roots.extend(children[:256])
    return {"sourceIsAuthoredRoot": source.get("id") == "imageWidget",
            "sourceUidPresent": isinstance(source.get("uid"), str),
            "targetMatchesSourceUid": source.get("uid") == target_uid,
            "visualRootPresent": bool(own_roots),
            "targetMatchesVisualRoot": target_uid in own_roots,
            "sourceHandler": source.get("handler") if source.get("handler") in ("Mount", "Tick", "Press") else "OTHER",
            **widget_uri_context_diagnostics(event)}

def widget_uri_context_diagnostics(event):
    request = event.get("request", {})
    uri = request.get("presentationUri", "")
    context = event.get("context", {})
    presentation = context.get("Alexa.Presentation", {})
    contexts = presentation.get("contexts", []) if isinstance(presentation, dict) else []
    contexts = contexts if isinstance(contexts, list) else []
    uris = [item.get("presentationUri") for item in contexts[:32]
            if isinstance(item, dict) and isinstance(item.get("presentationUri"), str)]
    direct = context.get("Alexa.Presentation.APL", {})
    if isinstance(direct, dict) and isinstance(direct.get("presentationUri"), str):
        uris.append(direct["presentationUri"])
    normalized = uri.replace("_live/", "/", 1).replace("_development/", "/", 1) if isinstance(uri, str) else ""
    runtime = context.get("System", {}).get("device", {}).get("supportedInterfaces", {}).get("Alexa.Presentation.APL", {}).get("runtime", {}).get("maxVersion")
    return {"visiblePresentationCount": len(uris),
            "requestUriInVisualContext": uri in uris,
            "stageOnlyDifferenceInVisualContext": any(candidate != uri and candidate.replace("_live/", "/", 1).replace("_development/", "/", 1) == normalized for candidate in uris),
            "runtimeVersion": runtime if runtime in ("1.8", "1.9", "2022.1", "2022.2", "2023.1", "2023.2", "2023.3", "2024.1", "2024.2", "2024.3", "2025.1", "2025.2", "2025.3", "2026.1", "2026.2", "2026.3") else "OTHER_OR_MISSING"}


def direct_image_access_reply(uri, target_uid, content, diagnostic_group):
    # Target only the validated requesting widget instance and its root UID.
    values = [("imageBase", content["imageBase"]),
              ("statusImageBase", content["statusImageBase"]),
              ("grantRefreshAt", content["expiresAt"] - 30000),
              ("imageNonce", "${elapsedTime}"),
              ("accountMessage", ""), ("grantReady", True)]
    return {"version": "1.0", "response": {"shouldEndSession": True, "directives": [{
        "type": "Alexa.Presentation.APL.ExecuteCommands", "presentationUri": uri,
        "commands": [{"type": "SetValue", "componentId": "imageWidget",
                      "property": name, "value": value} for name, value in values]
                    + store_probe_reply(uri, diagnostic_group)["response"]["directives"][0]["commands"]
    }]}}

def store_probe_reply(uri, expected_group):
    # Constant receipt: no APL expressions or private values.
    return {"version": "1.0", "response": {"shouldEndSession": True, "directives": [{
        "type": "Alexa.Presentation.APL.ExecuteCommands", "presentationUri": uri,
        "commands": [{"type": "SendEvent", "sequencer": "widgetReceiptProbe",
            "flags": {"interactionMode": "INLINE"},
            "arguments": ["solar.widget.receipt.v1", expected_group]}]}]}}

def route_account_images(event, context, fallback, *, skill_id, package_id,
                         access_factory, config_factory, session_factory, publish):
    request = event.get("request", {})
    arguments = request.get("arguments", [])
    kind = request.get("type")
    lifecycle = kind in ("Alexa.DataStore.PackageManager.UsagesInstalled",
                         "Alexa.DataStore.PackageManager.UpdateRequest")
    if kind != "Alexa.Presentation.APL.UserEvent" and not lifecycle:
        if (event.get("context", {}).get("System", {}).get("application", {}).get("applicationId") == skill_id
                and request.get("type") in ("Alexa.Presentation.APL.RuntimeError", "Alexa.Presentation.APL.CommandExecutionError", "System.ExceptionEncountered")):
            error = request.get("error", {})
            error = error if isinstance(error, dict) else {}
            # Error text is classified locally and never logged: it may contain private URLs.
            raw_text = json.dumps(error, ensure_ascii=True)[:8000].lower()
            print("SOLAR_APL_ERROR " + json.dumps({
                "requestType": request["type"],
                "mentionsPresentation": "presentation" in raw_text,
                "mentionsComponent": "component" in raw_text,
                "mentionsSetValue": "setvalue" in raw_text,
                "mentionsUnsupported": "unsupported" in raw_text or "not supported" in raw_text,
                "mentionsNotFound": "not found" in raw_text or "notfound" in raw_text
            }, sort_keys=True))
        return fallback(event, context)
    bootstrap = (isinstance(arguments, list) and len(arguments) == 2
                 and arguments[0] == "solar.widget.images.v1"
                 and isinstance(arguments[1], dict)
                 and set(arguments[1]) == {"targetUid"}
                 and isinstance(arguments[1]["targetUid"], str)
                 and re.fullmatch(r":[0-9]{1,16}", arguments[1]["targetUid"]))
    opening = arguments == ["solar.widget.open.v1"]
    probe_fields = {"imageAccessPresent", "statusAccessPresent", "lifetimeValid", "extensionPresent",
                    "expressionControl", "viewportContextPresent"}
    probe = (isinstance(arguments, list) and len(arguments) == 2
             and arguments[0] == "solar.widget.store.probe.v1"
             and isinstance(arguments[1], dict)
             and set(arguments[1]) in (probe_fields, probe_fields | {"replyExpectedGroup"})
             and all(type(arguments[1][key]) is bool for key in probe_fields)
             and ("replyExpectedGroup" not in arguments[1]
                  or (isinstance(arguments[1]["replyExpectedGroup"], str)
                      and re.fullmatch(r"W[0-9a-f]{16}", arguments[1]["replyExpectedGroup"])) ))
    receipt = (isinstance(arguments, list) and len(arguments) == 2
               and arguments[0] == "solar.widget.receipt.v1"
               and isinstance(arguments[1], str)
               and re.fullmatch(r"W[0-9a-f]{16}", arguments[1]))
    if not lifecycle and not bootstrap and not opening and not probe and not receipt:
        return fallback(event, context)
    silent = {"version": "1.0", "response": {"shouldEndSession": True}}
    system = event.get("context", {}).get("System", {})
    uri = request.get("presentationUri", "")
    pattern = r"widget://" + re.escape(skill_id) + r"(?:_development|_live)?/" + re.escape(package_id) + r"/[A-Za-z0-9_.:-]{1,300}"
    app_matches = system.get("application", {}).get("applicationId") == skill_id
    uri_matches = isinstance(uri, str) and bool(re.fullmatch(pattern, uri))
    if lifecycle:
        event_package = (request.get("payload") or {}).get("packageId") if kind.endswith("UsagesInstalled") else request.get("packageId")
        uri_matches = package_id == "SolarAccountImageBuild1211" and event_package == package_id
    diagnostic_group = widget_diagnostic_group(system.get("device", {}).get("deviceId"), uri) if app_matches and uri_matches else 0
    # Deliberately exclude identifiers, token URLs, measurements and raw requests.
    try:
        parts = uri.split("/") if isinstance(uri, str) else []
        authority = parts[2] if len(parts) > 2 else ""
        stage = authority[len(skill_id):] if authority.startswith(skill_id) else "FOREIGN_OR_MISSING"
        if not re.fullmatch(r"[A-Za-z0-9_-]{0,40}", stage):
            stage = "OTHER_SHAPE"
        print("SOLAR_STORE_ROUTE " + json.dumps({
            "command": "RECEIPT" if receipt else ("PROBE" if probe else ("OPEN" if opening else "IMAGES")),
            "diagnosticGroup": diagnostic_group,
            "diagnosticDevice": widget_diagnostic_group(system.get("device", {}).get("deviceId"), "DEVICE_ONLY") if app_matches and uri_matches else "UNAVAILABLE",
            "diagnosticPresentation": widget_diagnostic_group("amzn1.ask.device.PRESENTATION_ONLY", uri) if app_matches and uri_matches else "UNAVAILABLE",
            "ownApplication": app_matches,
            "uriAccepted": uri_matches,
            "ownUriAuthority": authority.startswith(skill_id),
            "stageSuffix": stage,
            "packageMatches": len(parts) > 3 and parts[3] == package_id,
            "uriSegments": len(parts),
            "instanceShapeAccepted": len(parts) == 5 and bool(re.fullmatch(r"[A-Za-z0-9_.:-]{1,300}", parts[4]))
        }, sort_keys=True))
    except Exception:
        pass
    if not app_matches or not uri_matches:
        return silent
    if receipt:
        print("SOLAR_STORE_RECEIPT " + json.dumps({
            "diagnosticGroup": diagnostic_group,
            "returnedToSameInstance": arguments[1] == diagnostic_group
        }, sort_keys=True))
        return silent
    if probe:
        available = event.get("context", {}).get("Extensions", {}).get("available", {})
        report = dict(arguments[1])
        report["diagnosticGroup"] = diagnostic_group
        report["replyReturnedToSameInstance"] = arguments[1].get("replyExpectedGroup") == diagnostic_group
        report.update(widget_uri_context_diagnostics(event))
        report["requestAdvertisesDataStore"] = isinstance(available, dict) and "alexaext:datastore:10" in available
        print("SOLAR_STORE_READ " + json.dumps(report, sort_keys=True))
        return silent
    if opening:
        launch = copy.deepcopy(event)
        launch["request"] = {**request, "type": "LaunchRequest"}
        launch["request"].pop("arguments", None)
    def finish():
        if lifecycle:
            return silent
        return fallback(launch, context) if opening else store_probe_reply(uri, diagnostic_group)
    device = system.get("device", {}).get("deviceId", "")
    access = access_factory(event)
    print("SOLAR_STORE_ACCESS " + json.dumps({"diagnosticGroup": diagnostic_group, "present": bool(access)}, sort_keys=True))
    if not access or not isinstance(device, str) or not device.startswith("amzn1.ask.device."):
        return finish()
    try:
        issued_at = int(time.time() * 1000)
        grant = session_factory(access, config_factory())
        prefix = "https://solaranlage-display.kulmi84.workers.dev/dashboard.png?s="
        base = grant.get("base_url", "")
        lifetime = grant.get("expires_in")
        if (not isinstance(base, str) or not base.startswith(prefix)
                or not re.fullmatch(r"[A-Za-z0-9_-]{40,1000}", base[len(prefix):])
                or type(lifetime) is not int or not 60 <= lifetime <= 86400):
            return finish()
        token = base[len(prefix):]
        origin = "https://solaranlage-display.kulmi84.workers.dev/widget/"
        command = {"type": "PUT_OBJECT", "namespace": NAMESPACE, "key": KEY,
                   "content": {"imageBase": origin + "value.png?s=" + token,
                               "statusImageBase": origin + "status.png?s=" + token,
                               "expiresIn": lifetime,
                               "expiresAt": issued_at + lifetime * 1000}}
        direct_reply = None
        if bootstrap and package_id in ("SolarAccountImageBuild1011", "SolarAccountImageBuild1211"):
            target_uid = arguments[1]["targetUid"]
            target = widget_target_diagnostics(event, target_uid)
            if (target["requestUriInVisualContext"] and target["sourceIsAuthoredRoot"]
                    and target["targetMatchesVisualRoot"]):
                print("SOLAR_BUILD1011_DIRECT " + json.dumps({"diagnosticGroup": diagnostic_group}))
                direct_reply = direct_image_access_reply(uri, target_uid, command["content"], diagnostic_group)
                if package_id == "SolarAccountImageBuild1011":
                    return direct_reply

        # Seed the device as well as replying to the current presentation.
        try:
            publish(device, [command])
            print("SOLAR_STORE_PUBLISH " + json.dumps({"diagnosticGroup": diagnostic_group, "success": True}, sort_keys=True))
        except Exception as error:
            print("SOLAR_STORE_PUBLISH " + type(error).__name__)
        if direct_reply is not None:
            return direct_reply
        if bootstrap:
            # Same short-lived image grant, same recipient; bypass a missing local extension.
            source = request.get("source", {})
            source = source if isinstance(source, dict) else {}
            print("SOLAR_STORE_DIRECT " + json.dumps({
                "diagnosticGroup": diagnostic_group,
                **widget_target_diagnostics(event, arguments[1]["targetUid"])
            }, sort_keys=True))
            return store_probe_reply(uri, diagnostic_group)
    except Exception as error:
        # Only the exception class is safe; messages can contain private URLs.
        print("SOLAR_STORE_PUBLISH " + type(error).__name__)
        # No CLEAR or deletion on errors: preserve last valid stored access and visible frame.
        pass
    return finish()

_image_replacement_fallback = lambda_handler

def replacement_publish(device, commands):
    credentials=image_config()['widget_datastore_credentials']
    return publish_image_access(device,commands,credentials)

def lambda_handler(event, context):
    uri = event.get('request', {}).get('presentationUri', '')
    new_package = (re.fullmatch(
        r'widget://amzn1\.ask\.skill\.80aa6d64-52ed-487a-b427-73e545a715d0(?:_development|_live)?/(SolarAccountImageBuild1011|SolarAccountImageBuild1211)/[A-Za-z0-9_.:-]{1,300}', uri) if isinstance(uri, str) else None)
    request = event.get('request', {})
    kind = request.get('type')
    package_id = new_package.group(1) if new_package else 'SolarAccountImageV3'
    if kind in ('Alexa.DataStore.PackageManager.UsagesInstalled',
                'Alexa.DataStore.PackageManager.UpdateRequest'):
        package_id = 'SolarAccountImageBuild1211'
    return route_account_images(event,context,_image_replacement_fallback,
        skill_id='amzn1.ask.skill.80aa6d64-52ed-487a-b427-73e545a715d0',
        package_id=package_id,access_factory=image_access_token,
        config_factory=image_config,session_factory=create_image_session,
        publish=replacement_publish)


# Append to the verified Development lambda_function.py for the device test.
from decimal import Decimal, ROUND_HALF_UP
from hmac import compare_digest
from dateutil.tz import gettz

_before_direct_values = lambda_handler
_direct_event = "solar.widget.directValues.v1"
_direct_skill = "amzn1.ask.skill.80aa6d64-52ed-487a-b427-73e545a715d0"
_direct_silent = {"version": "1.0", "response": {"shouldEndSession": True}}


def direct_snapshot(data, now):
    stamp = datetime.fromisoformat(data["received_at"].replace("Z", "+00:00"))
    age = (now - stamp).total_seconds()
    if age < -60:
        raise ValueError("Invalid measurement timestamp")

    def number(key, maximum):
        value = data[key]
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= maximum:
            raise ValueError("Invalid measurement")
        return Decimal(str(value))

    def formatted(value, places):
        return format(value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP), "f").replace(".", ",")

    def power(key):
        value = number(key, 10000000)
        return formatted(value / 1000, 2) + " kW" if value >= 1000 else formatted(value, 0) + " W"

    stale = age > 180
    local_stamp = stamp.astimezone(gettz("Europe/Berlin"))
    return {"solar": power("power_w"), "home": power("home_w"),
            "battery": formatted(number("battery_soc", 100), 0) + " %",
            "stamp": ("Veraltet: " if stale else "Stand: ") + local_stamp.strftime("%d.%m.%y, %H:%M"),
            "sampleTime": int(stamp.timestamp() * 1000), "stale": stale}


def lambda_handler(event, context):
    request = event.get("request", {})
    args = request.get("arguments", [])
    opening = args == ["solar.widget.open.v1"]
    installed = (request.get("type") == "Alexa.DataStore.PackageManager.UsagesInstalled"
                 and (request.get("payload") or {}).get("packageId") in ("SolarDirectValuesDev1611R2", "SolarDirectValuesDev1611R4", "SolarDirectValuesDev1611R5"))
    if not installed and (request.get("type") != "Alexa.Presentation.APL.UserEvent"
                          or not isinstance(args, list) or (not opening and args[:1] != [_direct_event])):
        return _before_direct_values(event, context)
    trace = installed or args[:1] == [_direct_event]
    if opening:
        print("SOLAR_DIRECT_WIDGET action=open result=received")

    def reject(reason):
        if trace:
            print("SOLAR_DIRECT_WIDGET action=" + ("open" if opening else "refresh") + " result=" + reason)
        return _direct_silent

    if not opening and not installed and len(args) != 2:
        return reject("invalid_target_argument")
    system = event.get("context", {}).get("System", {})
    if system.get("application", {}).get("applicationId") != _direct_skill:
        return reject("application_mismatch")
    uri = request.get("presentationUri")
    try:
        config = image_config().get("direct_widget_test", {})
        package = config.get("package_id", "")
        expected = config.get("allowed_device_tag", "")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{1,63}", package) or not re.fullmatch(r"W[a-f0-9]{16}", expected):
            return _before_direct_values(event, context) if opening else reject("configuration_missing")
        pattern = r"widget://" + re.escape(_direct_skill + "_development/") + "(?:" + re.escape(package) + "|SolarDirectValuesDev1611R2|SolarDirectValuesDev1611R4|SolarDirectValuesDev1611R5)" + r"/[A-Za-z0-9_.:-]{1,300}"
        # Alexa can omit the stage suffix for a widget tap. Permit this
        # variant only for the current DEV package, never _live or a data read.
        dev_tap_without_suffix = (opening and isinstance(uri, str) and re.fullmatch(
            r"widget://" + re.escape(_direct_skill)
            + r"/SolarDirectValuesDev1611R5/[A-Za-z0-9_.:-]{1,300}", uri))
        if not installed and not dev_tap_without_suffix and (not isinstance(uri, str) or not re.fullmatch(pattern, uri)):
            if opening:
                print("SOLAR_DIRECT_WIDGET action=open result=other_presentation")
                return _before_direct_values(event, context)
            return reject("presentation_mismatch")
        trace = True
        access = image_access_token(event)
        if not opening and (not isinstance(access, str) or not re.fullmatch(r"[a-f0-9]{64}", access)):
            return reject("linked_access_missing")
        device = system.get("device", {}).get("deviceId")
        if not isinstance(device, str) or not device.startswith("amzn1.ask.device."):
            return reject("device_missing")
        if not compare_digest(widget_diagnostic_group(device, "DEVICE_ONLY"), expected):
            return reject("device_mismatch")
        if opening:
            print("SOLAR_DIRECT_WIDGET action=open result=launch")
            launch = copy.deepcopy(event)
            launch["request"]["type"] = "LaunchRequest"
            launch["request"].pop("arguments")
            return _before_direct_values(launch, context)

        # The validated Development URI targets the instance; the authored
        # component ID is fixed here, never supplied by the event.
        relay_request = Request(RELAY_URL, headers={"Authorization": "Bearer " + access,
                                "Accept": "application/json", "User-Agent": "Solaranlage-DirectWidget-Test/1.0"})
        print("SOLAR_DIRECT_WIDGET relay_attempt=1")
        with urlopen(relay_request, timeout=3) as response:
            raw = response.read(4097)
        if len(raw) > 4096:
            raise ValueError("Response too large")
        snapshot = direct_snapshot(json.loads(raw), datetime.now(timezone.utc))
    except Exception:
        return reject("snapshot_unavailable")

    if installed or any("/" + pid + "/" in uri for pid in ("SolarDirectValuesDev1611R2", "SolarDirectValuesDev1611R4", "SolarDirectValuesDev1611R5")):
        try:
            scope = ("SolarDirectValuesDev", "snapshot")
            publish_image_access(device, [{"type": "PUT_OBJECT", "namespace": scope[0],
                                          "key": scope[1], "content": snapshot}],
                                 image_config()["widget_datastore_credentials"], scope=scope)
            print("SOLAR_DIRECT_WIDGET action=refresh result=datastore_written")
        except Exception:
            print("SOLAR_DIRECT_WIDGET action=refresh result=datastore_write_failed")
        if installed:
            return _direct_silent

    print("SOLAR_DIRECT_WIDGET action=refresh result=response_created")
    return {"version": "1.0", "response": {"shouldEndSession": True, "directives": [{
        "type": "Alexa.Presentation.APL.ExecuteCommands", "presentationUri": uri,
        "commands": [{"type": "SetValue", "componentId": "imageWidget",
                      "property": "snapshot", "value": snapshot,
                      "when": "${!event.target.bind.snapshot.sampleTime || event.target.bind.snapshot.sampleTime <= "
                              + str(snapshot["sampleTime"]) + "}"}]
    }]}}







# The existing status utterance can seed the text widget using the linked
# household on the allowed Development device, independent of widget events.
_before_dev_status_seed = lambda_handler

def lambda_handler(event, context):
    request = event.get("request", {})
    if request.get("type") != "IntentRequest" or request.get("intent", {}).get("name") != "StatusIntent":
        return _before_dev_status_seed(event, context)
    system = event.get("context", {}).get("System", {})
    device = system.get("device", {}).get("deviceId")
    access = image_access_token(event)
    if (system.get("application", {}).get("applicationId") != _direct_skill
            or not isinstance(device, str) or not device.startswith("amzn1.ask.device.")
            or not isinstance(access, str) or not re.fullmatch(r"[a-f0-9]{64}", access)):
        return _before_dev_status_seed(event, context)
    try:
        cfg = image_config()
        allowed = cfg.get("direct_widget_test", {}).get("allowed_device_tag", "")
        if not compare_digest(widget_diagnostic_group(device, "DEVICE_ONLY"), allowed):
            return _before_dev_status_seed(event, context)
        relay_request = Request(RELAY_URL, headers={"Authorization": "Bearer " + access,
                                "Accept": "application/json", "User-Agent": "Solaranlage-DirectWidget-Test/1.0"})
        with urlopen(relay_request, timeout=2) as response:
            raw = response.read(4097)
        if len(raw) > 4096:
            raise ValueError("Response too large")
        snapshot = direct_snapshot(json.loads(raw), datetime.now(timezone.utc))
        scope = ("SolarDirectValuesDev", "snapshot")
        def bounded_open(request, timeout):
            return build_opener(NoPublisherRedirect()).open(request, timeout=min(timeout, 1.5))
        publish_image_access(device, [{"type": "PUT_OBJECT", "namespace": scope[0],
                                      "key": scope[1], "content": snapshot}],
                             cfg["widget_datastore_credentials"], bounded_open, scope=scope)
        print("SOLAR_DIRECT_WIDGET action=status result=datastore_written")
        speech = ("Solarleistung " + snapshot["solar"] + ". Hausverbrauch " + snapshot["home"]
                  + ". Akkustand " + snapshot["battery"] + ".")
    except Exception:
        print("SOLAR_DIRECT_WIDGET action=status result=unavailable")
        speech = "Die Live-Werte sind gerade nicht verfÃ¼gbar."
    return {"version": "1.0", "response": {"outputSpeech": {"type": "PlainText", "text": speech},
                                          "shouldEndSession": True}}


# DEV fullscreen experiment. Keep the image route available for other devices.
_before_fullscreen_text = lambda_handler

def lambda_handler(event, context):
    request = event.get("request", {})
    kind = request.get("type")
    args = request.get("arguments")
    command = args[0] if isinstance(args, list) and args else None
    refresh_commands = {"solar.fullscreen.text.refresh.v1": "refresh",
                        "solar.fullscreen.text.auto.v1": "auto_refresh"}
    refresh = kind == "Alexa.Presentation.APL.UserEvent" and isinstance(command, str) and command in refresh_commands
    opening = (kind == "Alexa.Presentation.APL.UserEvent"
               and args == ["solar.widget.open.v1"]
               and isinstance(request.get("presentationUri"), str)
               and re.fullmatch(r"widget://" + re.escape(_direct_skill)
                                + r"(?:_development)?/SolarDirectValuesDev1611R5/[A-Za-z0-9_.:-]{1,300}",
                                request["presentationUri"]))
    if kind != "LaunchRequest" and not refresh and not opening:
        return _before_fullscreen_text(event, context)
    system = event.get("context", {}).get("System", {})
    device = system.get("device", {}).get("deviceId", "")
    try:
        tag = image_config().get("direct_widget_test", {}).get("allowed_device_tag", "")
    except (OSError, ValueError):
        return _before_fullscreen_text(event, context)
    access = image_access_token(event)
    if (system.get("application", {}).get("applicationId") != _direct_skill
            or not isinstance(device, str) or not device.startswith("amzn1.ask.device.")
            or not dev_text_target_authorized(event)
            or "Alexa.Presentation.APL" not in system.get("device", {}).get("supportedInterfaces", {})
            or not isinstance(access, str) or not re.fullmatch(r"[a-f0-9]{64}", access)):
        return _before_fullscreen_text(event, context)
    if refresh:
        if request.get("token") != "solaranlage":
            return {"version": "1.0", "response": {"shouldEndSession": True}}
        event = {**event, "request": {**request, "arguments": [refresh_commands[command], *args[1:]]}}
    elif opening:
        event = {**event, "request": {**request, "type": "LaunchRequest"}}
    return native_handler(event, context, dev_text=True)


def dev_text_target_authorized(event, config=None):
    # This is request eligibility only. Actual authorization is performed
    # atomically with the data read by the household-scoped DEV relay.
    system = event.get("context", {}).get("System", {})
    access = image_access_token(event)
    device = system.get("device", {}).get("deviceId", "")
    return bool(system.get("application", {}).get("applicationId") == _direct_skill
                and isinstance(device, str) and device.startswith("amzn1.ask.device.")
                and isinstance(access, str) and re.fullmatch(r"[a-f0-9]{64}", access))


_before_dev_explicit_open = lambda_handler

def lambda_handler(event, context):
    request = event.get("request", {})
    if request.get("type") != "Alexa.Presentation.APL.UserEvent" or request.get("arguments") != ["solar.widget.text.open.v1"]:
        return _before_dev_explicit_open(event, context)
    system = event.get("context", {}).get("System", {})
    device = system.get("device", {}).get("deviceId", "")
    uri = request.get("presentationUri", "")
    if system.get("application", {}).get("applicationId") != _direct_skill:
        return _direct_silent
    if not isinstance(uri, str) or not re.fullmatch(
            r"widget://" + re.escape(_direct_skill)
            + r"(?:_development)?/SolarDirectValuesDev1611R7/[A-Za-z0-9_.:-]{1,300}", uri):
        print("SOLAR_DEV_OPEN rejected=presentation")
        return _direct_silent
    try:
        if not dev_text_target_authorized(event):
            print("SOLAR_DEV_OPEN rejected=target")
            return _direct_silent
    except (OSError, ValueError):
        return _direct_silent
    launch = {**event, "request": {**request, "type": "LaunchRequest"}}
    launch["request"].pop("arguments", None)
    print("SOLAR_DEV_OPEN result=text_fullscreen")
    return native_handler(launch, context, dev_text=True)

# Restricted DEV routing telemetry: classifications only, never identifiers or readings.
_before_dev_route_trace = lambda_handler

def lambda_handler(event, context):
    request = event.get("request", {})
    kind = request.get("type", "")
    if kind not in ("Alexa.Presentation.APL.UserEvent", "LaunchRequest", "SessionEndedRequest"):
        return _before_dev_route_trace(event, context)
    system = event.get("context", {}).get("System", {})
    session = event.get("session", {})
    args = request.get("arguments", [])
    command = args[0] if isinstance(args, list) and args and isinstance(args[0], str) else ""
    known = {"solar.widget.text.open.v1": "text_open", "solar.widget.open.v1": "legacy_open",
             "solar.widget.directValues.v1": "direct_refresh", "solar.fullscreen.text.auto.v1": "fullscreen_auto",
             "solar.fullscreen.text.refresh.v1": "fullscreen_refresh"}
    uri = request.get("presentationUri")
    uri_class = "missing"
    if isinstance(uri, str):
        uri_class = "other"
        for suffix, label in (("_development", "development"), ("", "bare"), ("_live", "live")):
            if re.fullmatch(r"widget://" + re.escape(_direct_skill + suffix)
                           + r"/SolarDirectValuesDev1611R7/[A-Za-z0-9_.:-]{1,300}", uri):
                uri_class = label
                break
    try:
        expected = image_config().get("direct_widget_test", {}).get("allowed_device_tag", "")
        device = system.get("device", {}).get("deviceId", "")
        matches = bool(expected and isinstance(device, str) and
                       compare_digest(widget_diagnostic_group(device, "DEVICE_ONLY"), expected))
    except (OSError, ValueError):
        matches = False
    report = {"event": kind, "action": known.get(command, "other"),
              "contextApplicationMatches": system.get("application", {}).get("applicationId") == _direct_skill,
              "sessionApplicationMatches": session.get("application", {}).get("applicationId") == _direct_skill,
              "uri": uri_class, "deviceMatches": matches, "requestEligible": dev_text_target_authorized(event),
              "hasLinkedAccess": bool(image_access_token(event))}
    print("SOLAR_DEV_ROUTE " + json.dumps(report, sort_keys=True))
    result = _before_dev_route_trace(event, context)
    response = result.get("response", {}) if isinstance(result, dict) else {}
    directives = response.get("directives", [])
    print("SOLAR_DEV_ROUTE_RESULT " + json.dumps({
        "renderDocument": any(d.get("type") == "Alexa.Presentation.APL.RenderDocument" for d in directives),
        "linkAccount": response.get("card", {}).get("type") == "LinkAccount",
        "directiveCount": len(directives)}, sort_keys=True))
    return result
