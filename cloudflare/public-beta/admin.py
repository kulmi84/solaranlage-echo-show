"""Create a one-use beta invitation, saving it locally rather than logging it."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True, help='Private JSON: relay_url and admin_token')
    parser.add_argument('--out', required=True, help='New private invitation file; never overwritten')
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    url = config['relay_url'].rstrip('/')
    part = urlsplit(url)
    if part.scheme != 'https' or not part.hostname or part.username or part.password or part.path or part.query or part.fragment:
        raise SystemExit('Invalid HTTPS relay origin.')
    target = Path(args.out)
    # Reserve the file before consuming a server-side invitation slot.
    with target.open('x', encoding='utf-8') as output:
        request = Request(url + '/admin/invites', data=b'{}', method='POST', headers={
            'Authorization': 'Bearer ' + config['admin_token'], 'Content-Type': 'application/json', 'User-Agent': 'Solaranlage-Admin/0.1'})
        with build_opener(NoRedirect).open(request, timeout=15) as response:
            invitation = json.loads(response.read(4096))
        output.write(json.dumps(invitation, indent=2))
    print('Einmalige Einladung in privater Datei gespeichert. Gültig für sieben Tage.')


if __name__ == '__main__': main()
