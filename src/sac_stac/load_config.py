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
    host = os.environ.get("NATS_HOST", "localhost")
    return f"nats://{host}:4222"
