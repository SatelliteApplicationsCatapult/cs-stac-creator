import json
import os
from logging import INFO
from pathlib import Path

LOG_FORMAT = '%(asctime)s - %(levelname)6s - %(message)s'
LOG_LEVEL = INFO

with open(Path(__file__).parent / "config.json") as json_data_file:
    config_file = json.load(json_data_file)

config = config_file


def get_nats_uri():
    host = os.environ.get("NATS_HOST", "127.0.0.1")
    return f"nats://{host}:4222"


def get_s3_configuration():
    key_id = os.environ.get("S3_ACCESS_KEY_ID", None)
    access_key = os.environ.get("S3_SECRET_ACCESS_KEY", None)
    region = os.environ.get("S3_REGION", 'us-east-1')
    endpoint = os.environ.get("S3_ENDPOINT", 'https://s3-uk-1.sa-catapult.co.uk')
    bucket = os.environ.get("S3_BUCKET", 'public-eo-data')
    stac_key = os.environ.get("S3_STAC_KEY", 'stac_catalogs/cs_stac')
    return dict(key_id=key_id, access_key=access_key, region=region,
                endpoint=endpoint, bucket=bucket, stac_key=stac_key)
