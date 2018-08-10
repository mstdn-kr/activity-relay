from . import logging


import asyncio
import aiohttp
import aiohttp.web
import yaml


def load_config():
    with open('viera.yaml') as f:
         return yaml.load(f)


CONFIG = load_config()


app = aiohttp.web.Application()


from . import database
from . import actor
from . import webfinger

