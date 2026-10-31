"""UI-only setup: connection, sensor selection, explicit consent, enrollment."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig, TextSelector, TextSelectorConfig
from .api import Relay, RelayError, relay_url
from .const import DEFAULT_RELAY, DOMAIN, FIELDS
from .enrollment import installation_key, forget_installation


def sensor_schema(kind, defaults=None):
    defaults = defaults or {}
    return vol.Schema({
        (vol.Required(key, default=defaults[key]) if key == "power_w" and key in defaults else
         vol.Required(key) if key == "power_w" else
         vol.Optional(key, default=defaults[key]) if defaults.get(key) else vol.Optional(key)):
        EntitySelector(EntitySelectorConfig(domain="sensor"))
        for key, (_, field_kind) in FIELDS.items() if (field_kind == "energy") == (kind == "energy")
    })


def validate_sensors(hass, mapping):
    errors = {}
    energy = []
    for key, entity in mapping.items():
        if key not in FIELDS or not entity:
            continue
        state = hass.states.get(entity)
        kind = FIELDS[key][1]
        units = {"power": ("W", "kW"), "percent": ("%",), "energy": ("Wh", "kWh", "MWh")}[kind]
        if state is None or state.attributes.get("unit_of_measurement") not in units:
            errors[key] = "invalid_sensor"
        if kind == "energy":
            if entity in energy:
                errors[key] = "duplicate_energy"
            energy.append(entity)
            if state and state.attributes.get("state_class") not in ("total", "total_increasing"):
                errors[key] = "invalid_energy"
    return errors


class SolarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            if user_input.get("custom_server"):
                return await self.async_step_server()
            try:
                base = relay_url(user_input.get("relay_url", DEFAULT_RELAY))
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                relay = Relay(async_get_clientsession(self.hass), base)
                await relay.call("GET", "/v1/health")
                self._connection = {"relay_url": base, "mode": "invitation"}
                self._mapping = {}
                # Accept an already-open old flow without forcing a second invitation entry.
                if isinstance(user_input.get("invite"), str) and user_input["invite"].strip():
                    self._connection["invite"] = user_input["invite"].strip()
                    return await self.async_step_live()
                try:
                    capabilities = await relay.call("GET", "/v2/enrollment")
                except RelayError as error:
                    if str(error) != "enrollment_unsupported":
                        raise
                    capabilities = {"mode": "invitation"}
                if not isinstance(capabilities, dict) or capabilities.get("mode") not in ("automatic", "invitation"):
                    raise RelayError("cannot_connect")
                self._connection["mode"] = capabilities["mode"]
                if capabilities["mode"] == "automatic":
                    return await self.async_step_live()
                return await self.async_step_invite()
            except ValueError:
                errors["base"] = "invalid_url"
            except RelayError as error:
                errors["base"] = str(error)
        return self.async_show_form(step_id="user", data_schema=vol.Schema({
            vol.Optional("custom_server", default=False): bool,
        }), errors=errors)

    async def async_step_server(self, user_input=None):
        if user_input is not None:
            result = await self.async_step_user({"relay_url": user_input["relay_url"]})
            if result.get("step_id") != "user":
                return result
            errors = result.get("errors", {})
        else:
            errors = {}
        return self.async_show_form(step_id="server", data_schema=vol.Schema({
            vol.Required("relay_url", default=DEFAULT_RELAY): str,
        }), errors=errors)

    async def async_step_invite(self, user_input=None):
        errors = {}
        if user_input is not None:
            invitation = user_input.get("invite", "").strip()
            if invitation:
                self._connection["invite"] = invitation
                return await self.async_step_live()
            errors["base"] = "invalid_invite"
        return self.async_show_form(step_id="invite", data_schema=vol.Schema({
            vol.Required("invite"): TextSelector(TextSelectorConfig(type="password")),
        }), errors=errors)

    async def async_step_live(self, user_input=None):
        errors = validate_sensors(self.hass, user_input) if user_input else {}
        if user_input and not errors:
            self._mapping.update(user_input)
            return await self.async_step_energy()
        return self.async_show_form(step_id="live", data_schema=sensor_schema("live", user_input), errors=errors)

    async def async_step_energy(self, user_input=None):
        errors = validate_sensors(self.hass, user_input) if user_input is not None else {}
        if user_input is not None and not errors:
            self._mapping.update(user_input)
            return await self.async_step_consent()
        return self.async_show_form(step_id="energy", data_schema=sensor_schema("energy", user_input), errors=errors)

    async def async_step_consent(self, user_input=None):
        errors = {}
        if user_input:
            if not user_input["consent"]:
                errors["base"] = "consent_required"
            else:
                try:
                    connection = self._connection
                    if connection["mode"] == "automatic":
                        key = await installation_key(self.hass, connection["relay_url"])
                        path = "/v2/enroll"
                        payload = {"installation_key": key, "timezone": self.hass.config.time_zone}
                    else:
                        path = "/v1/enroll"
                        payload = {"invite": connection["invite"], "timezone": self.hass.config.time_zone}
                    result = await Relay(async_get_clientsession(self.hass), connection["relay_url"]).call("POST", path, payload)
                    if (not isinstance(result, dict) or not isinstance(result.get("write_token"), str)
                            or len(result["write_token"]) < 32 or not isinstance(result.get("tenant_id"), str)
                            or not result["tenant_id"]):
                        raise RelayError("cannot_connect")
                    return self.async_create_entry(title="Solaranlage Echo Show", data={
                        "relay_url": connection["relay_url"], "write_token": result["write_token"],
                        "tenant_id": result["tenant_id"], "sensors": self._mapping})
                except RelayError as error:
                    errors["base"] = str(error)
                    if str(error) == "registration_revoked":
                        # Do not auto-retry: a new confirmation starts a fresh setup key.
                        try:
                            await forget_installation(self.hass, self._connection["relay_url"])
                        except (OSError, ValueError, HomeAssistantError):
                            errors["base"] = "cannot_connect"
                except (OSError, ValueError, HomeAssistantError):
                    errors["base"] = "cannot_connect"
        return self.async_show_form(step_id="consent", data_schema=vol.Schema({vol.Required("consent", default=False): bool}), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SolarOptionsFlow(config_entry)


class SolarOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self._entry = entry

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(step_id="init", menu_options=["live", "link", "erase"])

    async def async_step_live(self, user_input=None):
        errors = validate_sensors(self.hass, user_input) if user_input else {}
        if user_input and not errors:
            self._mapping = dict(user_input)
            return await self.async_step_energy()
        return self.async_show_form(step_id="live", data_schema=sensor_schema("live", user_input or self._entry.options.get("sensors", self._entry.data["sensors"])), errors=errors)

    async def async_step_energy(self, user_input=None):
        errors = validate_sensors(self.hass, user_input) if user_input is not None else {}
        if user_input is not None and not errors:
            self._mapping.update(user_input)
            return self.async_create_entry(title="", data={"sensors": self._mapping})
        return self.async_show_form(step_id="energy", data_schema=sensor_schema("energy", user_input if user_input is not None else self._entry.options.get("sensors", self._entry.data["sensors"])), errors=errors)

    async def async_step_link(self, user_input=None):
        if user_input is not None:
            return self.async_abort(reason="link_ready")
        try:
            result = await Relay(async_get_clientsession(self.hass), self._entry.data["relay_url"], self._entry.data["write_token"]).call("POST", "/v1/pair", {})
        except RelayError:
            return self.async_abort(reason="cannot_connect")
        return self.async_show_form(step_id="link", data_schema=vol.Schema({}), description_placeholders={
            "code": str(result["pair_code"]), "expires": "10"})

    async def async_step_erase(self, user_input=None):
        errors = {}
        if user_input and user_input["confirm"]:
            try:
                await Relay(async_get_clientsession(self.hass), self._entry.data["relay_url"], self._entry.data["write_token"]).call("DELETE", "/v1/account")
                try:
                    await forget_installation(self.hass, self._entry.data["relay_url"])
                except (OSError, ValueError, HomeAssistantError):
                    # Server deletion has succeeded. A stale local key is rejected on reuse.
                    pass
                return self.async_create_entry(title="", data={**self._entry.options, "revoked": True})
            except RelayError as error:
                errors["base"] = str(error)
        return self.async_show_form(step_id="erase", data_schema=vol.Schema({vol.Required("confirm", default=False): bool}), errors=errors)
