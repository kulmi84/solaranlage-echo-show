"""Native Solaranlage display: live power above today's energy totals."""
import json
import time
from pathlib import Path
from beta_live_reader import read_pv

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


def lambda_handler(event, context):
    request = event.get('request', {})
    intent = request.get('intent', {}).get('name', '')
    if request.get('type') == 'SessionEndedRequest':
        return {'version': '1.0', 'response': {}}
    if intent in ('AMAZON.StopIntent', 'AMAZON.CancelIntent'):
        return {'version': '1.0', 'response': {'shouldEndSession': True}}
    if intent == 'AMAZON.FallbackIntent':
        # Do not recite help for a general Alexa request caught by this session.
        return {'version': '1.0', 'response': {'shouldEndSession': True}}
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
    # Omit shouldEndSession: show APL without opening the microphone for a reply.
    # True would close the skill; False would request speech after every refresh.
    response = {'directives': [{'type': 'Alexa.Presentation.APL.RenderDocument', 'token': 'solaranlage', 'document': document}]}
    if speech:
        response['outputSpeech'] = {'type': 'PlainText', 'text': speech}
    return {'version': '1.0', 'response': response}
