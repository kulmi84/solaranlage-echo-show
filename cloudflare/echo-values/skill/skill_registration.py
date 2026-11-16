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

        if request.get('arguments') not in (["solar.widget.open.v1"], ["solar.widget.text.open.v1"], ["solar.widget.values.register.v1"], ["solar.widget.directValues.v1"]):

            return []

        prefix = re.escape('widget://' + skill) + ('_development' if stage == 'development' else '(?:_live)?') + re.escape('/' + package + '/')

        match = re.fullmatch(prefix + r'([A-Za-z0-9_.:-]{1,300})', request.get('presentationUri', ''))

        if not match:

            raise ValueError('presentation_mismatch')

        instances, action = [match.group(1)], 'register'

    else:

        return []

    token = user.get('accessToken')

    if action == 'register' and (not isinstance(token, str) or not re.fullmatch(r'[a-f0-9]{64}', token)):

        raise ValueError('linked_access_missing')

    return [(action, dict(base, deviceId=system.get('device', {}).get('deviceId'), instanceId=instance), token if action == 'register' else None)

            for instance in instances]





def send_registration(call, config, opener=urlopen):

    action, payload, token = call

    if action not in ('register', 'remove', 'unlink', 'relink'):

        raise ValueError('invalid_action')

    if config.get('origin') != 'https://solaranlage-echo-werte.kulmi84.workers.dev':

        raise ValueError('origin_not_approved')

    secret = config.get('registration_secret')

    if not isinstance(secret, str) or len(secret) < 32:

        raise ValueError('secret_missing')

    headers = {'Content-Type': 'application/json', 'X-Solar-Registration': secret}

    if token:

        headers['Authorization'] = 'Bearer ' + token

    req = Request(config['origin'] + '/internal/' + action,

                  data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')

    # Called synchronously by the candidate handler; no detached background work.

    with opener(req, timeout=5) as response:

        if response.status != 200:

            raise ValueError('registration_failed')

        raw=response.read(8193)

        if len(raw)>8192:

            raise ValueError('response_too_large')

        return json.loads(raw)

