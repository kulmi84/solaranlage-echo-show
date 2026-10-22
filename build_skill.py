"""Build v1.0.6: stable native helpers plus the tested local image refresh."""
import ast
from pathlib import Path

def build():
    root=Path(__file__).parent
    reader=(root/'beta_live_reader.py').read_text(encoding='utf-8')
    native=(root/'beta_live_lambda.py').read_text(encoding='utf-8')
    native='\n'.join(line for line in native.splitlines() if line.strip()!='from beta_live_reader import read_pv')
    native=native.replace('def lambda_handler(event, context):','def native_handler(event, context):')
    runtime=(root/'image_runtime.py').read_text(encoding='utf-8')
    source=reader+'\n\n'+native+'\n\n'+runtime
    ast.parse(source,feature_version=(3,8))
    return source

if __name__=='__main__':
    path=Path(__file__).parent/'dist/lambda_function.py'
    path.parent.mkdir(exist_ok=True)
    path.write_text(build(),encoding='utf-8')
    print('v1.0.6 built; Python 3.8 syntax verified.')
