import io,json,unittest
from datastore_publisher import publish_image_access
class Reply(io.BytesIO):
    status=200
class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.calls=[]
        self.commands=[{"type":"PUT_OBJECT","namespace":"SolarAccountImages","key":"access","content":{"imageBase":"fixture","statusImageBase":"fixture","expiresIn":3600}}]
        self.credentials={"ALEXA_CLIENT_ID":"fixture-id","ALEXA_CLIENT_SECRET":"fixture-secret"}
    def transport(self,request,timeout):
        self.calls.append(request)
        if len(self.calls)==1:return Reply(json.dumps({"access_token":"fixture-lwa"}).encode())
        return Reply(json.dumps({"results":[{"deviceId":"amzn1.ask.device.fixture","type":"SUCCESS"}]}).encode())
    def test_exact_single_device_and_scope(self):
        self.assertTrue(publish_image_access("amzn1.ask.device.fixture",self.commands,self.credentials,self.transport))
        self.assertIn(b"scope=alexa%3A%3Adatastore",self.calls[0].data)
        payload=json.loads(self.calls[1].data);self.assertEqual(payload["target"],{"type":"DEVICES","items":["amzn1.ask.device.fixture"]})
    def test_clear_rejected_before_network(self):
        with self.assertRaises(ValueError):publish_image_access("amzn1.ask.device.fixture",[{"type":"CLEAR"}],self.credentials,self.transport)
        self.assertFalse(self.calls)
    def test_other_namespace_rejected(self):
        self.commands[0]["namespace"]="Solar"
        with self.assertRaises(ValueError):publish_image_access("amzn1.ask.device.fixture",self.commands,self.credentials,self.transport)
        self.assertFalse(self.calls)
    def test_wrong_returned_device_rejected(self):
        def transport(req,timeout):
            if "auth/o2" in req.full_url:return Reply(b'{"access_token":"fixture"}')
            return Reply(b'{"results":[{"deviceId":"other","type":"SUCCESS"}]}')
        with self.assertRaises(ValueError):publish_image_access("amzn1.ask.device.fixture",self.commands,self.credentials,transport)
    def test_oversized_token_reply_rejected(self):
        with self.assertRaises(ValueError):publish_image_access("amzn1.ask.device.fixture",self.commands,self.credentials,lambda *a,**k:Reply(b'x'*16385))
if __name__=="__main__":unittest.main()
