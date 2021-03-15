from pathlib import Path

from moto.s3 import mock_s3
from sac_stac.adapters import repository
from sac_stac.domain.s3 import S3
from sac_stac.service_layer import services


def initialise_s3_bucket(sensor_key, s3_resource, bucket_name):
    s3_resource.create_bucket(Bucket=bucket_name)
    for file in Path(f'tests/data/{sensor_key}').glob('**/*.tif'):
        s3_resource.Bucket(bucket_name).upload_file(
            Filename=str(file),
            Key=f"{sensor_key}{file.parent.stem}/{file.name}"
        )


@mock_s3
def test_add_stac_collection():
    sensor_key = 'common_sensing/fiji/landsat_5/'
    s3 = S3(key=None, secret=None, s3_endpoint=None, region_name='us-east-1')
    initialise_s3_bucket(sensor_key, s3.s3_resource, 'public-eo-data')

    repo = repository.S3Repository(s3)

    collection = services.add_stac_collection(repo=repo, sensor_key=sensor_key)

    assert collection
