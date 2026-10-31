"""Account-neutral Data Store image bootstrap; no credentials embedded."""
import copy
import re

NAMESPACE = "SolarAccountImages"
KEY = "access"

def route_account_images(event, context, fallback, *, skill_id, package_id,
                         access_factory, config_factory, session_factory, publish):
    request = event.get("request", {})
    arguments = request.get("arguments", [])
    if request.get("type") != "Alexa.Presentation.APL.UserEvent":
        return fallback(event, context)
    bootstrap = (isinstance(arguments, list) and len(arguments) == 2
                 and arguments[0] == "solar.widget.images.v1"
                 and isinstance(arguments[1], dict)
                 and set(arguments[1]) == {"targetUid"}
                 and isinstance(arguments[1]["targetUid"], str)
                 and re.fullmatch(r":[0-9]{1,16}", arguments[1]["targetUid"]))
    opening = arguments == ["solar.widget.open.v1"]
    if not bootstrap and not opening:
        return fallback(event, context)
    silent = {"version": "1.0", "response": {"shouldEndSession": True}}
    system = event.get("context", {}).get("System", {})
    uri = request.get("presentationUri", "")
    pattern = r"widget://" + re.escape(skill_id) + r"(?:_development)?/" + re.escape(package_id) + r"/[A-Za-z0-9_.:-]{1,300}"
    if (system.get("application", {}).get("applicationId") != skill_id
            or not isinstance(uri, str) or not re.fullmatch(pattern, uri)):
        return silent
    if opening:
        launch = copy.deepcopy(event)
        launch["request"] = {**request, "type": "LaunchRequest"}
        launch["request"].pop("arguments", None)
        return fallback(launch, context)
    device = system.get("device", {}).get("deviceId", "")
    access = access_factory(event)
    if not access or not isinstance(device, str) or not device.startswith("amzn1.ask.device."):
        return silent
    try:
        grant = session_factory(access, config_factory())
        prefix = "https://solaranlage-display.kulmi84.workers.dev/dashboard.png?s="
        base = grant.get("base_url", "")
        lifetime = grant.get("expires_in")
        if (not isinstance(base, str) or not base.startswith(prefix)
                or not re.fullmatch(r"[A-Za-z0-9_-]{40,1000}", base[len(prefix):])
                or type(lifetime) is not int or not 60 <= lifetime <= 86400):
            return silent
        token = base[len(prefix):]
        origin = "https://solaranlage-display.kulmi84.workers.dev/widget/"
        command = {"type": "PUT_OBJECT", "namespace": NAMESPACE, "key": KEY,
                   "content": {"imageBase": origin + "value.png?s=" + token,
                               "statusImageBase": origin + "status.png?s=" + token,
                               "expiresIn": lifetime}}
        # Publisher must use this skill's client-credentials token, never request apiAccessToken.
        publish(device, [command])
    except Exception:
        # No CLEAR or deletion on errors: preserve last valid stored access and visible frame.
        pass
    return silent
