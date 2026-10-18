"""Push selected statistics without YAML, HA tokens or inbound ports."""
import asyncio
from datetime import timedelta
import logging
from homeassistant.const import Platform, EVENT_HOMEASSISTANT_STARTED
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util
from .api import Relay, RelayError
from .const import DOMAIN, ENERGY_KEYS
from .payload import energy_values, live_values, numeric

_LOGGER = logging.getLogger(__name__)


class SolarUploader(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(hass, _LOGGER, name="Solaranlage upload", config_entry=entry)
        self.entry = entry
        self.relay = Relay(async_get_clientsession(hass), entry.data["relay_url"], entry.data["write_token"])
        self.lock = asyncio.Lock()
        self.closed = False
        self.last_history = None
        self.data = {"status": "waiting", "last_upload": None, "history_status": "waiting"}

    @property
    def mapping(self):
        return self.entry.options.get("sensors", self.entry.data["sensors"])

    async def statistics(self, start, now, period):
        ids = list(dict.fromkeys(self.mapping[key] for key in ENERGY_KEYS if self.mapping.get(key)))
        if not ids:
            return {}
        try:
            return await self.hass.services.async_call("recorder", "get_statistics", {
                "statistic_ids": ids, "start_time": start.isoformat(), "end_time": now.isoformat(),
                "period": period, "types": ["change"], "units": {"energy": "kWh"},
            }, blocking=True, return_response=True)
        except Exception:
            # Recorder may be starting or lack statistics. Never log household data.
            return {}

    async def upload(self, _now=None):
        if self.closed or self.entry.options.get("revoked") or self.lock.locked():
            return
        async with self.lock:
            now = dt_util.now()
            state = dict(self.data)
            payload = live_values(self.mapping, self.hass.states.get)
            if payload["power_w"] is None:
                state["status"] = "sensor_missing"
                self.async_set_updated_data(state)
                return
            stats = await self.statistics(now.replace(hour=0, minute=0, second=0, microsecond=0), now, "day")
            payload.update(energy_values(self.mapping, stats, "today"), energy_date=now.date().isoformat())
            state["missing_values"] = [key for key, value in payload.items() if value is None]
            try:
                await self.relay.call("POST", "/v1/pv", payload)
                state.update(status="online", last_upload=dt_util.utcnow().isoformat())
                bucket = (now.year, now.month, now.day, now.hour // 6)
                if self.last_history != bucket:
                    month = await self.statistics(now.replace(day=1, hour=0, minute=0, second=0, microsecond=0), now, "month")
                    year = await self.statistics(now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0), now, "year")
                    history = {"kind": "history", "month_id": now.strftime("%Y-%m"), "year_id": now.strftime("%Y"),
                               **energy_values(self.mapping, month, "month"), **energy_values(self.mapping, year, "year")}
                    await self.relay.call("POST", "/v1/pv", history)
                    # Retry unavailable recorder results next minute rather than freezing them for six hours.
                    selected = [self.mapping[key] for key in ENERGY_KEYS if self.mapping.get(key)]
                    def has_statistics(response, entity):
                        rows = (response or {}).get("statistics", {}).get(entity, [])
                        return bool(rows) and all(isinstance(row, dict) and numeric(row.get("change")) is not None for row in rows)
                    valid_stats = all(has_statistics(response, entity) for response in (month, year) for entity in selected)
                    if selected and valid_stats:
                        self.last_history = bucket
                        state["history_status"] = "online"
                    elif not selected:
                        self.last_history = bucket
                        state["history_status"] = "not_configured"
                    else:
                        state["history_status"] = "statistics_missing"
            except RelayError as error:
                state["status"] = str(error)
            self.async_set_updated_data(state)


async def async_setup_entry(hass, entry):
    uploader = SolarUploader(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = uploader
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    entry.async_on_unload(async_track_time_interval(hass, uploader.upload, timedelta(seconds=60)))
    entry.async_on_unload(entry.add_update_listener(_reload))
    if hass.is_running:
        await uploader.upload()
    else:
        async def started(_event):
            await uploader.upload()
        entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, started))
    return True


async def _reload(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    uploader = hass.data[DOMAIN][entry.entry_id]
    uploader.closed = True
    if await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR]):
        hass.data[DOMAIN].pop(entry.entry_id)
        # Wait for an in-flight upload before allowing reload/removal to complete.
        async with uploader.lock:
            pass
        return True
    uploader.closed = False
    return False
