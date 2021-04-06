import asyncio
import os
from pathlib import Path

from nats.aio.client import Client as NATS
from moto.s3 import mock_s3
from sac_stac.adapters import repository
from sac_stac.domain.s3 import S3
from sac_stac.entrypoints.nats_eventconsumer import run


def initialise_s3_bucket(sensor_key, s3_resource, bucket_name):
    s3_resource.create_bucket(Bucket=bucket_name)
    for file in Path(f'tests/data/{sensor_key}').glob('**/*.tif'):
        s3_resource.Bucket(bucket_name).upload_file(
            Filename=str(file),
            Key=f"{sensor_key}{file.parent.stem}/{file.name}"
        )


async def client(nc, sensor_key):
    future = asyncio.Future()

    async def message_handler(msg):
        data = msg.data.decode()
        future.set_result(data)

    await nc.subscribe("stac_indexer.*", cb=message_handler)
    await nc.publish("stac_creator.collection", sensor_key.encode())
    return await asyncio.wait_for(future, 1)


async def close_nats(nc, loop):
    loop.create_task(nc.close())
    await asyncio.sleep(0.1)
    loop.stop()


@mock_s3
def test_new_stac_collection():
    try:
        os.environ["TEST_ENV"] = "Yes"
        sensor_key = "common_sensing/fiji/landsat_5/"
        bucket = 'public-eo-data'

        s3 = S3(key=None, secret=None, s3_endpoint=None, region_name='us-east-1')
        initialise_s3_bucket(sensor_key, s3.s3_resource, bucket)
        repo = repository.S3Repository(s3)

        event_loop = asyncio.get_event_loop()
        nats_client = NATS()

        event_loop.run_until_complete(run(nats_client, repo, event_loop))
        collection_key = event_loop.run_until_complete(client(nats_client, sensor_key))
        event_loop.run_until_complete(close_nats(nats_client, event_loop))

        event_loop.run_forever()
        event_loop.close()

        assert collection_key == "stac_catalogs/cs_stac/landsat_5/collection.json"

        collection = repo.get_dict(bucket=bucket, key=collection_key)
        items = [link.get('href') for link in collection.get('links') if link.get('rel') == 'item']
        assert items == ['https://s3-uk-1.sa-catapult.co.uk/public-eo-data/stac_catalogs/cs_stac/landsat_5/'
                         'LT05_L1TP_075073_19911225/LT05_L1TP_075073_19911225.json']

    finally:
        os.environ.pop("TEST_ENV")
