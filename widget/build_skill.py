"""Build the widget candidate from frozen final v1.0.6, never overwrite it."""
import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).parent


def build():
    original = ROOT.parent / 'alexa/archive/v1.0.6/lambda_function.py'
    raw = original.read_bytes()
    if hashlib.sha256(raw).hexdigest() != '1687156a457c9a55afa2a13558949f7cc8fed1c39f6a61f38d15f9d3cbe7a0e4':
        raise ValueError('Frozen production source changed; stop before building')
    runtime = raw.decode('utf-8')
    adapter = (ROOT / 'widget_adapter.py').read_text(encoding='utf-8')
    binding = '''
def register_widget(event, action):
    config = image_config()
    if config.get('widget_registration_url') != 'https://solaranlage-widget.kulmi84.workers.dev/registrations':
        raise ValueError('Widget publisher not configured')
    system = event.get('context', {}).get('System', {})
    payload = {'action': action, 'user': system.get('user', {}).get('userId'),
               'device': system.get('device', {}).get('deviceId')}
    if action == 'install':
        payload['access'] = image_access_token(event)
    request = Request(config['widget_registration_url'], data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'User-Agent': 'Solaranlage-Widget/1.0',
                 'Authorization': 'Bearer ' + config['widget_registration_key']})
    with build_opener(NoImageRedirect()).open(request, timeout=2) as response:
        if response.status != 200:
            raise ValueError('Widget registration failed')

def lambda_handler(event, context):
    return route_widget(event, context, dashboard_handler, register_widget)
'''
    source = '\n\n'.join([runtime, 'dashboard_handler = lambda_handler', adapter, binding])
    ast.parse(source, feature_version=(3, 8))
    return source


if __name__ == '__main__':
    path = ROOT / 'dist/lambda_function.py'
    path.parent.mkdir(exist_ok=True)
    path.write_text(build(), encoding='utf-8')
