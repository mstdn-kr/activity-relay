import aiohttp.web
import logging
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


from . import app


async def actor(request):
    data = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "endpoints": {
            "sharedInbox": "https://{}/inbox".format(request.host)
        },
        "followers": "https://{}/followers".format(request.host),
        "inbox": "https://{}/inbox".format(request.host),
        "name": "Viera",
        "type": "Application",
        "publicKey": {
            "id": "https://{}/actor#main-key".format(request.host),
            "owner": "https://{}/actor".format(request.host),
            "publicKeyPem": DATABASE["actorKeys"]["publicKey"]
        },
        "summary": "Viera, the bot"
    }
    return aiohttp.web.json_response(data)


app.router.add_get('/actor', actor)
