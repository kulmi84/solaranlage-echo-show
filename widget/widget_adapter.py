"""Explicit widget tap routing, to wrap the unchanged v1.0.6 handler."""
from copy import deepcopy

OPEN = 'solar.widget.open.v1'


def route_widget(event, context, dashboard_handler, registration_handler=None):
    request = event.get('request', {})
    kind = request.get('type', '')
    package = request.get('payload', {}).get('packageId') or request.get('packageId')
    lifecycle = {'Alexa.DataStore.PackageManager.UsagesInstalled': 'install',
                 'Alexa.DataStore.PackageManager.UpdateRequest': 'install',
                 'Alexa.DataStore.PackageManager.UsagesRemoved': 'remove'}
    if kind in lifecycle and package == 'SolarWidget':
        if registration_handler:
            access = event.get('context', {}).get('System', {}).get('user', {}).get('accessToken')
            if lifecycle[kind] == 'remove' or access:
                registration_handler(event, lifecycle[kind])
        return {'version': '1.0', 'response': {'shouldEndSession': True}}
    if (request.get('type') == 'Alexa.Presentation.APL.UserEvent'
            and request.get('arguments') == [OPEN]):
        if registration_handler and event.get('context', {}).get('System', {}).get('user', {}).get('accessToken'):
            try:
                registration_handler(event, 'install')
            except Exception:
                # Registration failure must never prevent opening the existing dashboard.
                pass
        launch = deepcopy(event)
        launch['request'] = {**request, 'type': 'LaunchRequest'}
        launch['request'].pop('arguments', None)
        return dashboard_handler(launch, context)
    return dashboard_handler(event, context)
