import aiohttp
import aiohttp.web
import asyncio
import logging
import uuid
import re
import urllib.parse
import simplejson as json
import cgi
from Crypto.PublicKey import RSA
from .database import DATABASE
from .http_debug import http_debug


# generate actor keys if not present
if "actorKeys" not in DATABASE:
    logging.info("No actor keys present, generating 4096-bit RSA keypair.")

    privkey = RSA.generate(4096)
    pubkey = privkey.publickey()

    DATABASE["actorKeys"] = {
        "publicKey": pubkey.exportKey('PEM'),
        "privateKey": privkey.exportKey('PEM')
    }


PRIVKEY = RSA.importKey(DATABASE["actorKeys"]["privateKey"])
PUBKEY = PRIVKEY.publickey()


from . import app, CONFIG
from .remote_actor import fetch_actor


AP_CONFIG = CONFIG.get('ap', {'host': 'localhost','blocked_instances':[]})


async def actor(request):
    data = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "endpoints": {
            "sharedInbox": "https://{}/inbox".format(request.host)
        },
        "followers": "https://{}/followers".format(request.host),
        "following": "https://{}/following".format(request.host),
        "inbox": "https://{}/inbox".format(request.host),
        "sharedInbox": "https://{}/inbox".format(request.host),
        "name": "ActivityRelay",
        "type": "Application",
        "id": "https://{}/actor".format(request.host),
        "publicKey": {
            "id": "https://{}/actor#main-key".format(request.host),
            "owner": "https://{}/actor".format(request.host),
            "publicKeyPem": DATABASE["actorKeys"]["publicKey"]
        },
        "summary": "ActivityRelay bot",
        "preferredUsername": "relay",
        "url": "https://{}/actor".format(request.host)
    }
    return aiohttp.web.json_response(data)


app.router.add_get('/actor', actor)


from .http_signatures import sign_headers


get_actor_inbox = lambda actor: actor.get('endpoints', {}).get('sharedInbox', actor['inbox'])


async def push_message_to_actor(actor, message, our_key_id):
    inbox = get_actor_inbox(actor)

    url = urllib.parse.urlsplit(inbox)

    # XXX: Digest
    data = json.dumps(message)
    headers = {
        '(request-target)': 'post {}'.format(url.path),
        'Content-Length': str(len(data)),
        'Content-Type': 'application/activity+json',
        'User-Agent': 'ActivityRelay'
    }
    headers['signature'] = sign_headers(headers, PRIVKEY, our_key_id)
    headers.pop('(request-target)')

    logging.debug('%r >> %r', inbox, message)

    async with aiohttp.ClientSession(trace_configs=[http_debug()]) as session:
        async with session.post(inbox, data=data, headers=headers) as resp:
            resp_payload = await resp.text()
            logging.debug('%r >> resp %r', inbox, resp_payload)


async def follow_remote_actor(actor_uri):
    logging.info('following: %r', actor_uri)

    actor = await fetch_actor(actor_uri)

    message = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "Follow",
        "to": [actor['id']],
        "object": actor['id'],
        "id": "https://{}/activities/{}".format(AP_CONFIG['host'], uuid.uuid4()),
        "actor": "https://{}/actor".format(AP_CONFIG['host'])
    }
    await push_message_to_actor(actor, message, "https://{}/actor#main-key".format(AP_CONFIG['host']))


async def unfollow_remote_actor(actor_uri):
    logging.info('unfollowing: %r', actor_uri)

    actor = await fetch_actor(actor_uri)

    message = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "Undo",
        "to": [actor['id']],
        "object": {
             "type": "Follow",
             "object": actor_uri,
             "actor": actor['id'],
             "id": "https://{}/activities/{}".format(AP_CONFIG['host'], uuid.uuid4())
        },
        "id": "https://{}/activities/{}".format(AP_CONFIG['host'], uuid.uuid4()),
        "actor": "https://{}/actor".format(AP_CONFIG['host'])
    }
    await push_message_to_actor(actor, message, "https://{}/actor#main-key".format(AP_CONFIG['host']))


tag_re = re.compile(r'(<!--.*?-->|<[^>]*>)')
def strip_html(data):
    no_tags = tag_re.sub('', data)
    return cgi.escape(no_tags)


def distill_inboxes(actor):
    global DATABASE

    inbox = get_actor_inbox(actor)
    targets = [target for target in DATABASE.get('relay-list', []) if target != inbox]

    assert inbox not in targets

    return targets


def distill_object_id(activity):
    logging.debug('>> determining object ID for %r', activity['object'])
    obj = activity['object']

    if isinstance(obj, str):
        return obj

    return obj['id']


async def handle_relay(actor, data, request):
    object_id = distill_object_id(data)

    # don't relay mastodon announces -- causes LRP fake direction issues
    if data['type'] == 'Announce' and len(data.get('cc', [])) > 0:
        return

    message = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "Announce",
        "to": ["https://{}/actor/followers".format(request.host)],
        "actor": "https://{}/actor".format(request.host),
        "object": object_id,
        "id": "https://{}/activities/{}".format(request.host, uuid.uuid4())
    }

    logging.debug('>> relay: %r', message)

    inboxes = distill_inboxes(actor)

    futures = [push_message_to_actor({'inbox': inbox}, message, 'https://{}/actor#main-key'.format(request.host)) for inbox in inboxes]
    asyncio.ensure_future(asyncio.gather(*futures))


async def handle_follow(actor, data, request):
    global DATABASE

    following = DATABASE.get('relay-list', [])
    inbox = get_actor_inbox(actor)

    if urllib.parse.urlsplit(inbox).hostname in AP_CONFIG['blocked_instances']:
        return

    if inbox not in following:
        following += [inbox]
        DATABASE['relay-list'] = following

    message = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "Accept",
        "to": [actor["id"]],
        "actor": "https://{}/actor".format(request.host),

        # this is wrong per litepub, but mastodon < 2.4 is not compliant with that profile.
        "object": {
             "type": "Follow",
             "id": data["id"],
             "object": "https://{}/actor".format(request.host),
             "actor": actor["id"]
        },

        "id": "https://{}/activities/{}".format(request.host, uuid.uuid4()),
    }

    asyncio.ensure_future(push_message_to_actor(actor, message, 'https://{}/actor#main-key'.format(request.host)))

    if data['object'].endswith('/actor'):
        asyncio.ensure_future(follow_remote_actor(actor['id']))


async def handle_undo(actor, data, request):
    global DATABASE

    child = data['object']
    if child['type'] == 'Follow':
        following = DATABASE.get('relay-list', [])

        inbox = get_actor_inbox(actor)

        if inbox in following:
            following.remove(inbox)
            DATABASE['relay-list'] = following

        if child['object'].endswith('/actor'):
            await unfollow_remote_actor(actor['id'])


processors = {
    'Announce': handle_relay,
    'Create': handle_relay,
    'Follow': handle_follow,
    'Undo': handle_undo
}


async def inbox(request):
    data = await request.json()

    if 'actor' not in data or not request['validated']:
        raise aiohttp.web.HTTPUnauthorized(body='access denied', content_type='text/plain')

    actor = await fetch_actor(data["actor"])
    actor_uri = 'https://{}/actor'.format(request.host)

    logging.debug(">> payload %r", data)

    processor = processors.get(data['type'], None)
    if processor:
        await processor(actor, data, request)

    return aiohttp.web.Response(body=b'{}', content_type='application/activity+json')


app.router.add_post('/inbox', inbox)
