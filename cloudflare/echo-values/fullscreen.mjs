// Text payload for the existing native fullscreen layout, from the same DB row.
// Exact binary rounding matches Python's existing f-string renderer.
export function fixed(value, digits = 2, grouping = false) {
  const bytes = new DataView(new ArrayBuffer(8));
  bytes.setFloat64(0, value);
  const bits = bytes.getBigUint64(0), exponent = Number((bits >> 52n) & 2047n);
  let n = (bits & ((1n << 52n) - 1n)) | (exponent ? 1n << 52n : 0n);
  const shift = (exponent || 1) - 1023 - 52;
  n *= 10n ** BigInt(digits);
  if (shift >= 0) n <<= BigInt(shift);
  else {
    const d = 1n << BigInt(-shift), q = n / d, r = n % d;
    n = q + (r * 2n > d || (r * 2n === d && q % 2n) ? 1n : 0n);
  }
  let s = n.toString().padStart(digits + 1, '0');
  let whole = digits ? s.slice(0, -digits) : s;
  if (grouping) whole = whole.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return ((bits >> 63n) ? '-' : '') + whole + (digits ? ',' + s.slice(-digits) : '');
}

export function fullscreen(row, now) {
  const d = JSON.parse(row.live_json), at = Date.parse(row.live_at);
  if (!Number.isFinite(at) || at > now + 60000) throw Error('invalid_timestamp');
  const metric = (key, max = 10000000) => {
    const v = d[key];
    if (v == null) return null;
    if (typeof v !== 'number' || !Number.isFinite(v) || v < 0 || v > max) throw Error('invalid_measurement');
    return v;
  };
  for (const key of ['power_w','pv_dc_w','bkw_w','home_w','grid_import_w','grid_export_w',
      'battery_charge_w','battery_discharge_w','today_pv_kwh','today_home_kwh',
      'today_grid_import_kwh','today_grid_export_kwh','today_battery_charge_kwh','today_battery_discharge_kwh']) metric(key);
  metric('battery_soc', 100);
  const parts = new Intl.DateTimeFormat('en-CA', {timeZone: row.timezone || 'Europe/Berlin',
    year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23'}).formatToParts(at);
  const p = name => parts.find(x => x.type === name).value;
  const dateParts = new Intl.DateTimeFormat('en-CA', {timeZone: row.timezone || 'Europe/Berlin',
    year: 'numeric', month: '2-digit', day: '2-digit'}).formatToParts(now);
  const today = ['year', 'month', 'day'].map(k => dateParts.find(x => x.type === k).value).join('-');
  const num = (v, unit, digits = 2) => v == null ? '—' : fixed(v, digits) + ' ' + unit;
  const power = key => {const v = metric(key);return v == null ? '—' : v >= 1000 ? num(v / 1000, 'kW') : num(v, 'W', 0);};
  const energy = key => num(d.energy_date === today ? metric(key) : null, 'kWh');
  const live = {
    live0v: power('power_w'), live0d: 'PV ' + power('pv_dc_w'), live0e: 'BKW ' + power('bkw_w'),
    live1v: power('home_w'), live2v: power('grid_export_w'), live2e: 'Bezug ' + power('grid_import_w'),
    live3v: num(metric('battery_soc', 100), '%', 0), live3d: 'Laden ' + power('battery_charge_w'), live3e: 'Entladen ' + power('battery_discharge_w'),
    daily0v: energy('today_pv_kwh'), daily1v: energy('today_home_kwh'), daily2v: energy('today_grid_export_kwh'),
    daily2e: 'Bezug ' + energy('today_grid_import_kwh'), daily3v: energy('today_battery_charge_kwh'),
    daily3e: 'Entladen ' + energy('today_battery_discharge_kwh'),
    status: now - at > 180000 ? 'VERALTET · seit mehr als 3 Minuten kein Empfang' : `Stand ${p('hour')}:${p('minute')} Uhr · Auto alle 60 s · Tageswerte aus HA-Statistik`,
    stale: now - at > 180000
  };
  let h = {}, historyStatus = 'Noch keine Monats- und Jahreswerte', historyTime = 0;
  if (row.history_json) {
    try {
      const raw = JSON.parse(row.history_json), received = Date.parse(row.history_at);
      if (!Number.isFinite(received) || received > now + 60000) throw Error('invalid_history');
      for (const prefix of ['month', 'year']) {
        const period = today.slice(0, prefix === 'month' ? 7 : 4);
        for (const name of ['pv', 'home', 'grid_import', 'grid_export', 'battery_charge', 'battery_discharge']) {
          const key = `${prefix}_${name}_kwh`, value = raw[key];
          if (value != null && (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 10000000)) throw Error('invalid_history');
          h[key] = raw[prefix + '_id'] === period ? value : null;
        }
      }
      historyTime = received;
      historyStatus = 'Stand ' + row.history_at.slice(0, 16).replace('T', ' ') + ' UTC · alle 6 Stunden';
      if (now - received > 22200000) historyStatus = 'VERALTET · Monats-/Jahreswerte seit über 6 Stunden ohne Upload';
      if (raw.month_id !== today.slice(0, 7)) historyStatus = 'Neuer Monat · aktuelle Monatswerte stehen noch aus';
    } catch {h = {}; historyStatus = 'Monats- und Jahreswerte nicht verfügbar';}
  }
  const history = {monthLabel: 'MONAT · ' + today.slice(0, 7), yearLabel: 'JAHR · ' + today.slice(0, 4), historyStatus};
  for (const prefix of ['month', 'year']) {
    const f = key => h[`${prefix}_${key}_kwh`] == null ? '—' : fixed(h[`${prefix}_${key}_kwh`], 2, true);
    for (const [i, key] of ['pv', 'home', 'grid_export', 'battery_charge'].entries()) history[prefix + i + 'v'] = f(key);
    history[prefix + '2e'] = 'Bezug ' + f('grid_import') + ' kWh';
    history[prefix + '3e'] = '↓ ' + f('battery_discharge') + ' kWh';
  }
  return {schema: 1, sampleTime: at, historyTime, live, history};
}
