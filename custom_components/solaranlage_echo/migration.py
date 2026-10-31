"""Migrate only the bundled relay address; retain account, token and sensors."""
from .api import Relay, RelayError, relay_url
from .const import DEFAULT_RELAY, LEGACY_RELAY


async def migrate_relay_address(hass, entry, session):
    """Probe the new endpoint before persisting an existing entry's new address.

    Unrelated/custom endpoints never receive a token or get rewritten. Failure
    leaves the previous configuration intact and usable via the legacy adapter.
    No enrollment, invitation, pair code or account replacement is performed.
    """
    previous = entry.data.get("relay_url")
    try:
        if relay_url(previous) != LEGACY_RELAY:
            return False
    except (ValueError, TypeError, AttributeError):
        return False
    try:
        # No credential is needed for this availability probe.
        result = await Relay(session, DEFAULT_RELAY).call("GET", "/v1/health")
    except RelayError:
        return False
    if result != {"ok": True, "api": 1}:
        return False
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, "relay_url": DEFAULT_RELAY}
    )
    return True
