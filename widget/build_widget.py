"""Prepare the production widget without altering either deployed skill."""
import json
from pathlib import Path

ROOT = Path(__file__).parent
PACKAGE = ROOT / 'skill-package/dataStorePackages/SolarWidget'


def document():
    """Device-approved large transparent layout; production tap event only."""
    return {'type': 'APL',
     'version': '2023.3',
     'theme': 'dark',
     'extensions': [{'name': 'DataStore', 'uri': 'alexaext:datastore:10'}],
     'settings': {'DataStore': {'dataBindings': [{'namespace': 'Solar',
                                                  'key': 'live',
                                                  'dataBindingName': 'SolarLive',
                                                  'dataType': 'OBJECT'}]}},
     'mainTemplate': {'items': [{'type': 'TouchWrapper',
                                 'width': '100vw',
                                 'height': '100vh',
                                 'onPress': [{'type': 'SendEvent',
                                              'arguments': ['solar.widget.open.v1'],
                                              'flags': {'interactionMode': 'STANDARD'}}],
                                 'item': {'type': 'Frame',
                                          'width': '100vw',
                                          'height': '100vh',
                                          'backgroundColor': 'transparent',
                                          'borderColor': 'transparent',
                                          'borderWidth': 2,
                                          'borderRadius': 16,
                                          'item': {'type': 'Container',
                                                   'width': '100%',
                                                   'height': '100%',
                                                   'padding': 16,
                                                   'items': [{'type': 'Container',
                                                              'items': [{'type': 'Text',
                                                                         'text': 'Solaranlage',
                                                                         'fontSize': 26,
                                                                         'color': '#FFFFFF',
                                                                         'maxLines': 1,
                                                                         'fontWeight': '700'},
                                                                        {'type': 'Text',
                                                                         'text': 'LIVE',
                                                                         'fontSize': 16,
                                                                         'color': '#AFC1D1',
                                                                         'maxLines': 1,
                                                                         'spacing': 4}]},
                                                             {'type': 'Container',
                                                              'grow': 1,
                                                              'width': '100%',
                                                              'justifyContent': 'spaceAround',
                                                              'items': [{'type': 'Container',
                                                                         'items': [{'type': 'Text',
                                                                                    'text': 'PV + BKW',
                                                                                    'fontSize': 22,
                                                                                    'color': '#AFC1D1',
                                                                                    'maxLines': 1},
                                                                                   {'type': 'Text',
                                                                                    'text': '${SolarLive ? '
                                                                                            'SolarLive.production '
                                                                                            ": '�'}",
                                                                                    'fontSize': 48,
                                                                                    'color': '#FFD166',
                                                                                    'maxLines': 1,
                                                                                    'fontWeight': '700'}]},
                                                                        {'type': 'Container',
                                                                         'items': [{'type': 'Text',
                                                                                    'text': 'Hausverbrauch',
                                                                                    'fontSize': 22,
                                                                                    'color': '#AFC1D1',
                                                                                    'maxLines': 1},
                                                                                   {'type': 'Text',
                                                                                    'text': '${SolarLive ? '
                                                                                            'SolarLive.consumption '
                                                                                            ": '�'}",
                                                                                    'fontSize': 48,
                                                                                    'color': '#8BCBFF',
                                                                                    'maxLines': 1,
                                                                                    'fontWeight': '700'}]},
                                                                        {'type': 'Container',
                                                                         'items': [{'type': 'Text',
                                                                                    'text': 'Akku',
                                                                                    'fontSize': 22,
                                                                                    'color': '#AFC1D1',
                                                                                    'maxLines': 1},
                                                                                   {'type': 'Text',
                                                                                    'text': '${SolarLive ? '
                                                                                            'SolarLive.battery : '
                                                                                            "'�'}",
                                                                                    'fontSize': 48,
                                                                                    'color': '#51D3C5',
                                                                                    'maxLines': 1,
                                                                                    'fontWeight': '700'}]}]},
                                                             {'type': 'Container',
                                                              'items': [{'type': 'Text',
                                                                         'text': "${SolarLive.status ?? 'Warte "
                                                                                 "auf Live-Werte'}",
                                                                         'fontSize': 16,
                                                                         'color': '#FFD166',
                                                                         'maxLines': 1,
                                                                         'spacing': 16},
                                                                        {'type': 'Text',
                                                                         'text': "${SolarLive.stand ?? 'Noch "
                                                                                 "kein Empfang'}",
                                                                         'fontSize': 16,
                                                                         'color': '#AFC1D1',
                                                                         'maxLines': 2,
                                                                         'spacing': 12},
                                                                        {'type': 'Text',
                                                                         'text': 'Antippen: Vollbild �ffnen',
                                                                         'fontSize': 16,
                                                                         'color': '#8BCBFF',
                                                                         'maxLines': 1,
                                                                         'spacing': 6}]}]}}}]}}


def build():
    files = {'documents/document.json': document(), 'datasources/default.json': {},
             'presentations/default.tpl': dict(type='APL_PRESENTATION', documentUrl='documents/document.json', datasourceUrl='datasources/default.json'),
             'manifest.json': {'packageVersion':'1.0','packageType':'APL_PACKAGE',
                'manifest':{'id':'SolarWidget','version':'1.1.0','installStateChanges':'INFORM','updateStateChanges':'INFORM',
                    'presentationDefinitions':[{'url':'presentations/default.tpl'}],
                    'appliesTo':"${viewport.mode == 'HUB' && location == 'FAVORITE'}"},
                'publishingInformation':{'schemaVersion':'1.0','locales':{'de-DE':[{'targetViewport':'WIDGET_M','metadata':{
                    'name':'Solaranlage','description':'Sieh PV-Leistung, Hausverbrauch und Akkustand. Ein Tipp �ffnet die gro�e Solaranlagenanzeige.',
                    'keywords':['Solar','Photovoltaik','Home Assistant','PV','Akku'],
                    'iconUri':'https://solaranlage-widget.kulmi84.workers.dev/icon.png',
                    'previews':['https://solaranlage-widget.kulmi84.workers.dev/preview.png']}}]}}}}
    for name, value in files.items():
        target = PACKAGE / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    return files


if __name__ == '__main__':
    build()
