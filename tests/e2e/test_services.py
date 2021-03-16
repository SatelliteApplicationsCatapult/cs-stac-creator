import shutil
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


def add_stac_s3(sensor_name, s3_resource, bucket_name):
    s3_resource.Bucket(bucket_name).upload_file(
        Filename='tests/output/catalog.json',
        Key='stac_catalogs/cs_stac/catalog.json'
    )
    s3_resource.Bucket(bucket_name).upload_file(
        Filename=f'tests/output/{sensor_name}/collection.json',
        Key=f'stac_catalogs/cs_stac/{sensor_name}/collection.json'
    )
    for file in Path(f'tests/output/{sensor_name}').glob('**/*.json'):
        if 'collection' not in file.name:
            s3_resource.Bucket(bucket_name).upload_file(
                Filename=str(file),
                Key=f"stac_catalogs/cs_stac/{sensor_name}/{file.stem}/{file.name}"
            )


@mock_s3
def test_add_stac_collection():
    sensor_key = 'common_sensing/fiji/landsat_5/'
    s3 = S3(key=None, secret=None, s3_endpoint=None, region_name='us-east-1')
    initialise_s3_bucket(sensor_key, s3.s3_resource, 'public-eo-data')

    repo = repository.S3Repository(s3)

    collection = services.add_stac_collection(repo=repo, sensor_key=sensor_key)

    assert collection


@mock_s3
def test_add_stac_item():
    sensor_name = 'landsat_5'
    sensor_key = f'common_sensing/fiji/{sensor_name}/'
    acquisition_key = f'{sensor_key}LT05_L1TP_075073_19920125/'
    try:
        s3 = S3(key=None, secret=None, s3_endpoint=None, region_name='us-east-1')

        shutil.copytree(f'tests/data/test_add_stac_item/{acquisition_key}',
                        f'tests/data/{acquisition_key}')

        initialise_s3_bucket(sensor_key, s3.s3_resource, 'public-eo-data')
        add_stac_s3(sensor_name, s3.s3_resource, 'public-eo-data')

        repo = repository.S3Repository(s3)

        item = services.add_stac_item(repo=repo, acquisition_key=acquisition_key)

        assert item
    finally:
        shutil.rmtree(f'tests/data/{acquisition_key}')
