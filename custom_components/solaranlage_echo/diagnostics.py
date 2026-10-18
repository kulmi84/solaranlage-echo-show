"""No HA state values, entity IDs, URLs, tenant IDs or tokens in diagnostics."""
from .const import DOMAIN


async def async_get_config_entry_diagnostics(hass, entry):
    uploader = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    return {"version": 1, "configured_sensor_count": sum(bool(v) for v in entry.options.get("sensors", entry.data["sensors"]).values()),
            "status": uploader.data.get("status") if uploader else "unloaded",
            "history_status": uploader.data.get("history_status") if uploader else "unknown"}
