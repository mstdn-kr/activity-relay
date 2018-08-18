# viera

A useful IRC and ActivityPub bot which links identities and relays messages.


## Copyleft

`viera` is copyrighted, but free software, licensed under the terms of the GNU Affero
General Public License version 3 (AGPLv3) license.  You can find a copy of it in this
package as the `LICENSE` file.


## Setup

You need at least Python 3.5 (3.5.2 or newer recommended) to make use of this software.
It simply will not run on older Python versions.

`viera` uses the new `pipenv` python environment manager, you should install it before
trying to make use of this software:

    $ pip3 install pipenv

Next, create the virtual environment for `viera` to use:

    $ pipenv install

Next, copy `viera.yaml.example` to `viera.yaml` and edit it as appropriate:

    $ cp viera.yaml.example viera.yaml
    $ $EDITOR viera.yaml

Finally, you can launch viera:

    $ pipenv run python3 -m viera

It is suggested to run this under some sort of supervisor, such as runit, daemontools,
s6 or systemd.  Configuration of the supervisor is not covered here, as it is different
depending on which system you have available.

The bot runs a webserver, internally, on localhost at port 8080.  This needs to be
forwarded by nginx or similar.  The webserver is used to receive ActivityPub messages,
and needs to be secured with an SSL certificate inside nginx or similar.  Configuration
of your webserver is not discussed here, but any guide explaining how to configure a
modern non-PHP web application should cover it.


## Getting started

It is required to register a services account for the bot.  This is different depending
on the IRC network in use.

It is also required to use SASL to authenticate to the IRC network.  This is supported on
most IRC networks.

`viera` works with ActivityPub identities as the primary source of trust.  This means that
you are required to link an ActivityPub identity to your IRC identity in order to
authenticate to the bot.  To do that, make sure you are logged into your NickServ or similar
account and message the bot on IRC:

    /msg yourbot auth

The bot will respond with an authentication token that you must supply via the fediverse,
in most cases you can just copy and paste the exact message it provides.


### Following accounts to relay to IRC

Once you have authenticated to an AP identity which is listed in the `privileged` group in
the config file, you may configure the bot to follow accounts, by using the `follow` command:

    /msg yourbot follow https://pleroma.site/users/kaniini

This will cause your bot to request an ActivityPub connection between itself and the user you
followed.  In most cases this will be set up immediately, but in some cases, there may be a delay,
such as when accounts are restricted.

If you want the bot to stop following an account, you can use the `unfollow` command:

    /msg yourbot unfollow https://pleroma.site/users/kaniini

