import aiohttp.web
from . import app


async def webfinger(request):
    subject = request.query['resource']

    if subject != 'acct:relay@{}'.format(request.host):
        return aiohttp.web.json_response({'error': 'user not found'}, status=404)

    actor_uri = "https://{}/actor".format(request.host)
    data = {
        "aliases": [actor_uri],
        "links": [
            {"href": actor_uri, "rel": "self", "type": "application/activity+json"},
            {"href": actor_uri, "rel": "self", "type": "application/ld+json; profile=\"https://www.w3.org/ns/activitystreams\""}
        ],
        "subject": subject
    }

    return aiohttp.web.json_response(data)


app.router.add_get('/.well-known/webfinger', webfinger)
