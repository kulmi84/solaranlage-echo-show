"""Build the isolated beta without changing the production build entry point."""
import ast
from pathlib import Path

ROOT = Path(__file__).parent


def build_live():
    reader = (ROOT.parent.parent / 'beta_live_reader.py').read_text(encoding='utf8')
    display = (ROOT / 'diagnostic_display.py').read_text(encoding='utf8')
    display = display.replace('def lambda_handler(event, context):', 'def probe_handler(event, context):')
    runtime = (ROOT / 'live_image_runtime.py').read_text(encoding='utf8')
    status = (ROOT / 'status_speech.py').read_text(encoding='utf8')
    source = reader + '\n\n' + display + '\n\n' + status + '\n\n' + runtime
    ast.parse(source, feature_version=(3, 8))
    target = ROOT / 'image-live'
    target.mkdir(exist_ok=True)
    (target / 'lambda_function.py').write_text(source, encoding='utf8')
    return source


if __name__ == '__main__':
    build_live()
