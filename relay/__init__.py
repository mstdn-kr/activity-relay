from . import logging


import asyncio
import aiohttp
import aiohttp.web
import yaml


def load_config():
    with open('relay.yaml') as f:
        yaml_file = yaml.load(f)
        whitelist = yaml_file['ap'].get('whitelist', [])
        blocked = yaml_file['ap'].get('blocked_instances', [])

        config = {
            'db': yaml_file.get('db', 'relay.jsonld'),
            'listen': yaml_file.get('listen', '0.0.0.0'),
            'port': int(yaml_file.get('port', 8080)),
            'note': yaml_file.get('note', 'Make a note about your instance here.'),
            'ap': {
                'blocked_instances': [] if blocked is None else blocked,
                'host': yaml_file['ap'].get('host', 'localhost'),
                'whitelist': [] if whitelist is None else whitelist,
                'whitelist_enabled': yaml_file['ap'].get('whitelist_enabled', False)
            }
        }
        return config


CONFIG = load_config()


from .http_signatures import http_signatures_middleware


app = aiohttp.web.Application(middlewares=[
    http_signatures_middleware
])


from . import database
from . import actor
from . import webfinger
from . import default
from . import nodeinfo
from . import http_stats
