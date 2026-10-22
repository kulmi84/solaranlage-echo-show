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


def display_handler(event, context):
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
                'Frage meine Solaranlage Test nach der aktuellen Leistung, dem Akkustand, dem aktuellen Verbrauch, der heutigen Gesamtproduktion oder der heutigen Einspeisung.'}}}
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
    pv = {'metrics': {}, 'valueText': '-', 'stale': True, 'statusText': 'Diagnosegeruest - keine Messwerte'}
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
                    text('Solaranlage Test', '5vh', fontWeight='700'),
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
        cards = [card('PV + BKW', n('pv'), 'kWh Â· Erzeugung', gold),
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
    tick = document['handleTick'][0]
    tick['when'] = ('${displayState == "foreground" && utcTime < ' + str(expires_at) +
                    ' && ((currentPage == 0 && utcTime >= ' + str(now_ms + REFRESH_INTERVAL_MS) +
                    ') || (currentPage == 1 && utcTime >= ' + str(now_ms + HISTORY_INTERVAL_MS) + '))}')
    tick['commands'][0]['arguments'] = ['auto_refresh', expires_at, '${currentPage}']
    document['mainTemplate']['items'][0]['handleTick'] = document.pop('handleTick')
    # Use elapsed time on the device, independent of server/device clock offset.
    root = document['mainTemplate']['items'][0]
    root['bind'].append({'name': 'refreshAttempts', 'value': 0})
    tick = root['handleTick'][0]
    tick['when'] = ('${displayState == "foreground" && (elapsedTime >= ' +
        str(max(1000, expires_at - now_ms)) + ' || ((currentPage == 0 && elapsedTime >= ' +
        str(REFRESH_INTERVAL_MS) + ') || (currentPage == 1 && elapsedTime >= ' +
        str(HISTORY_INTERVAL_MS) + ')))}')
    tick['commands'].insert(0, {'type': 'SetValue', 'componentId': 'solarRoot',
        'property': 'refreshAttempts', 'value': '${refreshAttempts + 1}'})
    # Evaluate due conditions in commands, not the handler's when property.
    root = document['mainTemplate']['items'][0]
    root['bind'].append({'name': 'refreshSent', 'value': False})
    tick = root['handleTick'][0]
    due = tick.pop('when')
    due = due[:-1] + ' && !refreshSent}'
    tick['minimumDelay'] = 1000
    for command in tick['commands']:
        command['when'] = due
    tick['commands'].append({'type': 'SetValue', 'componentId': 'solarRoot',
        'property': 'refreshSent', 'value': True, 'when': due})
    # Isolated image reload test: no household information in this endpoint.
    root = document['mainTemplate']['items'][0]
    image_base = 'https://solaranlage-image-test.kulmi84.workers.dev/clock.png?n='
    root['bind'].append({'name': 'imageLoads', 'value': 0})
    root['items'].append({'type': 'Image', 'id': 'imageProbe',
        'source': image_base + str(now_ms), 'width': '90vw', 'height': '20vh',
        'position': 'absolute', 'bottom': '9vh', 'left': '5vw', 'scale': 'best-fit',
        'onLoad': [{'type': 'SetValue', 'componentId': 'solarRoot',
                    'property': 'imageLoads', 'value': '${imageLoads + 1}'},
                   {'type': 'SetValue', 'componentId': 'imageProbeStatus', 'property': 'text',
                    'value': '${"Server-Uhrbild (UTC) | Geladen: " + imageLoads}'}],
        'onFail': [{'type': 'SetValue', 'componentId': 'imageProbeStatus', 'property': 'text',
                    'value': 'Uhrbild konnte nicht geladen werden'}]})
    root['items'].append({'type': 'Text', 'id': 'imageProbeStatus',
        'text': 'Server-Uhrbild wird geladen (keine Live-Daten)', 'fontSize': '2.5vh',
        'color': '#FFD166', 'position': 'absolute', 'bottom': '5vh', 'left': '2vw'})
    root['handleTick'].append({'minimumDelay': 10000, 'commands': [{
        'type': 'SetValue', 'componentId': 'imageProbe', 'property': 'source',
        'value': '${"' + image_base + '" + (' + str(now_ms) + ' + elapsedTime)}',
        'when': '${displayState == "foreground"}'}]})
    # Diagnostic only: local timer independent of foreground/SendEvent.
    root = document['mainTemplate']['items'][0]
    root['items'].append({'type': 'Text', 'id': 'tickProbe',
        'text': 'APL-Test: Timer wartet', 'fontSize': '2.4vh', 'color': '#FFD166',
        'position': 'absolute', 'bottom': 0, 'left': '2vw', 'width': '96vw'})
    root['handleTick'].append({'minimumDelay': 1000, 'commands': [{
        'type': 'SetValue', 'componentId': 'tickProbe', 'property': 'text',
        'value': '${"APL: " + displayState + " | Tick-ms: " + elapsedTime + " | Versuche: " + refreshAttempts}'}]})
    # Omit shouldEndSession: show APL without opening the microphone for a reply.
    # True would close the skill; False would request speech after every refresh.
    response = {'directives': [{'type': 'Alexa.Presentation.APL.RenderDocument', 'token': 'solaranlage', 'document': document}]}
    if speech:
        response['outputSpeech'] = {'type': 'PlainText', 'text': speech}
    return {'version': '1.0', 'response': response}


def lambda_handler(event, context):
    result = display_handler(event, context)
    # End voice interaction after rendering; do not Finish the APL document.
    # Apply the same rule to touch/tick updates so they cannot reopen voice.
    if event.get('request', {}).get('type') in ('LaunchRequest', 'Alexa.Presentation.APL.UserEvent'):
        response = result.get('response', {})
        if any(d.get('type') == 'Alexa.Presentation.APL.RenderDocument' for d in response.get('directives', [])):
            response['shouldEndSession'] = True
    # Deliberately log only routing metadata. Never log the request envelope,
    # slots, user/device IDs, access tokens, utterances, or raw session IDs.
    try:
        import hashlib
        request = event.get('request', {})
        session = event.get('session', {})
        response = result.get('response', {})
        kind = request.get('type', '')
        known_types = {'LaunchRequest', 'IntentRequest', 'SessionEndedRequest',
                       'Alexa.Presentation.APL.UserEvent'}
        intent = request.get('intent', {}).get('name', '')
        known_intents = set(SPOKEN_METRICS) | {'AMAZON.FallbackIntent',
            'AMAZON.HelpIntent', 'AMAZON.StopIntent', 'AMAZON.CancelIntent'}
        args = request.get('arguments', [])
        action = args[0] if isinstance(args, list) and args and args[0] in ('refresh', 'auto_refresh') else None
        reason = request.get('reason')
        record = {
            'build': 'image-probe-2026-10-20',
            'at_ms': int(time.time() * 1000),
            'request_type': kind if kind in known_types else 'OTHER',
            'intent': intent if intent in known_intents else None,
            'session_tag': hashlib.sha256(session['sessionId'].encode()).hexdigest()[:12] if session.get('sessionId') else None,
            'session_new': session.get('new') is True,
            'end_reason': reason if reason in ('USER_INITIATED', 'ERROR', 'EXCEEDED_MAX_REPROMPTS') else None,
            'apl_action': action,
            'end_session': response.get('shouldEndSession', 'unset'),
            'speech': bool(response.get('outputSpeech')),
            'render': any(d.get('type') == 'Alexa.Presentation.APL.RenderDocument' for d in response.get('directives', []))
        }
        print('SOLAR_DIAG ' + json.dumps(record, sort_keys=True), flush=True)
    except Exception:
        pass  # Diagnostics must never change the skill response.
    return result
