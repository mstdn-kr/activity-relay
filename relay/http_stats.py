import aiohttp.web

from . import app
from .http_debug import STATS


async def stats(request):
    return aiohttp.web.json_response(STATS)


app.router.add_get('/stats', stats)
