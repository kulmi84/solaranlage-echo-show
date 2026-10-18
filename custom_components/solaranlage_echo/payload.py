"""Pure conversions. Unknown is never silently converted to zero."""
import math
from .const import ENERGY_KEYS, FIELDS


def numeric(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (ValueError, TypeError):
        return None
    return value if math.isfinite(value) and 0 <= value <= 10_000_000 else None


def live_values(mapping, get_state):
    result = {}
    for key, (_, kind) in FIELDS.items():
        if kind == "energy":
            continue
        state = get_state(mapping.get(key, "")) if mapping.get(key) else None
        value = numeric(state.state) if state else None
        unit = state.attributes.get("unit_of_measurement") if state else None
        if kind == "power":
            value = value * (1000 if unit == "kW" else 1) if value is not None and unit in ("W", "kW") else None
            if value is not None and value > 10_000_000:
                value = None
        elif unit != "%" or (value is not None and value > 100):
            value = None
        result[key] = value
    return result


def energy_values(mapping, response, prefix):
    stats = response.get("statistics", {}) if isinstance(response, dict) else {}
    def total(key):
        rows = stats.get(mapping.get(key), [])
        if not isinstance(rows, list) or not rows:
            return None
        values = [numeric(row.get("change")) if isinstance(row, dict) else None for row in rows]
        return sum(values) if all(value is not None for value in values) else None
    pv, bkw, imp, exp, charge, discharge = (total(key) for key in ENERGY_KEYS)
    return {
        prefix + "_pv_kwh": pv + bkw if pv is not None and bkw is not None else None,
        prefix + "_home_kwh": max(0, pv + bkw + imp + discharge - exp - charge)
        if all(value is not None for value in (pv, bkw, imp, exp, charge, discharge)) else None,
        prefix + "_grid_import_kwh": imp,
        prefix + "_grid_export_kwh": exp,
        prefix + "_battery_charge_kwh": charge,
        prefix + "_battery_discharge_kwh": discharge,
    }
