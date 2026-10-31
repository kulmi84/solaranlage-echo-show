"""Private durable setup keys: retries/restarts must not create duplicate accounts."""
import asyncio
import re
import secrets
from homeassistant.helpers.storage import Store
from .const import DOMAIN

_STORAGE_KEY = DOMAIN + ".enrollment"


def _store(hass):
    return Store(hass, 1, _STORAGE_KEY, private=True, atomic_writes=True)


def _lock(hass):
    return hass.data.setdefault(DOMAIN, {}).setdefault("_enrollment_lock", asyncio.Lock())


async def installation_key(hass, base):
    async with _lock(hass):
        store = _store(hass)
        data = await store.async_load() or {}
        keys = data.get("installations", {}) if isinstance(data, dict) else {}
        if not isinstance(keys, dict):
            keys = {}
        key = keys.get(base)
        if isinstance(key, str) and re.fullmatch(r"[a-f0-9]{64}", key):
            return key
        key = secrets.token_hex(32)
        # Save before sending: the same key survives a lost reply or HA restart.
        await store.async_save({"installations": {**keys, base: key}})
        # HA Store logs some write failures instead of raising. Reopen before sending.
        saved = await _store(hass).async_load()
        if not isinstance(saved, dict) or saved.get("installations", {}).get(base) != key:
            raise OSError("enrollment_key_not_persisted")
        return key


async def forget_installation(hass, base):
    async with _lock(hass):
        store = _store(hass)
        data = await store.async_load() or {}
        keys = data.get("installations", {}) if isinstance(data, dict) else {}
        if not isinstance(keys, dict) or base not in keys:
            return
        remaining = {url: key for url, key in keys.items() if url != base}
        if remaining:
            await store.async_save({"installations": remaining})
        else:
            await store.async_remove()
