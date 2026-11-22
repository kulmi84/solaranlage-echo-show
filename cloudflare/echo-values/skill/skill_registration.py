"""Local Live integration candidate; caller must already validate Alexa requests.

No monkey-patch of the running handler and no credentials in this module.

"""

import json

import re

from urllib.request import Request, build_opener, HTTPRedirectHandler



class NoRedirect(HTTPRedirectHandler):

    def redirect_request(self, *args, **kwargs):

        return None



def urlopen(request, timeout):

    return build_opener(NoRedirect).open(request, timeout=timeout)






def widget_trigger(arguments, receipt=False):
    """Only enum/timing metadata; no identity, measurement, URL or free text."""
    names = ('solar.widget.values.receipt.v1',) if receipt else ('solar.widget.values.register.v1','solar.widget.directValues.v1')
    if not isinstance(arguments,list) or not arguments or arguments[0] not in names:
        raise ValueError('invalid_widget_trigger')
    if len(arguments)==1:
        return {'trigger':'legacy'}
    if len(arguments)!=2 or not isinstance(arguments[1],dict):
        raise ValueError('invalid_widget_trigger')
    marker=arguments[1]
    keys={'trigger','shownElapsedMs','sentElapsedMs'} | ({'ackElapsedMs'} if receipt else set())
    optional={'connectionVersion'} if 'connectionVersion' in marker else set()
    if optional and (type(marker['connectionVersion']) is not int or marker['connectionVersion'] not in (1,2,3)):
        raise ValueError('invalid_widget_trigger')
    if set(marker)!=keys|optional or marker.get('trigger') not in ('mount','reveal','minute'):
        raise ValueError('invalid_widget_trigger')
    for key in keys-{'trigger'}:
        if type(marker[key]) not in (int,float) or not 0<=marker[key]<=604800000:
            raise ValueError('invalid_widget_trigger')
    if marker['shownElapsedMs']>marker['sentElapsedMs'] or (receipt and marker['ackElapsedMs']<marker['sentElapsedMs']):
        raise ValueError('invalid_widget_trigger')
    return dict(marker)

def registration_requests(event, config):

    """Return internal calls; household is resolved by Worker, never supplied here."""

    if config.get('enabled') is not True:

        return []

    stage, package, skill = (config.get(k) for k in ('stage', 'package_id', 'skill_id'))

    if stage not in ('live', 'development') or not all(isinstance(x, str) and x for x in (package, skill)):

        raise ValueError('scope_missing')

    system = event.get('context', {}).get('System', {})

    if system.get('application', {}).get('applicationId') != skill:

        raise ValueError('application_mismatch')

    user = system.get('user', {})

    request = event.get('request', {})

    base = dict(stage=stage, packageId=package, userId=user.get('userId'), occurredAt=request.get('timestamp'))

    kind = request.get('type')
    if kind in ('AlexaSkillEvent.SkillDisabled','AlexaSkillEvent.SkillAccountLinked'):
        base['occurredAt'] = request.get('eventCreationTime') or request.get('timestamp')

    payload = request.get('payload') or {}

    if kind == 'AlexaSkillEvent.SkillAccountLinked':
        token=(request.get('body') or {}).get('accessToken') or user.get('accessToken')
        if not isinstance(token,str) or not re.fullmatch(r'[a-f0-9]{64}',token):
            raise ValueError('linked_access_missing')
        if system.get('person'):
            return []  # This integration is household/account-scoped, not voice-profile scoped.
        return [('relink',base,token)]
    if kind == 'AlexaSkillEvent.SkillDisabled':

        return [('unlink', base, None)]

    lifecycle = {'Alexa.DataStore.PackageManager.UsagesInstalled': 'register',

                 'Alexa.DataStore.PackageManager.UsagesRemoved': 'remove'}

    if kind in lifecycle:

        if payload.get('packageId') != package:

            return []

        instances = [u.get('instanceId') for u in payload.get('usages', []) if isinstance(u, dict)]

        # Installation events may omit instanceId. Wait for an authenticated widget event.

        instances = [x for x in instances if isinstance(x, str) and x]

        action = lifecycle[kind]
        if action == 'remove' and not instances:
            return [('remove', dict(base, deviceId=system.get('device', {}).get('deviceId'), removeAll=True), None)]

    elif kind == 'Alexa.Presentation.APL.UserEvent':

        arguments=request.get('arguments')
        marker=None
        if arguments not in (["solar.widget.open.v1"], ["solar.widget.text.open.v1"]):
            if not isinstance(arguments,list) or not arguments or arguments[0] not in ('solar.widget.values.register.v1','solar.widget.directValues.v1'):
                return []
            marker=widget_trigger(arguments)
        if marker and marker['trigger']!='legacy':
            base['trigger']=marker['trigger']
            if marker.get('connectionVersion') in (2,3) and package == 'SolarAccountImageBuild1211':
                base['connectionVersion']=marker['connectionVersion']

        prefix = re.escape('widget://' + skill) + ('_development' if stage == 'development' else '(?:_live)?') + re.escape('/' + package + '/')

        match = re.fullmatch(prefix + r'([A-Za-z0-9_.:-]{1,300})', request.get('presentationUri', ''))

        if not match:

            raise ValueError('presentation_mismatch')

        instances, action = [match.group(1)], 'register'

    else:

        return []

    session_user=event.get('session', {}).get('user', {})
    if (not user.get('accessToken') and session_user.get('accessToken')
            and session_user.get('userId') and user.get('userId')
            and session_user['userId']!=user['userId']):
        raise ValueError('account_mismatch')
    token = user.get('accessToken') or session_user.get('accessToken')

    if action == 'register' and (not isinstance(token, str) or not re.fullmatch(r'[a-f0-9]{64}', token)):
        if (not token and kind=='Alexa.Presentation.APL.UserEvent'
                and ((stage=='live' and package=='SolarAccountImageBuild1211')
                     or (stage=='development' and package=='Solaranlage1811'))):
            return [('refresh',dict(base,deviceId=system.get('device',{}).get('deviceId'),instanceId=instance),None) for instance in instances]
        if kind == 'Alexa.DataStore.PackageManager.UsagesInstalled':
            # Lifecycle notifications may omit account-linking access. Do not
            # reject installation or invent a household; mount/wake authenticates.
            return []
        raise ValueError('linked_access_missing')

    return [(action, dict(base, deviceId=system.get('device', {}).get('deviceId'), instanceId=instance), token if action == 'register' else None)

            for instance in instances]





def send_registration(call, config, opener=urlopen):

    action, payload, token = call

    if action not in ('register', 'refresh', 'voice', 'remove', 'unlink', 'relink'):

        raise ValueError('invalid_action')

    if config.get('origin') != 'https://solaranlage-echo-werte.kulmi84.workers.dev':

        raise ValueError('origin_not_approved')

    secret = config.get('registration_secret')

    if not isinstance(secret, str) or len(secret) < 32:

        raise ValueError('secret_missing')

    headers = {'Content-Type': 'application/json', 'X-Solar-Registration': secret, 'X-Solar-Stage': config['stage'], 'X-Solar-Package': config['package_id'],
               'User-Agent': 'SolaranlageSkill/1.1.0'}

    if token:

        headers['Authorization'] = 'Bearer ' + token

    trigger=payload.get('trigger')
    if trigger is not None and trigger not in ('mount','reveal','minute'):
        raise ValueError('invalid_widget_trigger')
    suffix=('?trigger='+trigger) if action in ('register','refresh') and trigger else ''
    req = Request(config['origin'] + '/internal/' + action + suffix,

                  data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')

    # Called synchronously by the candidate handler; no detached background work.

    with opener(req, timeout=5) as response:

        if response.status != 200:

            raise ValueError('registration_failed')

        limit=65536 if action in ('refresh','voice') and ((config.get('stage')=='development' and config.get('package_id')=='Solaranlage1811') or (config.get('stage') in ('live','development') and config.get('package_id')=='SolarAccountImageBuild1211')) else 8192
        raw=response.read(limit+1)

        if len(raw)>limit:

            raise ValueError('response_too_large')

        return json.loads(raw)

