import aiohttp
from .database import DATABASE


ACTORS = DATABASE.get("actors", {})
async def fetch_actor(uri, force=False):
    if uri in ACTORS and not force:
        return ACTORS[uri]

    async with aiohttp.ClientSession() as session:
        async with session.get(uri, headers={'Accept': 'application/activity+json'}) as resp:
            ACTORS[uri] = (await resp.json(content_type=None))
            DATABASE["actors"] = ACTORS
            return ACTORS[uri]
