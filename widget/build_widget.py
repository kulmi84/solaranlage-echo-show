"""Prepare the production widget without altering either deployed skill."""
import json
from pathlib import Path

ROOT = Path(__file__).parent
PACKAGE = ROOT / 'skill-package/dataStorePackages/SolarWidget'


def document():
    def label(value, size=20, color='#AFC1D1'):
        return dict(type='Text', text=value, fontSize=size, color=color, maxLines=1)
    rows = [label('Solaranlage', 30, '#FFFFFF')]
    for title, field, color in [('PV + BKW', 'production', '#FFD166'),
                                ('Hausverbrauch', 'consumption', '#8BCBFF'),
                                ('Akku', 'battery', '#51D3C5')]:
        rows.append(dict(type='Container', spacing=14, items=[
            label(title, 22),
            dict(label('${SolarLive.' + field + " ?? '—'}", 42, color), fontWeight='bold')]))
    rows += [dict(label("${SolarLive.status ?? 'Warte auf Live-Werte'}", 14), spacing=18),
             label("${SolarLive.stand ?? 'Noch kein Empfang'}", 14),
             dict(label('Antippen: Vollbild öffnen', 16, '#8BCBFF'), spacing=6)]
    return dict(type='APL', version='2023.3', theme='dark',
        extensions=[dict(name='DataStore', uri='alexaext:datastore:10')],
        settings={'DataStore': {'dataBindings': [dict(namespace='Solar', key='live', dataBindingName='SolarLive', dataType='OBJECT')]}},
        mainTemplate={'items': [dict(type='TouchWrapper', width='100vw', height='100vh',
            onPress=[dict(type='SendEvent', arguments=['solar.widget.open.v1'], flags={'interactionMode': 'STANDARD'})],
            item=dict(type='Container', width='100%', height='100%', backgroundColor='#0C151F', padding=16, items=rows))]})


def build():
    files = {'documents/document.json': document(), 'datasources/default.json': {},
             'presentations/default.tpl': dict(type='APL_PRESENTATION', documentUrl='documents/document.json', datasourceUrl='datasources/default.json'),
             'manifest.json': {'packageVersion':'1.0','packageType':'APL_PACKAGE',
                'manifest':{'id':'SolarWidget','version':'1.0.0','installStateChanges':'INFORM','updateStateChanges':'INFORM',
                    'presentationDefinitions':[{'url':'presentations/default.tpl'}],
                    'appliesTo':"${viewport.mode == 'HUB' && location == 'FAVORITE'}"},
                'publishingInformation':{'schemaVersion':'1.0','locales':{'de-DE':[{'targetViewport':'WIDGET_M','metadata':{
                    'name':'Solaranlage','description':'Sieh PV-Leistung, Hausverbrauch und Akkustand. Ein Tipp öffnet die große Solaranlagenanzeige.',
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
