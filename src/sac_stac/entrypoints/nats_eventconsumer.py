import asyncio
import logging
import signal

from nats.aio.client import Client as NATS
from sac_stac.service_layer.services import add_stac_collection, add_stac_item
from sac_stac.load_config import get_nats_uri, LOG_LEVEL, LOG_FORMAT

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)

logger = logging.getLogger(__name__)


async def run(loop):
    nc = NATS()

    async def closed_cb():
        logger.info("Connection to NATS is closed.")
        await asyncio.sleep(0.1, loop=loop)
        loop.stop()

    options = {
        "servers": [get_nats_uri()],
        "loop": loop,
        "closed_cb": closed_cb
    }

    await nc.connect(**options)
    logger.info(f"Connected to NATS at {nc.connected_url.netloc}...")

    async def message_handler(msg):
        subject = msg.subject
        data = msg.data.decode()
        logger.info(f"Received a message on '{subject}': {data}")
        r = {
            'collection': add_stac_collection,
            'item': add_stac_item
        }
        for k, v in r.items():
            if k in subject:
                v(data)

    await nc.subscribe("stac.creator.*", cb=message_handler)

    def signal_handler():
        if nc.is_closed:
            return
        logger.info("Disconnecting...")
        loop.create_task(nc.close())

    for sig in ('SIGINT', 'SIGTERM'):
        loop.add_signal_handler(getattr(signal, sig), signal_handler)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(loop))
    try:
        loop.run_forever()
    finally:
        loop.close()
