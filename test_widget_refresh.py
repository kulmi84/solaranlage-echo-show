"""Exercise late/failed loads against the actual generated APL command tree."""
import copy
import json
from pathlib import Path
import re
import unittest

DOC=json.loads((Path(__file__).parent/'experiments/widget-image/document.template.json').read_text(encoding='utf-8'))
ROOT=DOC['mainTemplate']['items'][0]

def expression(value,state):
    if isinstance(value,dict):return {k:expression(v,state) for k,v in value.items()}
    if not isinstance(value,str) or not value.startswith('${'):return value
    code=value[2:-1].replace('&&',' and ').replace('||',' or ')
    code=re.sub(r'!(?!=)',' not ',code).replace('true','True').replace('false','False')
    return eval(code,{'__builtins__':{}},state)

def run(commands,state):
    for cmd in commands:
        if not expression(cmd.get('when',True),state):continue
        kind=cmd['type']
        if kind=='SetValue':state[cmd['property']]=expression(cmd['value'],state)
        elif kind=='Sequential':run(cmd['commands'],state)
        elif kind=='SendEvent':state['sent']=state.get('sent',0)+1
        else:raise AssertionError('Unexpected command '+kind)

def nodes(value):
    if isinstance(value,dict):
        yield value
        for child in value.values():yield from nodes(child)
    elif isinstance(value,list):
        for child in value:yield from nodes(child)

IMAGES={n['id']:n for n in nodes(ROOT) if n.get('type')=='Image'}

class RefreshTests(unittest.TestCase):
    def state(self):
        state={b['name']:copy.deepcopy(b['value']) for b in ROOT['bind']}
        state.update(grantReady=True,hasImage=True,activeBuffer=0,
            valueBase0='old',statusBase0='old-status',nonce0=1,
            imageBase='new',statusImageBase='new-status',elapsedTime=60000)
        return state
    def start(self,state):run(ROOT['handleTick'][0]['commands'],state)
    def event(self,state,image,event):run(IMAGES[image][event],state)
    def test_partial_failure_keeps_complete_old_frame_and_timestamp(self):
        s=self.state();old=copy.deepcopy((s['valueBase0'],s['statusBase0'],s['nonce0']));self.start(s)
        self.event(s,'valueImage0Buffer1','onLoad')
        self.event(s,'valueImage1Buffer1','onLoad')
        self.event(s,'measurementStatusBuffer1','onLoad')
        self.assertEqual(s['activeBuffer'],0)
        self.event(s,'valueImage3Buffer1','onFail')
        self.assertEqual((s['valueBase0'],s['statusBase0'],s['nonce0']),old);self.assertEqual(s['activeBuffer'],0)
        self.assertTrue(s['hasImage']);self.assertFalse(s['loading'])
        self.event(s,'valueImage3Buffer1','onLoad') # late callback cannot commit
        self.assertEqual(s['activeBuffer'],0)
    def test_automatic_retry_commits_only_after_all_four_new_images(self):
        s=self.state();self.start(s);self.event(s,'valueImage0Buffer1','onFail')
        s['elapsedTime']=61000;self.start(s)
        for image in ['valueImage0','valueImage1','valueImage3']:
            self.event(s,image+'Buffer1','onLoad');self.assertEqual(s['activeBuffer'],0)
        self.event(s,'measurementStatusBuffer1','onLoad')
        self.assertEqual(s['activeBuffer'],1);self.assertFalse(s['loading'])
        self.assertFalse(s['imageFailed']);self.assertEqual(s['nonce1'],61000)
    def test_next_refresh_writes_only_inactive_buffer(self):
        s=self.state();s.update(activeBuffer=1,nonce1=7);self.start(s)
        self.assertEqual(s['nonce1'],7);self.assertEqual(s['nonce0'],60000)
    def test_timeout_keeps_frame_and_manual_button_is_removed(self):
        s=self.state();self.start(s);s['elapsedTime']=76000
        timeout=ROOT['handleTick'][-1];self.assertTrue(expression(timeout['when'],s))
        run(timeout['commands'],s);self.assertEqual(s['activeBuffer'],0);self.assertTrue(s['imageFailed'])
        self.assertFalse(any(n.get('id')=='refreshWidget' for n in nodes(ROOT)))
        self.assertNotIn('Aktualisieren',json.dumps(ROOT))
    def test_images_load_in_background_without_replacing_visible_sources(self):
        self.assertEqual(len(IMAGES),8)
        for image in IMAGES.values():
            self.assertNotIn('display',image)
            self.assertIn('activeBuffer',image['opacity'])
            self.assertNotIn('imageBase +',image['source'])

if __name__=='__main__':unittest.main()


