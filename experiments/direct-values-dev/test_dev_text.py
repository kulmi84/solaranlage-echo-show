import contextlib
import copy
import io
import json
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest

HERE = Path(__file__).parent

class DevTextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        source = Path(self.temp.name) / "lambda_function.py"
        shutil.copyfile(HERE / "lambda_function.py", source)
        shutil.copyfile(HERE / "relay_config.example.json", source.with_name("relay_config.json"))
        self.ns = runpy.run_path(str(source))
        self.g = self.ns["lambda_handler"].__globals__
        self.calls = []
        self.g["read_pv"] = self.read
        self.event = {"request": {"type": "Alexa.Presentation.APL.UserEvent",
            "arguments": ["solar.widget.text.open.v1"],
            "presentationUri": "widget://" + self.ns["_direct_skill"] + "_development/SolarDirectValuesDev1611R7/test"},
            "context": {"System": {"application": {"applicationId": self.ns["_direct_skill"]},
            "user": {"userId": "amzn1.ask.account.synthetic", "accessToken": "a" * 64},
            "device": {"deviceId": "amzn1.ask.device.synthetic", "supportedInterfaces": {"Alexa.Presentation.APL": {}}}}}}

    def read(self, url, token):
        self.assertEqual(url, "https://solaranlage-dev-text-publisher.kulmi84.workers.dev/v1/pv")
        self.assertEqual(token, "a" * 64)
        self.calls.append(url)
        return {"metrics": {"power_w": 1005, "home_w": 650, "battery_soc": 55},
                "valueText": "1,01 kW", "statusText": "Stand", "stale": False}

    def invoke(self, event=None):
        with contextlib.redirect_stdout(io.StringIO()):
            return self.ns["lambda_handler"](event or self.event, None)

    def test_tap_native_fullscreen_single_read(self):
        doc = self.invoke()["response"]["directives"][0]["document"]
        self.assertEqual(len(self.calls), 1)
        self.assertNotIn('"type": "Image"', json.dumps(doc))
        self.assertIn("1611.7", json.dumps(doc))

    def test_live_uri_rejected(self):
        self.event["request"]["presentationUri"] = self.event["request"]["presentationUri"].replace("_development", "_live")
        self.assertFalse(self.invoke()["response"].get("directives"))
        self.assertFalse(self.calls)

    def test_foreign_skill_rejected(self):
        self.event["context"]["System"]["application"]["applicationId"] = "foreign"
        self.assertFalse(self.invoke()["response"].get("directives"))
        self.assertFalse(self.calls)

    def test_missing_access_rejected(self):
        self.event["context"]["System"]["user"].pop("accessToken")
        self.assertFalse(self.invoke()["response"].get("directives"))
        self.assertFalse(self.calls)

    def test_refresh_preserves_page(self):
        self.event["request"] = {"type": "Alexa.Presentation.APL.UserEvent",
            "arguments": ["solar.fullscreen.text.refresh.v1", 1], "token": "solaranlage"}
        doc = self.invoke()["response"]["directives"][0]["document"]
        self.assertEqual(doc["mainTemplate"]["items"][0]["items"][0]["initialPage"], 1)
        self.assertEqual(len(self.calls), 1)

    def test_failed_refresh_keeps_screen(self):
        self.event["request"] = {"type": "Alexa.Presentation.APL.UserEvent",
            "arguments": ["solar.fullscreen.text.refresh.v1", 0], "token": "solaranlage"}
        def failed(*args):
            raise RuntimeError("synthetic failure")
        self.g["read_pv"] = failed
        self.assertFalse(self.invoke()["response"].get("directives"))

if __name__ == "__main__":
    unittest.main()
