"""Beta-only image transport. This is appended to the existing diagnostic skill."""
from urllib.request import Request, build_opener, HTTPRedirectHandler
import re

IMAGE_ORIGIN = 'https://solaranlage-image-test.kulmi84.workers.dev'
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
    if not isinstance(result.get('expires_in'), int) or not 1 <= result['expires_in'] <= 3600:
        raise ValueError('Invalid image lifetime')
    return result


def live_image_document(result, grant=None, message=None):
    """Replace only the data area. Keep clock image, tick and attempts below."""
    response = result['response']
    document = response['directives'][0]['document']
    root = document['mainTemplate']['items'][0]
    pager = root['items'][0]
    pager['height'] = '84vh'
    # Keep all requested probes, compactly arranged below the actual dashboard.
    for item in root['items'][1:]:
        if item.get('id') == 'imageProbe':
            item.update(width='32vw', height='9vh', bottom='3vh', left='65vw')
        elif item.get('id') == 'imageProbeStatus':
            item.update(fontSize='1.8vh', bottom='6vh', left='2vw', width='61vw')
        elif item.get('id') == 'tickProbe':
            item.update(fontSize='2vh', bottom=0)
    root['bind'] += [{'name': 'imageFailed', 'value': False},
                     {'name': 'lastDashboardRefresh', 'value': 0}]
    root['items'].append({'type': 'Text', 'text':
        'Wertebild nicht verfuegbar. Testskill bitte neu oeffnen.',
        'color': '#FF8080', 'fontSize': '3vh', 'backgroundColor': '#0C151F',
        'position': 'absolute', 'top': '70vh', 'left': '2vw', 'width': '96vw',
        'display': '${imageFailed ? "normal" : "none"}'})
    if grant is None:
        pager['items'] = [{'type': 'Container', 'width': '100vw', 'height': '84vh',
            'backgroundColor': '#0C151F', 'padding': '5vw', 'items': [
                text('Solaranlage Test', '6vh', fontWeight='700'),
                {'type': 'Text', 'text': message, 'fontSize': '4vh',
                 'color': '#FFD166', 'width': '90vw', 'spacing': '8vh'}]}]
        return result
    base, lifetime = grant['base_url'], grant['expires_in'] * 1000
    root['bind'].append({'name': 'dashboardBase', 'value': base})
    pages = []
    for index, name in enumerate(('live', 'history')):
        change_source = '${dashboardBase + "&page=' + name + '&n=" + elapsedTime}'
        image_id = 'liveValuesImage' if index == 0 else 'historyValuesImage'
        refresh = {'type': 'SetValue', 'componentId': image_id,
                   'property': 'source', 'value': change_source}
        pages.append({'type': 'Container', 'width': '100vw', 'height': '84vh',
            'backgroundColor': '#0C151F', 'items': [
                {'type': 'Image', 'id': image_id, 'width': '100vw', 'height': '84vh',
                 'scale': 'best-fit', 'source': base + '&page=' + name + '&n=initial',
                 'onLoad': [{'type': 'SetValue', 'componentId': 'solarRoot',
                             'property': 'imageFailed', 'value': False}],
                 'onFail': [{'type': 'SetValue', 'componentId': 'solarRoot',
                             'property': 'imageFailed', 'value': True}]},
                {'type': 'TouchWrapper', 'position': 'absolute', 'top': '1vh',
                 'right': '1vw', 'onPress': [{'type': 'SetPage',
                     'componentId': 'solarPager', 'position': 'absolute', 'value': 1 - index}],
                 'item': text('Monat/Jahr' if index == 0 else 'Live/Heute', '2.5vh', '#8BCBFF')},
                {'type': 'TouchWrapper', 'position': 'absolute', 'bottom': '1vh',
                 'right': '1vw', 'onPress': [refresh],
                 'item': text('Aktualisieren', '2.5vh', '#8BCBFF')} ]})
        command = dict(refresh)
        command['when'] = ('${displayState == "foreground" && currentPage == ' + str(index) +
            ' && elapsedTime < ' + str(lifetime) +
            ' && (elapsedTime - lastDashboardRefresh >= 60000 || (imageFailed && elapsedTime - lastDashboardRefresh >= 10000))}')
        # Local SetValue -> HTTPS image request, never a SendEvent to the skill.
        root.setdefault('dashboardRefreshCommands', []).append(command)
    pager['items'] = pages
    commands = root.pop('dashboardRefreshCommands')
    commands.append({'type': 'SetValue', 'componentId': 'solarRoot',
        'property': 'lastDashboardRefresh', 'value': '${elapsedTime}',
        'when': '${displayState == "foreground" && (elapsedTime - lastDashboardRefresh >= 60000 || (imageFailed && elapsedTime - lastDashboardRefresh >= 10000))}'})
    commands.append({'type': 'SetValue', 'componentId': 'solarRoot',
        'property': 'imageFailed', 'value': True,
        'when': '${elapsedTime >= ' + str(lifetime) + '}'})
    root['handleTick'].append({'minimumDelay': 1000, 'commands': commands})
    return result


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
    request = event.get('request', {})
    kind, intent = request.get('type'), request.get('intent', {}).get('name')
    access = image_access_token(event)
    if kind == 'IntentRequest' and intent in SPOKEN_METRICS:
        if not access:
            return {'version': '1.0', 'response': {'card': {'type': 'LinkAccount'},
                'outputSpeech': {'type': 'PlainText', 'text': 'Bitte verknuepfe zuerst den Testskill in der Alexa-App.'},
                'shouldEndSession': True}}
        try:
            from_image_pv = read_pv(RELAY_URL, access)
            speech = spoken_reading(from_image_pv, intent)
        except Exception:
            speech = 'Die Live-Werte sind gerade nicht verfuegbar.'
        return {'version': '1.0', 'response': {
            'outputSpeech': {'type': 'PlainText', 'text': speech}, 'shouldEndSession': True}}
    result = probe_handler(event, context)
    if kind == 'LaunchRequest' and not any(d.get('type') == 'Alexa.Presentation.APL.RenderDocument'
            for d in result.get('response', {}).get('directives', [])):
        return {'version': '1.0', 'response': {
            'outputSpeech': {'type': 'PlainText', 'text': 'Bitte oeffne die Bild-Testversion auf einem Echo Show.'},
            'shouldEndSession': True}}
    if not any(d.get('type') == 'Alexa.Presentation.APL.RenderDocument'
               for d in result.get('response', {}).get('directives', [])):
        return result
    if not access:
        result['response']['card'] = {'type': 'LinkAccount'}
        return live_image_document(result, message=
            'Bitte meine Solaranlage Test in der Alexa-App mit deinem Konto verknuepfen. Die Diagnose unten bleibt aktiv.')
    try:
        grant = create_image_session(access, image_config())
    except Exception as error:
        diagnostic = type(error).__name__
        if isinstance(getattr(error, 'code', None), int):
            diagnostic += '-' + str(error.code)
            try:
                detail = json.loads(error.read(1024)).get('detail', '')
                if re.fullmatch(r'(upstream_[0-9]{3}|too_large|configuration|invalid|internal)', detail):
                    diagnostic += '-' + detail
            except Exception:
                pass
        elif isinstance(error, ValueError):
            diagnostic += '-' + ('config' if 'origin' in str(error) else 'validation')
        print('IMAGE_SESSION_FAILURE ' + diagnostic)
        return live_image_document(result, message=
            'Live-Bildzugang gerade nicht verfuegbar. Diagnose: ' + diagnostic)
    return house_image_pilot(live_image_document(result, grant=grant), grant)
