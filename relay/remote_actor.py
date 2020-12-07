import logging
import aiohttp
from . import CONFIG
from .http_debug import http_debug

from cachetools import TTLCache


CACHE_SIZE = CONFIG.get('cache-size', 16384)
CACHE_TTL = CONFIG.get('cache-ttl', 3600)

ACTORS = TTLCache(CACHE_SIZE, CACHE_TTL)


async def fetch_actor(uri, headers={}, force=False):
    if uri in ACTORS and not force:
        return ACTORS[uri]

    new_headers = {'Accept': 'application/activity+json'}

    for k,v in headers.items():
        new_headers[k.capitalize()] = v

    try:
        async with aiohttp.ClientSession(trace_configs=[http_debug()]) as session:
            async with session.get(uri, headers=new_headers) as resp:
                if resp.status != 200:
                    return None
                ACTORS[uri] = (await resp.json(encoding='utf-8', content_type=None))
                return ACTORS[uri]
    except Exception as e:
        logging.info('Caught %r while fetching actor %r.', e, uri)
        return None
