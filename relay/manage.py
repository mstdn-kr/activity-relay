import asyncio
import sys
import simplejson as json

from .actor import follow_remote_actor, unfollow_remote_actor
from . import CONFIG
from .database import DATABASE


def relay_list():
    print('Connected to the following instances or relays:')
    [print('-', relay) for relay in DATABASE['relay-list']]


def relay_follow():
    if len(sys.argv) < 3:
        print('usage: python3 -m relay.manage follow <target>')
        exit()

    target = sys.argv[2]

    loop = asyncio.get_event_loop()
    loop.run_until_complete(follow_remote_actor(target))

    print('Sent follow message to:', target)


def relay_unfollow():
    if len(sys.argv) < 3:
        print('usage: python3 -m relay.manage unfollow <target>')
        exit()

    target = sys.argv[2]

    loop = asyncio.get_event_loop()
    loop.run_until_complete(unfollow_remote_actor(target))

    print('Sent unfollow message to:', target)

def relay_forceremove():
    if len(sys.argv) < 3:
        print('usage: python3 -m relay.manage force-remove <target>')
        exit()

    target = sys.argv[2]

    following = DATABASE.get('relay-list', [])

    if target in following:
        following.remove(target)
        DATABASE['relay-list'] = following
        with open('relay.jsonld', 'w') as f:
            json.dump(DATABASE, f)
        print('Removed target from DB:', target)


TASKS = {
    'list': relay_list,
    'follow': relay_follow,
    'unfollow': relay_unfollow,
    'force-remove': relay_forceremove
}


def usage():
    print('usage: python3 -m relay.manage <task> [...]')
    print('tasks:')
    [print('-', task) for task in TASKS.keys()]
    exit()


def main():
    if len(sys.argv) < 2:
        usage()

    if sys.argv[1] in TASKS:
        TASKS[sys.argv[1]]()
    else:
        usage()


if __name__ == '__main__':
    main()
