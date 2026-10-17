"""Read-only connectivity check using ignored local configuration."""
import json
import sys
from pathlib import Path
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from beta_live_reader import read_pv

config = json.loads(Path(__file__).resolve().parent.parent.joinpath('relay_config.json').read_text())
try:
    result = read_pv(config['url'], config['read_token'])
    print(result['valueText'], result['statusText'])
except HTTPError as error:
    if error.code != 404:
        raise SystemExit('Relay check failed: HTTP ' + str(error.code))
    print('HTTPS relay reachable; awaiting first HA value')
