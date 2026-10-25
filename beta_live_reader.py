"""Read-only PV relay client, to be integrated into the Beta skill."""
import json
import math
from datetime import datetime, timezone
from urllib.request import Request, build_opener, HTTPRedirectHandler


class NoRelayRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def urlopen(request, timeout):
    return build_opener(NoRelayRedirect).open(request, timeout=timeout)


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
    history = {}
    history_status = 'Noch keine Monats- und Jahreswerte'
    raw_history = data.get('history')
    if isinstance(raw_history, dict):
        try:
            if not isinstance(raw_history.get('received_at'), str):
                raise ValueError('Invalid history timestamp')
            h_received = datetime.fromisoformat(raw_history['received_at'].replace('Z', '+00:00'))
            h_age = (datetime.now(timezone.utc) - h_received).total_seconds()
            if h_age < -60:
                raise ValueError('Invalid history timestamp')
            for prefix, period in [('month', (today or '')[:7]), ('year', (today or '')[:4])]:
                valid_period = bool(period) and raw_history.get(prefix + '_id') == period
                for name in ['pv', 'home', 'grid_import', 'grid_export', 'battery_charge', 'battery_discharge']:
                    key = prefix + '_' + name + '_kwh'
                    value = raw_history.get(key)
                    if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or value > 10000000):
                        raise ValueError('Invalid history value')
                    history[key] = value if valid_period else None
            history_status = 'Stand ' + raw_history['received_at'][:16].replace('T', ' ') + ' UTC · alle 6 Stunden'
            if h_age > 6 * 3600 + 600:
                history_status = 'VERALTET · Monats-/Jahreswerte seit über 6 Stunden ohne Upload'
            if raw_history.get('month_id') != (today or '')[:7]:
                history_status = 'Neuer Monat · aktuelle Monatswerte stehen noch aus'
        except (ValueError, KeyError, TypeError):
            history = {}
            history_status = 'Monats- und Jahreswerte nicht verfügbar'
    return {
        'metrics': metrics,
        'history': history,
        'historyStatus': history_status,
        'monthLabel': (today or '')[:7],
        'yearLabel': (today or '')[:4],
        'energyDate': energy_date,
        'receivedText': data.get('received_local', '—'),
        'valueText': f'{power / 1000:.2f}'.replace('.', ',') + ' kW',
        'statusText': 'VERALTET · seit mehr als 3 Minuten kein Empfang' if age > 180 else 'PV-Leistung · zuletzt empfangener Wert',
        'ageSeconds': max(0, int(age)),
        'stale': age > 180,
    }
