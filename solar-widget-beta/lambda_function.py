"""Deploy only to the NEW Alexa-hosted skill Meine Solaranlage BETA."""
import os


def lambda_handler(event, context):
    expected = os.environ.get('BETA_SKILL_ID', 'amzn1.ask.skill.6a7a8591-1eb6-42cf-b514-e1d0d056c4a2')
    actual = event.get('context', {}).get('System', {}).get('application', {}).get('applicationId')
    if not expected or actual != expected:
        raise ValueError('Separate BETA skill ID required')
    request = event.get('request', {})
    kind = request.get('type', '')
    response = {}
    if kind in ('LaunchRequest', 'IntentRequest'):
        intent = request.get('intent', {}).get('name')
        response['shouldEndSession'] = True
        if intent not in ('AMAZON.StopIntent', 'AMAZON.CancelIntent'):
            response['outputSpeech'] = {'type': 'PlainText', 'text':
                'Meine Solaranlage BETA. Füge das neue Beta Widget in der Widget Galerie hinzu. Die Messwerte werden dort automatisch aktualisiert.'}
    return {'version': '1.0', 'response': response}
