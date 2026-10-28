"""Build the account-neutral widget package. No private image configuration."""
import argparse, json
from pathlib import Path

def build(output):
    root=Path(__file__).resolve().parent
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    document=json.loads((root/'document.template.json').read_text(encoding='utf-8'))
    # Access URLs are provided at runtime by the linked normal skill only.
    serialized=json.dumps(document,ensure_ascii=False,indent=2)
    if '?k=' in serialized or '?s=' in serialized or '__PRIVATE' in serialized:
        raise ValueError('Widget package must contain no access grant')
    package=Path(output)/'dataStorePackages'/manifest['manifest']['id']
    (package/'presentations').mkdir(parents=True,exist_ok=True)
    (package/'presentations/default.tpl').write_text(serialized,encoding='utf-8')
    (package/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return package

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default=str(Path(__file__).resolve().parents[2]/'dist/widget'))
    args=parser.parse_args()
    build(args.output)
    print('Account-neutral widget built; no private image address included.')
