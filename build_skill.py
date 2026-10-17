"""Build the single-file Alexa-hosted module, independent of Windows newlines."""
import ast
from pathlib import Path


def build():
    root = Path(__file__).parent
    reader = (root / 'beta_live_reader.py').read_text(encoding='utf-8')
    display = (root / 'beta_live_lambda.py').read_text(encoding='utf-8')
    display = '\n'.join(line for line in display.splitlines()
                        if line.strip() != 'from beta_live_reader import read_pv')
    source = reader + '\n\n' + display + '\n'
    ast.parse(source, feature_version=(3, 8))
    assert 'from beta_live_reader import' not in source
    return source


if __name__ == '__main__':
    target = Path(__file__).parent / 'dist' / 'lambda_function.py'
    target.parent.mkdir(exist_ok=True)
    target.write_text(build(), encoding='utf-8')
    print('Single-file Alexa module built; Python 3.8 syntax verified.')
