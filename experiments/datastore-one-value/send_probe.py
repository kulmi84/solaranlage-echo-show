"""One-value EU Data Store probe. No network unless --send is supplied."""
import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

ENDPOINT = "https://api.eu.amazonalexa.com/v1/datastore/commands"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--send", action="store_true", help="Send exactly one PUT_OBJECT")
    args = parser.parse_args()
    commands = json.loads(Path(__file__).with_name("commands.json").read_text(encoding="utf-8"))
    expected = [{"type": "PUT_OBJECT", "namespace": "AccessProbeOne",
                 "key": "sample", "content": {"value": 731042}}]
    if commands != expected:
        parser.error("Unexpected commands; review the sender before changing the probe.")
    if not args.send:
        print(json.dumps({"mode": "dry-run", "endpoint": ENDPOINT, "commands": commands}))
        return 0
    token = os.environ.get("ALEXA_DATASTORE_ACCESS_TOKEN", "")
    device = os.environ.get("ALEXA_DEVICE_ID", "")
    if not token or not device.startswith("amzn1.ask.device."):
        parser.error("Set ALEXA_DATASTORE_ACCESS_TOKEN and a skill-specific ALEXA_DEVICE_ID locally.")
    body = {"commands": commands, "target": {"type": "DEVICES", "items": [device]}}
    request = Request(ENDPOINT, data=json.dumps(body).encode("utf-8"), method="POST",
                      headers={"Content-Type": "application/json",
                               "Authorization": "Bearer " + token})
    try:
        with build_opener(NoRedirect).open(request, timeout=25) as response:
            http_status = response.status
            result = json.load(response)
        rows = result.get("results", [])
        matches = len(rows) == 1 and rows[0].get("deviceId") == device
        kinds = [row.get("type") for row in rows]
        print(json.dumps({"http": http_status, "results": kinds,
                          "returnedTargetMatches": matches,
                          "actualWidgetRead": "NOT_VERIFIED"}))
        return 0 if http_status == 200 and matches and kinds == ["SUCCESS"] else 1
    except HTTPError as error:
        print(json.dumps({"error": "HTTP_ERROR", "http": error.code}))
    except (URLError, TimeoutError):
        print(json.dumps({"error": "NETWORK_ERROR"}))
    except (ValueError, TypeError, AttributeError):
        print(json.dumps({"error": "INVALID_RESPONSE"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
