import io,json,unittest
from urllib.error import HTTPError
from skill.skill_registration import send_registration

class BusyDelivery(unittest.TestCase):
 def setUp(self):
  self.cfg={'origin':'https://solaranlage-echo-werte.kulmi84.workers.dev','registration_secret':'r'*40,
            'stage':'live','package_id':'SolarAccountImageBuild1211'}
  self.call=('refresh',{'trigger':'minute'},None)
 def error(self,code,message):
  def opening(*a,**k):raise HTTPError('https://test',code,'error',{},io.BytesIO(json.dumps({'error':message}).encode()))
  return opening
 def test_only_exact_live_store_busy_error_is_retryable(self):
  self.assertEqual(send_registration(self.call,self.cfg,opener=self.error(503,'delivery_busy')),
                   {'registered':False,'deliveryBusy':True})
  for status,message in [(401,'unauthorized'),(503,'delivery_failed'),(503,'not_configured')]:
   with self.assertRaises(HTTPError):send_registration(self.call,self.cfg,opener=self.error(status,message))
 def test_dev_and_removal_keep_original_error_semantics(self):
  for cfg,call in [({**self.cfg,'stage':'development','package_id':'Solaranlage1811'},self.call),
                   (self.cfg,('remove',{},None))]:
   with self.assertRaises(HTTPError):send_registration(call,cfg,opener=self.error(503,'delivery_busy'))
