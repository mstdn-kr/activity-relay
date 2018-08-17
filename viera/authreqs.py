import uuid
import logging
from collections import namedtuple


from .database import DATABASE


PendingAuth = namedtuple('PendingAuth', ['irc_nickname', 'irc_account', 'actor'])


AUTHS = DATABASE.get('auths', {})
DATABASE["auths"] = AUTHS
PENDING_AUTHS = {}
IRC_BOT = None


def check_reqs(chunks, actor):
    global DATABASE

    results = [x in PENDING_AUTHS for x in chunks]
    logging.debug('AUTHREQ: chunks: %r, results: %r', chunks, results)

    if True in results:
        pending_slot = results.index(True)
        pending_uuid = chunks[pending_slot]
        req = PENDING_AUTHS.pop(pending_uuid)._replace(actor=actor["id"])

        logging.debug("IRC BOT: %r, AUTHREQ: %r", IRC_BOT, req)

        if IRC_BOT:
            IRC_BOT.handle_auth_req(req)

        DATABASE["auths"][req.irc_account] = req.actor

    return True in results


def new_auth_req(irc_nickname, irc_account):
    authid = str(uuid.uuid4())
    PENDING_AUTHS[authid] = PendingAuth(irc_nickname, irc_account, None)

    return authid


def set_irc_bot(bot):
    global IRC_BOT

    IRC_BOT = bot
    logging.debug("SET IRC BOT TO: %r", bot)


def check_auth(account):
    return account in DATABASE["auths"]


def fetch_auth(account):
    if check_auth(account):
        return DATABASE["auths"][account]

    return None


def drop_auth(account):
    DATABASE["auths"].pop(account, None)
