import unittest
from skill_registration import registration_requests

class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.config=dict(enabled=True, stage='live', package_id='ProposedOnly', skill_id='skill')
        self.event={'context':{'System':{'application':{'applicationId':'skill'},'user':{'userId':'amzn1.ask.account.synthetic','accessToken':'a'*64},'device':{'deviceId':'amzn1.ask.device.synthetic'}}}, 'request':{'type':'Alexa.Presentation.APL.UserEvent','arguments':['solar.widget.open.v1'],'timestamp':'2026-11-16T15:00:00Z','presentationUri':'widget://skill/ProposedOnly/instance'}}
    def test_register_uses_current_context_and_no_household_override(self):
        action,data,token=registration_requests(self.event,self.config)[0]
        self.assertEqual(action,'register'); self.assertEqual(token,'a'*64)
        self.assertNotIn('household',data); self.assertEqual(data['instanceId'],'instance')
    def test_dev_uri_cannot_register_live(self):
        self.event['request']['presentationUri']='widget://skill_development/ProposedOnly/instance'
        with self.assertRaisesRegex(ValueError,'presentation'): registration_requests(self.event,self.config)
    def test_no_token_cannot_register(self):
        del self.event['context']['System']['user']['accessToken']
        with self.assertRaisesRegex(ValueError,'linked_access'): registration_requests(self.event,self.config)
    def test_missing_instance_waits_without_inventing_identity(self):
        self.event['request'].update(type='Alexa.DataStore.PackageManager.UsagesInstalled',payload={'packageId':'ProposedOnly','usages':[{'location':'FAVORITE'}]})
        self.assertEqual(registration_requests(self.event,self.config),[])
    def test_disabled_adapter_does_nothing(self):
        self.assertEqual(registration_requests(self.event,dict(self.config,enabled=False)),[])
if __name__=='__main__': unittest.main()
