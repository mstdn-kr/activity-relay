import json
import logging
import traceback

from Crypto.PublicKey import RSA
from urllib.parse import urlparse


class RelayDatabase:
	def __init__(self, config):
		self.config = config
		self.data = None
		self.PRIVKEY = None


	@property
	def PUBKEY(self):
		return self.PRIVKEY.publickey()


	@property
	def pubkey(self):
		return self.PUBKEY.exportKey('PEM').decode('utf-8')


	@property
	def privkey(self):
		try:
			return self.data['private-key']

		except KeyError:
			return False


	@property
	def hostnames(self):
		return [urlparse(inbox).hostname for inbox in self.inboxes]


	@property
	def inboxes(self):
		return self.data.get('relay-list', [])


	def generate_key(self):
		self.PRIVKEY = RSA.generate(4096)
		self.data['private-key'] = self.PRIVKEY.exportKey('PEM').decode('utf-8')


	def load(self):
		new_db = True

		try:
			with self.config.db.open() as fd:
				self.data = json.load(fd)

			key = self.data.pop('actorKeys', None)

			if key:
				self.data['private-key'] = key.get('privateKey')

			self.data.pop('actors', None)
			new_db = False

		except FileNotFoundError:
			pass

		except json.decoder.JSONDecodeError as e:
			if self.config.db.stat().st_size > 0:
				raise e from None

		if not self.data:
			logging.info('No database was found. Making a new one.')
			self.data = {}

		for inbox in self.inboxes:
			if self.config.is_banned(inbox) or (self.config.whitelist_enabled and not self.config.is_whitelisted(inbox)):
				self.del_inbox(inbox)

		if not self.privkey:
			logging.info("No actor keys present, generating 4096-bit RSA keypair.")
			self.generate_key()

		else:
			self.PRIVKEY = RSA.importKey(self.privkey)

		self.save()
		return not new_db


	def save(self):
		with self.config.db.open('w') as fd:
			data = {
				'relay-list': self.inboxes,
				'private-key': self.privkey
			}

			json.dump(data, fd, indent=4)


	def get_inbox(self, domain):
		if domain.startswith('http'):
			domain = urlparse(domain).hostname

		for inbox in self.inboxes:
			if domain == urlparse(inbox).hostname:
				return inbox


	def add_inbox(self, inbox):
		assert inbox.startswith('https')
		assert inbox not in self.inboxes

		self.data['relay-list'].append(inbox)


	def del_inbox(self, inbox):
		if inbox not in self.inboxes:
			raise KeyError(inbox)

		self.data['relay-list'].remove(inbox)
