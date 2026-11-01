"""Build stable fullscreen and the device-tested account image widget."""
import ast
from pathlib import Path

def build():
    root=Path(__file__).parent
    reader=(root/'beta_live_reader.py').read_text(encoding='utf-8')
    native=(root/'beta_live_lambda.py').read_text(encoding='utf-8')
    native='\n'.join(line for line in native.splitlines() if line.strip()!='from beta_live_reader import read_pv')
    native=native.replace('def lambda_handler(event, context):','def native_handler(event, context):')
    runtime=(root/'image_runtime.py').read_text(encoding='utf-8')
    status=(root/'status_speech.py').read_text(encoding='utf-8')
    modules=[reader,native,status,runtime]
    for filename in ('widget_publisher.py','widget_account.py','widget_runtime.py'):
        modules.append((root/filename).read_text(encoding='utf-8'))
    source='\n\n'.join(modules)
    ast.parse(source,feature_version=(3,8))
    return source

if __name__=='__main__':
    path=Path(__file__).parent/'dist/lambda_function.py'
    path.parent.mkdir(exist_ok=True)
    path.write_text(build(),encoding='utf-8')
    print('Fullscreen + account widget built; Python 3.8 syntax verified.')
