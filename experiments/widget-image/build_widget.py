"""Build private APL artifacts from the public template without logging access URLs."""
import argparse,json,re
from pathlib import Path
from urllib.parse import urlsplit,parse_qs

def build(config_path,output):
    base=json.loads(Path(config_path).read_text(encoding='utf-8'))['image_base']
    url=urlsplit(base)
    query=parse_qs(url.query,strict_parsing=True)
    if url.scheme!='https' or not url.hostname or url.username or url.password or url.port not in (None,443) or url.path!='/value.png' or url.fragment or list(query)!=['k'] or len(query['k'])!=1 or not re.fullmatch(r'[a-f0-9]{64}',query['k'][0]):
        raise ValueError('Expected a private HTTPS widget image base')
    root=Path(__file__).resolve().parent
    doc=json.loads((root/'document.template.json').read_text(encoding='utf-8'))
    widget=doc['mainTemplate']['items'][0]
    bindings=widget['item']['bind'] if widget['type']=='TouchWrapper' else widget['bind']
    next(binding for binding in bindings if binding['name']=='imageBase')['value']=base
    next(binding for binding in bindings if binding['name']=='statusImageBase')['value']=base.replace('/value.png?','/status.png?')
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    output=Path(output).resolve()
    if not any(part in ('.private','private-output') for part in output.parts):
        raise ValueError('Use a .private or private-output directory for credentials')
    package=output/'dataStorePackages'/manifest['manifest']['id']
    (package/'presentations').mkdir(parents=True,exist_ok=True)
    (package/'presentations/default.tpl').write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding='utf-8')
    (package/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--image-config',required=True,help='Private JSON file containing image_base; never commit it')
    parser.add_argument('--output',default=str(Path(__file__).resolve().parent/'private-output'))
    args=parser.parse_args()
    try:build(args.image_config,args.output)
    except Exception:
        raise SystemExit('Build failed. Check private configuration and output directory; no access URL printed.')
    print('Private widget package prepared. Do not publish the generated files.')
