import urllib.parse

import aiohttp.web

from . import app
from .database import DATABASE


nodeinfo_template = {
    # XXX - is this valid for a relay?
    'openRegistrations': True,
    'protocols': ['activitypub'],
    'services': {
        'inbound': [],
        'outbound': []
    },
    'software': {
        'name': 'activityrelay',
        'version': '0.1'
    },
    'usage': {
        'localPosts': 0,
        'users': {
            'total': 1
        }
    },
    'version': '2.0'
}


def get_peers():
    global DATABASE

    return [urllib.parse.urlsplit(inbox).hostname for inbox in DATABASE.get('relay-list', [])]


async def nodeinfo_2_0(request):
    data = nodeinfo_template.copy()
    data['metadata'] = {
        'peers': get_peers()
    }
    return aiohttp.web.json_response(data)


app.router.add_get('/nodeinfo/2.0.json', nodeinfo_2_0)


async def nodeinfo_wellknown(request):
    data = {
        'links': [
             {
                 'rel': 'http://nodeinfo.diaspora.software/ns/schema/2.0',
                 'href': 'https://{}/nodeinfo/2.0.json'.format(request.host)
             }
        ]
    }
    return aiohttp.web.json_response(data)


app.router.add_get('/.well-known/nodeinfo', nodeinfo_wellknown)
