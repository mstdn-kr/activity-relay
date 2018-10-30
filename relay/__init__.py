from . import logging


import asyncio
import aiohttp
import aiohttp.web
import yaml


def load_config():
    with open('relay.yaml') as f:
         return yaml.load(f)


CONFIG = load_config()


from .http_signatures import http_signatures_middleware


app = aiohttp.web.Application(middlewares=[
    http_signatures_middleware
])


from . import database
from . import actor
from . import webfinger

