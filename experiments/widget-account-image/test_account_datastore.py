import copy
import json
import unittest
from account_datastore import route_account_images

SKILL = "amzn1.ask.skill.fixture"
PACKAGE = "SolarAccountImage"
TOKEN = "x" * 64
class AccountDataStoreTests(unittest.TestCase):
    def setUp(self):
        self.published=[]; self.fallback=[]
        self.event={"request":{"type":"Alexa.Presentation.APL.UserEvent","arguments":["solar.widget.images.v1",{"targetUid":":1000"}],"presentationUri":"widget://"+SKILL+"_development/"+PACKAGE+"/instance"},"context":{"System":{"application":{"applicationId":SKILL},"device":{"deviceId":"amzn1.ask.device.fixture"},"user":{"accessToken":"linked-fixture"}}}}
    def run_route(self,event=None,grant=None,access="linked-fixture",publish=None):
        return route_account_images(event or self.event,None,lambda e,c:self.fallback.append(e) or "fallback",skill_id=SKILL,package_id=PACKAGE,access_factory=lambda e:access,config_factory=lambda:{},session_factory=lambda a,c:grant or {"base_url":"https://solaranlage-display.kulmi84.workers.dev/dashboard.png?s="+TOKEN,"expires_in":3600},publish=publish or (lambda device,cmd:self.published.append((device,cmd))))
    def test_current_device_and_account_grant(self):
        result=self.run_route(); self.assertEqual(result["response"],{"shouldEndSession":True});self.assertEqual(self.published[0][0],"amzn1.ask.device.fixture");command=self.published[0][1][0];self.assertEqual(command["namespace"],"SolarAccountImages");self.assertEqual(command["content"]["expiresIn"],3600);self.assertNotIn("linked-fixture",json.dumps(command))
    def test_foreign_skill_rejected(self):
        self.event["context"]["System"]["application"]["applicationId"]="other";self.run_route();self.assertFalse(self.published)
    def test_foreign_package_rejected(self):
        self.event["request"]["presentationUri"]="widget://"+SKILL+"/other/instance";self.run_route();self.assertFalse(self.published)
    def test_missing_link_rejected(self):
        self.run_route(access=None);self.assertFalse(self.published)
    def test_bad_grant_and_expiry_rejected(self):
        for grant in [{"base_url":"https://other.invalid/?s="+TOKEN,"expires_in":3600},{"base_url":"https://solaranlage-display.kulmi84.workers.dev/dashboard.png?s="+TOKEN,"expires_in":0}]:self.run_route(grant=grant)
        self.assertFalse(self.published)
    def test_transient_failure_does_not_clear(self):
        self.run_route(publish=lambda *a:(_ for _ in ()).throw(TimeoutError()));self.assertFalse(self.published)
    def test_launch_unchanged(self):
        e={"request":{"type":"LaunchRequest"}};self.assertEqual(self.run_route(e),"fallback");self.assertEqual(self.fallback,[e])
    def test_open_translates_only_request(self):
        self.event["request"]["arguments"]=["solar.widget.open.v1"];original=copy.deepcopy(self.event);self.assertEqual(self.run_route(),"fallback");self.assertEqual(self.fallback[0]["request"]["type"],"LaunchRequest");self.assertEqual(self.event,original)

if __name__ == "__main__":unittest.main()
