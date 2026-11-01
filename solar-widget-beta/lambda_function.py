"""Deploy only to the NEW Alexa-hosted skill Meine Solaranlage BETA."""
import os
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

REFRESH_EVENT = 'solar.beta.refresh.v1'


def refresh_widget():
    token = os.environ.get('BETA_ADMIN_TOKEN', '')
    if not token:
        return False
    request = Request('https://meine-solaranlage-widget-beta.kulmi84.workers.dev/push',
                      data=b'{}', method='POST', headers={
                          'Authorization': 'Bearer ' + token,
                          'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=6) as result:
            return json.loads(result.read(4096)).get('delivered', 0) > 0
    except (HTTPError, URLError, TimeoutError, ValueError, OSError):
        return False


def lambda_handler(event, context):
    expected = os.environ.get('BETA_SKILL_ID', 'amzn1.ask.skill.6a7a8591-1eb6-42cf-b514-e1d0d056c4a2')
    actual = event.get('context', {}).get('System', {}).get('application', {}).get('applicationId')
    if not expected or actual != expected:
        raise ValueError('Separate BETA skill ID required')
    request = event.get('request', {})
    kind = request.get('type', '')
    response = {}
    if kind == 'Alexa.Presentation.APL.UserEvent':
        if request.get('arguments') == [REFRESH_EVENT]:
            refresh_widget()
        return {'version': '1.0', 'response': {'shouldEndSession': True}}
    if kind in ('LaunchRequest', 'IntentRequest'):
        intent = request.get('intent', {}).get('name')
        response['shouldEndSession'] = True
    return {'version': '1.0', 'response': response}
