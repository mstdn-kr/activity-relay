# ActivityRelay

A generic LitePub message relay.


## Copyleft

ActivityRelay is copyrighted, but free software, licensed under the terms of the GNU
Affero General Public License version 3 (AGPLv3) license.  You can find a copy of it
in this package as the `LICENSE` file.


## Setup

You need at least Python 3.6 (latest version of 3.x recommended) to make use of this software.
It simply will not run on older Python versions.

Install the dependencies as you normally would (`pip3 install -r requirements.txt`).

Copy `relay.yaml.example` to `relay.yaml` and edit it as appropriate:

    $ cp relay.yaml.example relay.yaml
    $ $EDITOR relay.yaml

Finally, you can launch the relay:

    $ python3 -m relay

It is suggested to run this under some sort of supervisor, such as runit, daemontools,
s6 or systemd.  Configuration of the supervisor is not covered here, as it is different
depending on which system you have available.

The bot runs a webserver, internally, on localhost at port 8080.  This needs to be
forwarded by nginx or similar.  The webserver is used to receive ActivityPub messages,
and needs to be secured with an SSL certificate inside nginx or similar.  Configuration
of your webserver is not discussed here, but any guide explaining how to configure a
modern non-PHP web application should cover it.


## Getting Started

Normally, you would direct your LitePub instance software to follow the LitePub actor
found on the relay.  In Pleroma this would be something like:

    $ MIX_ENV=prod mix relay_follow https://your.relay.hostname/actor

Mastodon uses an entirely different relay protocol but supports LitePub relay protocol
as well when the Mastodon relay handshake is used.  In these cases, Mastodon relay
clients should follow `http://your.relay.hostname/inbox` as they would with Mastodon's
own relay software.


## Performance

Performance is very good, with all data being stored in memory and serialized to a
JSON-LD object graph.  Worker coroutines are spawned in the background to distribute
the messages in a scatter-gather pattern.  Performance is comparable to, if not
superior to, the Mastodon relay software, with improved memory efficiency.


## Management

You can perform a few management tasks such as peering or depeering other relays by
invoking the `relay.manage` module.

This will show the available management tasks:

    $ python3 -m relay.manage

When following remote relays, you should use the `/actor` endpoint as you would in
Pleroma and other LitePub-compliant software.

## Docker

You can run ActivityRelay with docker. Edit `relay.yaml` so that the database
location is set to `./data/relay.jsonld` and then build and run the docker
image :

    $ docker volume create activityrelay-data
    $ docker build -t activityrelay .
	$ docker run -d -p 8080:8080 -v activityrelay-data:/workdir/data activityrelay
