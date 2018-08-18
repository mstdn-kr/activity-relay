import asyncio
import logging
import base64

from blinker import signal

from . import CONFIG
from .actor import follow_remote_actor, unfollow_remote_actor
from .irc_envelope import RFC1459Message

from .authreqs import new_auth_req, set_irc_bot, check_auth, fetch_auth, drop_auth
IRC_CONFIG = CONFIG.get('irc', {})
AP_CONFIG = CONFIG.get('irc', {'host': 'localhost'})

# SASL_PAYLOAD = base64.b64encode(b'\x00'.join([IRC_CONFIG['sasl_username'], IRC_CONFIG['sasl_username'], IRC_CONFIG['sasl_password']]))


class IRCProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        self.pending_actions = {}

        self.caps_available = []
        self.caps_requested = []
        self.caps_acknowledged = []

        self.transport = transport
        self.recv_buffer = b''

        self.send_message(verb='CAP', params=['LS'])
        self.send_message(verb='NICK', params=[IRC_CONFIG['nickname']])
        self.send_message(verb='USER', params=[IRC_CONFIG['username'], '*', '*', IRC_CONFIG['realname']])
 
    def data_received(self, data):
        self.recv_buffer += data
        recvd = self.recv_buffer.replace(b'\r', b'').split(b'\n')
        self.recv_buffer = recvd.pop(-1)

        [self.line_received(m) for m in recvd]

    def line_received(self, data):
        data = data.decode('UTF-8', 'replace').strip('\r\n')

        m = RFC1459Message.from_message(data)
        self.message_received(m)

    def request_caps(self, caps):
        caps = [cap for cap in caps if cap in self.caps_available]
        caps = [cap for cap in caps if cap not in self.caps_requested]

        logging.debug('IRC: requesting caps: %r', caps)

        self.caps_requested += caps
        self.send_message(verb='CAP', params=['REQ', ' '.join(caps)])

    def end_caps(self):
        self.send_message(verb='CAP', params=['END'])

    def do_blind_authenticate(self, username, password):
        username = username.encode('ascii')
        password = password.encode('ascii')

        payload = b'\x00'.join([username, username, password])
        payload = base64.b64encode(payload).decode('ascii')

        self.send_message(verb='AUTHENTICATE', params=['PLAIN'])
        self.send_message(verb='AUTHENTICATE', params=[payload])

    def handle_cap_message(self, message):
        self.cap_requested = True
        if message.params[1] == 'LS':
            caps = message.params[2].split()
            logging.debug('IRC: available caps: %r', caps)

            self.caps_available += message.params[2].split()
            self.request_caps(['sasl', 'extended-join', 'account-tag', 'account-notify'])
        elif message.params[1] == 'ACK':
            caps = message.params[2].split()
            logging.debug('IRC: acknowledged caps: %r', caps)

            self.caps_acknowledged += caps
            if 'sasl' in self.caps_acknowledged:
                self.do_blind_authenticate(IRC_CONFIG['sasl_username'], IRC_CONFIG['sasl_password'])
            else:
                self.end_caps()

    def join_channels(self):
        self.send_message(verb='JOIN', params=[','.join(IRC_CONFIG['channels'])])

    def say(self, target, message, verb='NOTICE'):
        self.send_message(verb=verb, params=[target, message])

    def invite(self, nickname):
        [self.send_message(verb="INVITE", params=[nickname, chan]) for chan in IRC_CONFIG['channels']]

    def voice(self, nickname):
        [self.send_message(verb="MODE", params=[chan, "+v", nickname]) for chan in IRC_CONFIG['channels']]

    def whois(self, nickname, chan, account):
        data = fetch_auth(account)
        if not data:
            return
        self.say(chan, '\x02{0}\x02: \x02{1}\x02'.format(nickname, data), verb='PRIVMSG')

    def follow(self, nickname, actor_uri):
        asyncio.ensure_future(follow_remote_actor(actor_uri))
        self.say(nickname, 'Following \x02{}\x02'.format(actor_uri))

    def set_pending_action(self, nickname, action):
        if nickname not in self.pending_actions:
            self.pending_actions[nickname] = action

    def process_pending_action(self, nickname, account=None):
        if nickname not in self.pending_actions:
            return
        action = self.pending_actions.pop(nickname)
        if action == 'voice':
            self.voice(nickname)
        elif action == 'invite':
            self.invite(nickname)
        elif action == 'drop':
            data = fetch_auth(account)
            drop_auth(account)
            self.say(nickname, "The association of \x02{0}\x02 with \x02{1}\x02 has been dropped.".format(account, data))
        elif 'whois' in action:
            self.whois(nickname, action['whois'], account)
        elif 'follow' in action:
            data = fetch_auth(account)
            if not data:
                return
            if data not in IRC_CONFIG['privileged']:
                self.say(nickname, "Access denied: \x02{0}\x02 is unprivileged.".format(data))
                return
            logging.info('allowed follow: %r', action['follow'])
            self.follow(nickname, action['follow'])
        elif 'unfollow' in action:
            data = fetch_auth(account)
            if not data:
                return
            if data not in IRC_CONFIG['privileged']:
                self.say(nickname, "Access denied: \x02{0}\x02 is unprivileged.".format(data))
                return
            logging.info('allowed unfollow: %r', action['follow'])
            self.follow(nickname, action['follow'])

    def handle_auth_req(self, req):
        self.say(req.irc_nickname, "The actor \x02{0}\x02 is now linked to the IRC account \x02{1}\x02.".format(req.actor, req.irc_account))
        self.set_pending_action(req.irc_nickname, 'voice')
        self.process_pending_action(req.irc_nickname)

    def pending_whois(self, nickname, pop=False):
        if nickname not in self.pending_actions:
            return False
        data = self.pending_actions[nickname]
        if isinstance(data, dict) and 'whois' in data:
            return True
        if pop:
            self.pending_actions.pop(nickname)

    def handle_whox(self, message):
        nickname = message.params[1]
        account = message.params[2]

        if not check_auth(account) and not self.pending_whois(nickname, True):
            auth = new_auth_req(nickname, account)
            self.say(nickname, "Authentication is required for this action.  In order to prove your identity, you need to send me a token via the fediverse.")
            self.say(nickname, "On most platforms, posting like this will work: \x02@viera@{1} {0}\x02".format(auth, AP_CONFIG['host']))
            self.say(nickname, "This token is ephemeral, so you can send it to me publicly if your platform does not support direct messages.")
        else:
            self.process_pending_action(nickname, account)

    def fetch_account_whox(self, message):
        source_nick = message.source.split('!')[0]
        self.send_message(verb='WHO', params=[source_nick, "%na"])

    def handle_private_message(self, message):
        source_nick = message.source.split('!')[0]
        if message.params[1] == 'auth':
            self.fetch_account_whox(message)
        elif message.params[1] in ('voice', 'invite', 'drop'):
            self.set_pending_action(source_nick, message.params[1])
            self.fetch_account_whox(message)
        elif message.params[1][0:6] == 'follow':
            chunks = message.params[1].split()
            logging.info('considering whether to follow: %r', chunks[1])

            self.set_pending_action(source_nick, {'follow': chunks[1]})
            self.fetch_account_whox(message)

    def handle_public_message(self, message):
        if not message.params[1].startswith(IRC_CONFIG['nickname']):
            return

        chunks = message.params[1].split()
        if chunks[1] == 'whois':
            self.set_pending_action(chunks[2], {'whois': message.params[0]})
            self.send_message(verb='WHO', params=[chunks[2], "%na"])

    def handle_chat_message(self, message):
        if message.params[0] == IRC_CONFIG['nickname']:
            self.handle_private_message(message)
        else:
            self.handle_public_message(message)

    def handle_join(self, message):
        source_nick = message.source.split('!')[0]
        if check_auth(message.params[1]):
            self.set_pending_action(source_nick, 'voice')
            self.process_pending_action(source_nick, message.params[1])

    def message_received(self, message):
        if message.verb in ('PRIVMSG', 'NOTICE'):
            self.handle_chat_message(message)
        elif message.verb == '001':
            self.join_channels()
        elif message.verb == 'JOIN':
            self.handle_join(message)
        elif message.verb == 'CAP':
            self.handle_cap_message(message)
        elif message.verb == '354':
            self.handle_whox(message)
        elif message.verb == '433':
            self.send_message(verb='NICK', params=[message.params[0] + '_'])
        elif message.verb in ('900', '901', '902', '903', '904', '905', '906', '907'):
            self.end_caps()
        elif message.verb == 'PING':
            self.send_message(verb='PONG', params=message.params)
        elif message.verb in ('AUTHENTICATE',):
            pass
        else:
            logging.debug('IRC: unhandled inbound message: %r', message)

    def send_message(self, **kwargs):
        m = RFC1459Message.from_data(**kwargs)
        logging.debug('> %r', m)
        self.transport.write(m.to_message().encode('utf-8') + b'\r\n')

    def relay_message(self, actor, obj, content):
        fmt = "\x02{name}\x02: {content} [{url}]"

        msgcontent = content[0:256]
        if len(content) > 256:
            msgcontent += '...'

        message = fmt.format(name=actor['name'], content=msgcontent, url=obj['id'])
        target = ','.join(IRC_CONFIG['relay_channels'])

        self.say(target, message)


async def irc_bot():
    loop = asyncio.get_event_loop()

    if 'host' not in IRC_CONFIG:
        return

    server = IRC_CONFIG['host']
    port = IRC_CONFIG['port']
    ssl = IRC_CONFIG['ssl']

    transport, protocol = await loop.create_connection(IRCProtocol, host=server, port=port, ssl=ssl)
    set_irc_bot(protocol)

    logging.info('IRC bot ready.')
