"""UI-only setup: connection, sensor selection, explicit consent, enrollment."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig, TextSelector, TextSelectorConfig
from .api import Relay, RelayError, relay_url
from .const import DEFAULT_RELAY, DOMAIN, FIELDS


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
        if user_input:
            try:
                base = relay_url(user_input["relay_url"])
                await Relay(async_get_clientsession(self.hass), base).call("GET", "/v1/health")
                self._connection = {"relay_url": base, "invite": user_input["invite"].strip()}
                self._mapping = {}
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return await self.async_step_live()
            except ValueError:
                errors["base"] = "invalid_url"
            except RelayError as error:
                errors["base"] = str(error)
        return self.async_show_form(step_id="user", data_schema=vol.Schema({
            vol.Required("relay_url", default=DEFAULT_RELAY): str,
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
                    result = await Relay(async_get_clientsession(self.hass), connection["relay_url"]).call(
                        "POST", "/v1/enroll", {"invite": connection["invite"], "timezone": self.hass.config.time_zone})
                    if not isinstance(result.get("write_token"), str) or len(result["write_token"]) < 32 or not isinstance(result.get("tenant_id"), str):
                        raise RelayError("cannot_connect")
                    return self.async_create_entry(title="Solaranlage Echo Show", data={
                        "relay_url": connection["relay_url"], "write_token": result["write_token"],
                        "tenant_id": result["tenant_id"], "sensors": self._mapping})
                except RelayError as error:
                    errors["base"] = str(error)
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
                return self.async_create_entry(title="", data={**self._entry.options, "revoked": True})
            except RelayError as error:
                errors["base"] = str(error)
        return self.async_show_form(step_id="erase", data_schema=vol.Schema({vol.Required("confirm", default=False): bool}), errors=errors)
