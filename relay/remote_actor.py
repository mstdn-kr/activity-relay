import aiohttp
from .database import DATABASE
from .http_debug import http_debug


ACTORS = DATABASE.get("actors", {})
async def fetch_actor(uri, force=False):
    if uri in ACTORS and not force:
        return ACTORS[uri]

    async with aiohttp.ClientSession(trace_configs=[http_debug()]) as session:
        async with session.get(uri, headers={'Accept': 'application/activity+json'}) as resp:
            ACTORS[uri] = (await resp.json(encoding='utf-8', content_type=None))
            DATABASE["actors"] = ACTORS
            return ACTORS[uri]
