import aiohttp
from . import CONFIG
from .http_debug import http_debug

from cachetools import TTLCache


CACHE_SIZE = CONFIG.get('cache-size', 16384)
CACHE_TTL = CONFIG.get('cache-ttl', 3600)

ACTORS = TTLCache(CACHE_SIZE, CACHE_TTL)


async def fetch_actor(uri, force=False):
    if uri in ACTORS and not force:
        return ACTORS[uri]

    async with aiohttp.ClientSession(trace_configs=[http_debug()]) as session:
        async with session.get(uri, headers={'Accept': 'application/activity+json'}) as resp:
            ACTORS[uri] = (await resp.json(encoding='utf-8', content_type=None))
            return ACTORS[uri]
