"""Bounded Data Store publisher for a single current widget device."""
import json
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler

class NoPublisherRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def publish_image_access(device, commands, credentials, http_open=None):
    if not isinstance(device,str) or not device.startswith("amzn1.ask.device."):
        raise ValueError("Invalid device")
    if (len(commands)!=1 or commands[0].get("type")!="PUT_OBJECT"
            or commands[0].get("namespace")!="SolarAccountImages"
            or commands[0].get("key")!="access"):
        raise ValueError("Unexpected write scope")
    open_request=http_open or build_opener(NoPublisherRedirect()).open
    payload=urlencode({"grant_type":"client_credentials",
                       "client_id":credentials["ALEXA_CLIENT_ID"],
                       "client_secret":credentials["ALEXA_CLIENT_SECRET"],
                       "scope":"alexa::datastore"}).encode()
    req=Request("https://api.amazon.com/auth/o2/token",data=payload,method="POST",
                headers={"Content-Type":"application/x-www-form-urlencoded"})
    with open_request(req,timeout=4) as response:
        raw=response.read(16385)
    if len(raw)>16384:raise ValueError("Oversize auth response")
    token=json.loads(raw)["access_token"]
    body={"commands":commands,"target":{"type":"DEVICES","items":[device]}}
    req=Request("https://api.eu.amazonalexa.com/v1/datastore/commands",
                data=json.dumps(body).encode(),method="POST",
                headers={"Content-Type":"application/json","Authorization":"Bearer "+token})
    with open_request(req,timeout=4) as response:
        raw=response.read(16385)
        status=response.status
    if len(raw)>16384:raise ValueError("Oversize write response")
    rows=json.loads(raw).get("results",[])
    if status!=200 or len(rows)!=1 or rows[0].get("deviceId")!=device or rows[0].get("type")!="SUCCESS":
        raise ValueError("Write not confirmed")
    return True
