# Configuration

## DB

The path to the database. It contains the relay actor private key and all subscribed
instances. If the path is not absolute, it is relative to the working directory.

	db: relay.jsonld


## Listener

The address and port the relay will listen on. If the reverse proxy (nginx, apache, caddy, etc)
is running on the same host, it is recommended to change `listen` to `localhost`

	listen: 0.0.0.0
	port: 8080


## Note

A small blurb to describe your relay instance. This will show up on the relay's home page.

	note: "Make a note about your instance here."


## Post Limit

The maximum number of messages to send out at once. For each incoming message, a message will be
sent out to every subscribed instance minus the instance which sent the message. This limit
is to prevent too many outgoing connections from being made, so adjust if necessary.

	push_limit: 512


## AP

Various ActivityPub-related settings


### Host

The domain your relay will use to identify itself.

	host: relay.example.com


### Whitelist Enabled

If set to `true`, only instances in the whitelist can follow the relay. Any subscribed instances
not in the whitelist will be removed from the inbox list on startup.

	whitelist_enabled: false


### Whitelist

A list of domains of instances which are allowed to subscribe to your relay.

	whitelist:
	- bad-instance.example.com
	- another-bad-instance.example.com


### Blocked Instances

A list of instances which are unable to follow the instance. If a subscribed instance is added to
the block list, it will be removed from the inbox list on startup.

	blocked_instances:
	- bad-instance.example.com
	- another-bad-instance.example.com


### Blocked Software

A list of ActivityPub software which cannot follow your relay. This list is empty by default, but
setting this to the above list will block all other relays and prevent relay chains

	blocked_software:
	- activityrelay
	- aoderelay
	- social.seattle.wa.us-relay
	- unciarelay


## Cache

These are object limits for various caches. Only change if you know what you're doing.


### Objects

The urls of messages which have been processed by the relay.

	objects: 1024


### Actors

The ActivityPub actors of incoming messages.

	actors: 1024


### Actors

The base64 encoded hashes of messages.

	digests: 1024
