"""Native Solaranlage display: live power above today's energy totals."""
import json
from pathlib import Path
from beta_live_reader import read_pv


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
    if request.get('type') == 'Alexa.Presentation.APL.UserEvent' and request.get('arguments') != ['refresh']:
        return {'version': '1.0', 'response': {}}
    try:
        config = json.loads(Path(__file__).with_name('relay_config.json').read_text())
        pv = read_pv(config['url'], config['read_token'])
    except Exception:
        pv = {'metrics': {}, 'valueText': '—', 'statusText': 'Keine aktuellen Daten · Verbindung prüfen', 'stale': True}
    m = pv.get('metrics', {})
    g = m.get
    interfaces = event.get('context', {}).get('System', {}).get('device', {}).get('supportedInterfaces', {})
    if 'Alexa.Presentation.APL' not in interfaces:
        return {'version': '1.0', 'response': {
            'outputSpeech': {'type': 'PlainText', 'text': 'Solaranlage. PV-Leistung: ' + pv['valueText'] + '. Hausverbrauch: ' + power(g('home_w')) + '. Akkustand: ' + number(g('battery_soc'), 'Prozent', 0) + '. ' + pv['statusText']},
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
    status = pv['statusText'] if pv['stale'] else 'Stand ' + pv.get('receivedText', '—') + ' Uhr · Messwerte jede Minute · Tageswerte aus HA-Statistik'
    document = {
        'type': 'APL', 'version': '1.6', 'theme': 'dark',
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
    return {'version': '1.0', 'response': {
        'directives': [{'type': 'Alexa.Presentation.APL.RenderDocument', 'token': 'solaranlage', 'document': document}],
        'shouldEndSession': False}}
