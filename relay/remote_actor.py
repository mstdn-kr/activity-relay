import logging
import aiohttp

from cachetools import TTLCache
from datetime import datetime
from urllib.parse import urlsplit

from . import CONFIG
from .http_debug import http_debug


CACHE_SIZE = CONFIG.get('cache-size', 16384)
CACHE_TTL = CONFIG.get('cache-ttl', 3600)

ACTORS = TTLCache(CACHE_SIZE, CACHE_TTL)


async def fetch_actor(uri, headers={}, force=False, sign_headers=True):
    if uri in ACTORS and not force:
        return ACTORS[uri]

    from .actor import PRIVKEY
    from .http_signatures import sign_headers

    url = urlsplit(uri)
    key_id = 'https://{}/actor#main-key'.format(CONFIG['ap']['host'])

    headers.update({
        'Accept': 'application/activity+json',
        'User-Agent': 'ActivityRelay'
    })

    if sign_headers:
        headers.update({
            '(request-target)': 'get {}'.format(url.path),
            'Date': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT'),
            'Host': url.netloc
        })

        headers['signature'] = sign_headers(headers, PRIVKEY, key_id)
        headers.pop('(request-target)')
        headers.pop('Host')

    try:
        async with aiohttp.ClientSession(trace_configs=[http_debug()]) as session:
            async with session.get(uri, headers=headers) as resp:

                if resp.status != 200:
                    return None

                ACTORS[uri] = (await resp.json(encoding='utf-8', content_type=None))
                return ACTORS[uri]

    except Exception as e:
        logging.info('Caught %r while fetching actor %r.', e, uri)
        return None
