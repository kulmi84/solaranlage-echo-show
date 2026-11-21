"""Bind existing fullscreen Text nodes to the verified DEV snapshot.

No voice/session changes. No render/layout substitution and no network reads.
"""
import re


def attach(document, snapshot, expires_at, namespace="Solaranlage1811"):
    if namespace not in ("Solaranlage1811", "SolarAccountImagesV3"):
        return False
    binding = snapshot.get('binding')
    sample_time = snapshot.get('sampleTime')
    if (not isinstance(binding, str) or not re.fullmatch(r'[a-f0-9]{64}', binding)
            or type(sample_time) not in (int, float) or sample_time <= 0):
        return False
    root = document['mainTemplate']['items'][0]
    live_page, history_page = root['items'][0]['items']
    live_nodes, history_nodes = {}, {}
    for prefix, row in (('live', live_page['items'][2]), ('daily', live_page['items'][4]),
                        ('month', history_page['items'][2]), ('year', history_page['items'][4])):
        for i, card in enumerate(row['items']):
            nodes = card['item']['items']
            target = live_nodes if prefix in ('live', 'daily') else history_nodes
            target[prefix + str(i) + 'v'] = nodes[1]
            if prefix == 'live' and i in (0, 3):
                target[prefix + str(i) + 'd'] = nodes[2]
            if (prefix == 'live' and i in (0, 2, 3)) or (prefix != 'live' and i in (2, 3)):
                target[prefix + str(i) + 'e'] = nodes[3]
    live_nodes['status'] = live_page['items'][5]
    history_nodes.update(monthLabel=history_page['items'][1], yearLabel=history_page['items'][3],
                         historyStatus=history_page['items'][5])
    initial_live = {key: node['text'] for key, node in live_nodes.items()}
    initial_live['stale'] = live_nodes['status']['color'] == '#FFD166'
    initial_history = {key: node['text'] for key, node in history_nodes.items()}
    root['bind'].extend([
        {'name': 'fsLive', 'value': initial_live},
        {'name': 'fsHistory', 'value': initial_history},
        {'name': 'fsSampleTime', 'value': sample_time},
        {'name': 'fsPending', 'value': {}},
        {'name': 'nextHistoryAt', 'value': 21600000},
    ])
    for name, nodes in (('fsLive', live_nodes), ('fsHistory', history_nodes)):
        for key, node in nodes.items():
            node['text'] = '${' + name + '.' + key + '}'
    live_nodes['status']['color'] = '${fsLive.stale ? "#FFD166" : "#8FA8BC"}'
    document.setdefault('extensions', []).append({'name': 'FullscreenStore', 'uri': 'alexaext:datastore:10'})
    document['settings']['FullscreenStore'] = {'dataBindings': [{
        'namespace': namespace, 'key': 'snapshot', 'dataBindingName': 'FullscreenSnapshot', 'dataType': 'OBJECT'}]}
    # Extension handlers run in document scope and cannot read solarRoot's
    # fsSampleTime. Consume the live DataBinding in the component's tick scope,
    # where both the local original timestamp and delivered object are visible.
    valid = ('FullscreenSnapshot && FullscreenSnapshot.binding == "' + binding + '"'
             ' && FullscreenSnapshot.fullscreen.schema == 1'
             ' && FullscreenSnapshot.fullscreen.sampleTime == FullscreenSnapshot.sampleTime'
             ' && FullscreenSnapshot.sampleTime >= fsSampleTime'
             + ''.join(' && FullscreenSnapshot.fullscreen.live.' + key + ' != null' for key in initial_live)
             + ''.join(' && FullscreenSnapshot.fullscreen.history.' + key + ' != null' for key in initial_history))
    # No extension callback or spoken skill session is needed for local updates.
    tick = root['handleTick'][0]
    tick['when'] = ('${displayState == "foreground" && utcTime < ' + str(expires_at)
                     + ' && ' + valid + '}')
    setv = lambda name, value, when=None: dict(type='SetValue', componentId='solarRoot', property=name,
        value=value, **({'when': when} if when else {}))
    tick['commands'] = [
        setv('fsPending', '${FullscreenSnapshot.fullscreen}'),
        setv('fsLive', '${fsPending.live}', '${currentPage == 0 && (refreshAfterWake || elapsedTime >= nextRefreshAt || fsPending.sampleTime > fsSampleTime)}'),
        setv('fsHistory', '${fsPending.history}', '${currentPage == 1 && (refreshAfterWake || elapsedTime >= nextHistoryAt)}'),
        setv('nextHistoryAt', '${elapsedTime + 21600000}', '${currentPage == 1 && (refreshAfterWake || elapsedTime >= nextHistoryAt)}'),
        setv('fsSampleTime', '${fsPending.sampleTime}', '${currentPage == 0}'),
        setv('nextRefreshAt', '${elapsedTime + 60000}', '${currentPage == 0 && (refreshAfterWake || elapsedTime >= nextRefreshAt)}'),
        setv('refreshAfterWake', False),
    ]
    return True
