import aiohttp
import aiohttp.web
import logging
import uuid
import urllib.parse
import simplejson as json
import re
import cgi
from Crypto.PublicKey import RSA
from .database import DATABASE


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


AP_CONFIG = CONFIG.get('ap', {'host': 'localhost'})


async def actor(request):
    data = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "endpoints": {
            "sharedInbox": "https://{}/inbox".format(request.host)
        },
        "followers": "https://{}/followers".format(request.host),
        "following": "https://{}/following".format(request.host),
        "inbox": "https://{}/inbox".format(request.host),
        "name": "Viera",
        "type": "Application",
        "id": "https://{}/actor".format(request.host),
        "publicKey": {
            "id": "https://{}/actor#main-key".format(request.host),
            "owner": "https://{}/actor".format(request.host),
            "publicKeyPem": DATABASE["actorKeys"]["publicKey"]
        },
        "summary": "Viera, the bot",
        "preferredUsername": "viera",
        "url": "https://{}/actor".format(request.host)
    }
    return aiohttp.web.json_response(data)


app.router.add_get('/actor', actor)


from .http_signatures import sign_headers


async def push_message_to_actor(actor, message, our_key_id):
    url = urllib.parse.urlsplit(actor['inbox'])

    # XXX: Digest
    data = json.dumps(message)
    headers = {
        '(request-target)': 'post {}'.format(url.path),
        'Content-Length': str(len(data)),
        'Content-Type': 'application/activity+json',
        'User-Agent': 'Viera'
    }
    headers['signature'] = sign_headers(headers, PRIVKEY, our_key_id)

    logging.debug('%r', headers)
    logging.debug('%r >> %r', actor['inbox'], message)

    async with aiohttp.ClientSession() as session:
        async with session.post(actor['inbox'], data=data, headers=headers) as resp:
            pass


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


from .authreqs import check_reqs, get_irc_bot


async def handle_create(actor, data, request):
    # for now, we only care about Notes
    if data['object']['type'] != 'Note':
        return

    # strip the HTML if present
    content = strip_html(data['object']['content']).split()

    # check if the message is an authorization token for linking identities together
    # if it is, then it's not a message we want to relay to IRC.
    if check_reqs(content, actor):
        return

    # check that the message is public before relaying
    public_uri = 'https://www.w3.org/ns/activitystreams#Public'

    if public_uri in data.get('to', []) or public_uri in data.get('cc', []):
        bot = get_irc_bot()
        bot.relay_message(actor, data['object'], ' '.join(content))


async def handle_follow(actor, data, request):
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
    await push_message_to_actor(actor, message, 'https://{}/actor#main-key'.format(request.host))


processors = {
    'Create': handle_create,
    'Follow': handle_follow
}


async def inbox(request):
    data = await request.json()

    if 'actor' not in data or not request['validated']:
        raise aiohttp.web.HTTPUnauthorized(body='access denied', content_type='text/plain')

    actor = await fetch_actor(data["actor"])
    actor_uri = 'https://{}/actor'.format(request.host)

    processor = processors.get(data['type'], None)
    if processor:
        await processor(actor, data, request)

    return aiohttp.web.Response(body=b'{}', content_type='application/activity+json')


app.router.add_post('/inbox', inbox)
