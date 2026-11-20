"""Temporary, device-scoped Amazon support trace. Never logs tokens or readings."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

CONFIG = Path(__file__).with_name('support_trace_config.json')

def stamp():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')

def selected(event):
    try:
        cfg = json.loads(CONFIG.read_text(encoding='utf-8'))
        expiry = datetime.fromisoformat(cfg['expiresAt'].replace('Z', '+00:00'))
        system = event.get('context', {}).get('System', {})
        device = system.get('device', {}).get('deviceId', '')
        return (cfg.get('enabled') is True and expiry.tzinfo is not None
                and datetime.now(timezone.utc) < expiry
                and system.get('application', {}).get('applicationId') == cfg['skillId']
                and bool(device) and hashlib.sha256(device.encode()).hexdigest() in
                cfg.get('deviceSha256s', [cfg.get('deviceSha256')]))
    except Exception:
        return False

def uris(value):
    found = set()
    def walk(node):
        if isinstance(node, dict):
            for key, val in node.items():
                if key in ('presentationUri', 'presentationURI') and isinstance(val, str) and val.startswith('widget://'):
                    found.add(val)
                elif isinstance(val, (dict, list)):
                    walk(val)
        elif isinstance(node, list):
            for val in node:
                walk(val)
    walk(value)
    return sorted(found)

def emit(data):
    try:
        print('SOLAR_SUPPORT_TRACE ' + json.dumps(data, ensure_ascii=True, separators=(',', ':')))
    except Exception:
        pass

def invoke(handler, event, context):
    if not selected(event):
        return handler(event, context)
    req = event.get('request', {})
    system = event.get('context', {}).get('System', {})
    device = system.get('device', {}).get('deviceId', '')
    args = req.get('arguments', [])
    known = ('solar.widget.values.register.v1', 'solar.widget.text.open.v1',
             'solar.widget.values.receipt.v1', 'solar.fullscreen.live.auto.v1',
             'solar.fullscreen.text.auto.v1', 'solar.widget.directValues.v1')
    command = args[0] if args and args[0] in known else 'other'
    base = {'requestId': req.get('requestId'), 'requestType': req.get('type'),
            'deviceSha256': hashlib.sha256(device.encode()).hexdigest(),
            'command': command, 'presentationUris': uris({'request': req, 'context': event.get('context', {})})}
    emit({**base, 'phase': 'received', 'utc': stamp()})
    try:
        response = handler(event, context)
    except BaseException:
        emit({**base, 'phase': 'raised', 'utc': stamp()})
        raise
    directives = response.get('response', {}).get('directives', []) if isinstance(response, dict) else []
    emit({**base, 'phase': 'reply_ready', 'utc': stamp(), 'responsePresentationUris': uris(directives),
          'directiveTypes': [d.get('type') for d in directives if isinstance(d, dict)],
          'executeCommandsCount': sum(d.get('type') == 'Alexa.Presentation.APL.ExecuteCommands' for d in directives if isinstance(d, dict))})
    return response
