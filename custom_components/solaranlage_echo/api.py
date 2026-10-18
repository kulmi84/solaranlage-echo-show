"""Bounded HTTPS requests; bearer tokens never follow redirects."""
import asyncio
from urllib.parse import urlsplit
import aiohttp


class RelayError(Exception):
    """Safe error code, without URL, payload or credentials."""


def relay_url(value):
    part = urlsplit(value)
    if (part.scheme != "https" or not part.hostname or part.username or part.password
            or part.path not in ("", "/") or part.query or part.fragment):
        raise ValueError("invalid_url")
    return value.rstrip("/")


class Relay:
    def __init__(self, session, base, token=None):
        self.session, self.base, self.token = session, relay_url(base), token

    async def call(self, method, path, payload=None):
        headers = {"User-Agent": "Solaranlage-HACS/0.1", "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        try:
            async with self.session.request(method, self.base + path, json=payload, headers=headers,
                    allow_redirects=False, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status not in (200, 201):
                    raise RelayError({401: "invalid_auth", 403: "invalid_invite", 409: "beta_full",
                                      429: "rate_limited"}.get(response.status, "cannot_connect"))
                raw = bytearray()
                async for chunk in response.content.iter_chunked(4096):
                    raw.extend(chunk)
                    if len(raw) > 8192:
                        raise RelayError("cannot_connect")
                import json
                return json.loads(raw)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
            raise RelayError("cannot_connect") from error
