import asyncio
import aiohttp.web
import logging

from . import app


async def start_webserver():
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()

    logging.info('Starting webserver at localhost:8080')

    site = aiohttp.web.TCPSite(runner, 'localhost', 8080)
    await site.start()


def main():
    loop = asyncio.get_event_loop()
    asyncio.ensure_future(start_webserver())
    loop.run_forever()


if __name__ == '__main__':
    main()
