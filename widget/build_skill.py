"""Build the widget on the current production source, preserving v1.0.7 status speech."""
import ast
import runpy
from pathlib import Path

ROOT = Path(__file__).parent


def build():
    runtime = runpy.run_path(str(ROOT.parent / 'build_skill.py'))['build']()
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
