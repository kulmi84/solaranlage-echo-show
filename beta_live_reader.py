"""Read-only PV relay client, to be integrated into the Beta skill."""
import json
import math
from datetime import datetime, timezone
from urllib.request import Request, urlopen


def read_pv(url, read_token):
    if not url.startswith('https://'):
        raise ValueError('HTTPS required')
    request = Request(url, headers={
        'Authorization': 'Bearer ' + read_token,
        'User-Agent': 'HomeAssistant-PV-Beta/1.0',
        'Accept': 'application/json',
    })
    with urlopen(request, timeout=3) as response:
        raw = response.read(4097)
    if len(raw) > 4096:
        raise ValueError('Response too large')
    data = json.loads(raw)
    power = data.get('power_w')
    if isinstance(power, bool) or not isinstance(power, (int, float)) or not math.isfinite(power) or power < 0:
        raise ValueError('Invalid power')
    received = datetime.fromisoformat(data['received_at'].replace('Z', '+00:00'))
    age = (datetime.now(timezone.utc) - received).total_seconds()
    if age < -60:
        raise ValueError('Invalid timestamp')
    metrics = {}
    for key in ['pv_dc_w', 'bkw_w', 'home_w', 'grid_import_w', 'grid_export_w', 'battery_soc', 'battery_charge_w', 'battery_discharge_w', 'today_pv_kwh', 'today_home_kwh', 'today_grid_import_kwh', 'today_grid_export_kwh', 'today_battery_charge_kwh', 'today_battery_discharge_kwh']:
        value = data.get(key)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or value > (100 if key == 'battery_soc' else 10000000)):
            raise ValueError('Invalid metric')
        metrics[key] = value
    metrics['power_w'] = power
    energy_date = data.get('energy_date')
    today = data.get('local_date')
    if energy_date != today:
        for key in metrics:
            if key.startswith('today_'): metrics[key] = None
    return {
        'metrics': metrics,
        'energyDate': energy_date,
        'receivedText': data.get('received_local', '—'),
        'valueText': f'{power / 1000:.2f}'.replace('.', ',') + ' kW',
        'statusText': 'VERALTET · seit mehr als 3 Minuten kein Empfang' if age > 180 else 'PV-Leistung · zuletzt empfangener Wert',
        'stale': age > 180,
    }
