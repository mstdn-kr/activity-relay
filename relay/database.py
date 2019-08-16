import asyncio
import logging
import urllib.parse
import simplejson as json


from . import CONFIG
AP_CONFIG = CONFIG.get('ap', {'blocked_instances':[], 'whitelist_enabled': False, 'whitelist': []})


try:
    with open(CONFIG['db']) as f:
        DATABASE = json.load(f)
except:
    logging.info('No database was found, making a new one.')
    DATABASE = {}

following = DATABASE.get('relay-list', [])
for inbox in following:
    if urllib.parse.urlsplit(inbox).hostname in AP_CONFIG['blocked_instances']:
        following.remove(inbox)
        DATABASE['relay-list'] = following

    elif AP_CONFIG['whitelist_enabled'] is True and urllib.parse.urlsplit(inbox).hostname not in AP_CONFIG['whitelist']:
        following.remove(inbox)
        DATABASE['relay-list'] = following

if 'actors' in DATABASE:
    DATABASE.pop('actors')

async def database_save():
    while True:
        with open(CONFIG['db'], 'w') as f:
            json.dump(DATABASE, f)
        await asyncio.sleep(30)


asyncio.ensure_future(database_save())
