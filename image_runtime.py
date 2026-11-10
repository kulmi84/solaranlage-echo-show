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
    expires_at = int(time.time() * 1000) + grant['expires_in'] * 1000
    renew = {'type': 'SendEvent', 'arguments': ['solar.fullscreen.renew.v1'],
             'sequencer': 'solarImageAccess'}
    renewal_due = 'utcTime >= imageAccessExpiresAt - 300000'
    root['bind'] += [{'name': 'statusImageBase', 'value': base.replace('/tile.png?', '/status.png?', 1)},
                     {'name': 'imageAccessExpiresAt', 'value': expires_at},
                     {'name': 'lastImageAccessRequest', 'value': 0}]
    root['bind'] += [{'name': 'tileImageBase', 'value': base}, {'name': 'tileRenderNonce', 'value': render_nonce}, {'name': 'tileImageLoads', 'value': 0}]
    pages, timer = [], []
    for page_index, page_name in enumerate(('live', 'history')):
        clock = 'lastDashboardRefresh' if page_name == 'live' else 'lastHistoryRefresh'
        interval = REFRESH_INTERVAL_MS if page_name == 'live' else HISTORY_INTERVAL_MS
        refresh, rows = [], []
        for row in range(2):
            cards = []
            for col, label in enumerate(('PV + BKW', 'Haus', 'Netz', 'Akku')):
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
                        'value': '${statusImageBase + "&page=' +
                        page_name + '&n=" + tileRenderNonce + "-" + elapsedTime}'})
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
                {'type': 'TouchWrapper', 'id': 'solarRefreshButton' + str(page_index),
                 'onPress': [
                     {'type': 'Sequential', 'when': '${' + renewal_due + '}', 'commands': [
                         {'type': 'SetValue', 'componentId': 'solarRoot', 'property': 'lastImageAccessRequest',
                          'value': '${utcTime}'}, renew]},
                     {'type': 'Sequential', 'when': '${!(' + renewal_due + ')}', 'commands': refresh}],
                 'item': text('Aktualisieren', '3.6vh', '#8BCBFF', padding='1.5vh')},
                {'type': 'TouchWrapper', 'onPress': [{'type': 'SetPage', 'componentId': 'solarPager',
                     'position': 'absolute', 'value': 1-page_index}],
                 'item': text('Monat/Jahr' if page_index == 0 else 'Live/Heute', '3vh', '#8BCBFF', padding='1vh')}]}] + rows + [
                {'type': 'Image', 'id': status_id, 'width': '94vw', 'height': '3vh', 'scale': 'best-fit',
                 'align': 'left', 'spacing': '2vh', 'source': status_base + '&n=' + render_nonce},
                text('1/2 - Nach rechts wischen: Monat/Jahr' if page_index == 0 else '2/2 - Nach links wischen: Live/Heute',
                     '2.3vh', '#8FA8BC', spacing='1vh')]})
        due = ('${displayState == "foreground" && currentPage == ' + str(page_index) +
               ' && utcTime < imageAccessExpiresAt' +
               ' && (elapsedTime - ' + clock + ' >= ' + str(interval) +
               ' || (imageFailed && elapsedTime - ' + clock + ' >= 10000))}')
        timer.extend(dict(step, when=due) for step in refresh)
        timer.append({'type': 'SetValue', 'componentId': 'solarRoot', 'property': clock,
                      'value': '${elapsedTime}', 'when': due})
    root['items'][0]['height'] = '100vh'
    root['items'][0]['items'] = pages
    timer += [
        {'type': 'Sequential',
         'when': '${displayState == "foreground" && ' + renewal_due +
                 ' && utcTime - lastImageAccessRequest >= 60000}',
         'commands': [
             {'type': 'SetValue', 'componentId': 'solarRoot', 'property': 'lastImageAccessRequest',
              'value': '${utcTime}'}, renew]},
        {'type': 'SetValue', 'componentId': 'solarRoot', 'property': 'imageFailed',
         'value': True, 'when': '${utcTime >= imageAccessExpiresAt}'}]
    root['handleTick'][-1]['commands'] = timer
    document = result['response']['directives'][0]['document']
    document['onDisplayStateChange'] = [{'type': 'SetValue', 'componentId': 'solarRoot', 'property': 'lastDashboardRefresh', 'value': -60000, 'when': '${event.displayState == "foreground"}'}]
    return result


def renew_fullscreen_image_access(event, access):
    request = event['request']
    visual = event.get('context', {}).get('Alexa.Presentation.APL', {})
    if (not access or request.get('presentationUri')
            or request.get('token') != 'solaranlage' or visual.get('token') != 'solaranlage'
            or request.get('source', {}).get('id') not in ('solarRoot', 'solarRefreshButton0', 'solarRefreshButton1')):
        return {'version': '1.0', 'response': {}}
    issued_at = int(time.time() * 1000)
    try:
        grant = create_image_session(access, image_config())
    except Exception:
        return {'version': '1.0', 'response': {}}
    values = {
        'tileImageBase': grant['base_url'].replace('/dashboard.png?', '/tile.png?', 1),
        'statusImageBase': grant['base_url'].replace('/dashboard.png?', '/status.png?', 1),
        'imageAccessExpiresAt': issued_at + grant['expires_in'] * 1000,
        'lastDashboardRefresh': '${elapsedTime - ' + str(REFRESH_INTERVAL_MS) + '}',
        'lastHistoryRefresh': '${elapsedTime - ' + str(HISTORY_INTERVAL_MS) + '}',
    }
    return {'version': '1.0', 'response': {'directives': [{
        'type': 'Alexa.Presentation.APL.ExecuteCommands', 'token': 'solaranlage',
        'commands': [{'type': 'SetValue', 'componentId': 'solarRoot', 'property': name, 'value': value}
                     for name, value in values.items()],
    }]}}


def lambda_handler(event, context):
    request=event.get('request',{})
    kind,intent=request.get('type'),request.get('intent',{}).get('name')
    access=image_access_token(event)
    if kind=='Alexa.Presentation.APL.UserEvent':
        if request.get('arguments') == ['solar.fullscreen.renew.v1']:
            return renew_fullscreen_image_access(event, access)
        return {'version':'1.0','response':{}}
    if kind=='IntentRequest' and (intent in SPOKEN_METRICS or intent=='StatusIntent'):
        if not access:
            return {'version':'1.0','response':{'card':{'type':'LinkAccount'},
                'outputSpeech':{'type':'PlainText','text':'Bitte verbinde deine Anlage in der Alexa-App mit Solaranlage.'},'shouldEndSession':True}}
        try:
            pv=read_pv(RELAY_URL,access)
            speech=spoken_status(pv) if intent=='StatusIntent' else spoken_reading(pv,intent)
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
