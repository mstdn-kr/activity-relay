from . import logging


import asyncio
import aiohttp
import aiohttp.web
import yaml


def load_config():
    with open('relay.yaml') as f:
        options = {}

        ## Prevent a warning message for pyyaml 5.1+
        if getattr(yaml, 'FullLoader', None):
            options['Loader'] = yaml.FullLoader

        yaml_file = yaml.load(f, **options)

        config = {
            'db': yaml_file.get('db', 'relay.jsonld'),
            'listen': yaml_file.get('listen', '0.0.0.0'),
            'port': int(yaml_file.get('port', 8080)),
            'note': yaml_file.get('note', 'Make a note about your instance here.'),
            'ap': {
                'blocked_software': [v.lower() for v in yaml_file['ap'].get('blocked_software', [])],
                'blocked_instances': yaml_file['ap'].get('blocked_instances', []),
                'host': yaml_file['ap'].get('host', 'localhost'),
                'whitelist': yaml_file['ap'].get('whitelist', []),
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
