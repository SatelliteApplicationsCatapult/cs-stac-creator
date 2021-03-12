from moto import mock_s3
from sac_stac.adapters import repository
from sac_stac.domain.s3 import S3
from pathlib import Path

from sac_stac.util import load_json

BUCKET = 'public-eo-data'


def initialise_cs_bucket(s3_resource, bucket_name):
    s3_resource.create_bucket(Bucket=bucket_name)
    for file in Path('tests/data/common_sensing/fiji/sentinel_2').glob('**/*.tif'):
        s3_resource.Bucket(bucket_name).upload_file(
            Filename=str(file),
            Key=f"common_sensing/fiji/sentinel_2/{file.parent.stem}/{file.name}"
        )


@mock_s3
def test_get_acquisition_keys():
    s3 = S3(key=None, secret=None, s3_endpoint=None, region_name='us-east-1')
    initialise_cs_bucket(s3_resource=s3.s3_resource, bucket_name=BUCKET)

    repo = repository.S3Repository(s3)
    acquisitions = repo.get_acquisition_keys(bucket=BUCKET, acquisition_prefix='common_sensing/fiji/sentinel_2/')

    assert acquisitions == ['common_sensing/fiji/sentinel_2/S2A_MSIL2A_20151022T222102_T01KBU/',
                            'common_sensing/fiji/sentinel_2/S2B_MSIL2A_20191023T220919_T01KBA/',
                            'common_sensing/fiji/sentinel_2/S2B_MSIL2A_20191023T220919_T01KBB/']


@mock_s3
def test_get_product_keys():
    s3 = S3(key=None, secret=None, s3_endpoint=None, region_name='us-east-1')
    initialise_cs_bucket(s3_resource=s3.s3_resource, bucket_name=BUCKET)

    repo = repository.S3Repository(s3)
    products = repo.get_product_keys(bucket=BUCKET,
                                     products_prefix='common_sensing/fiji/sentinel_2/'
                                                     'S2A_MSIL2A_20151022T222102_T01KBU/')

    assert products == ['common_sensing/fiji/sentinel_2/S2A_MSIL2A_20151022T222102_T01KBU/'
                        'S2A_MSIL2A_20151022T222102_T01KBU_AOT_10m.tif',
                        'common_sensing/fiji/sentinel_2/S2A_MSIL2A_20151022T222102_T01KBU/'
                        'S2A_MSIL2A_20151022T222102_T01KBU_B01_60m.tif',
                        'common_sensing/fiji/sentinel_2/S2A_MSIL2A_20151022T222102_T01KBU/'
                        'S2A_MSIL2A_20151022T222102_T01KBU_B02_10m.tif',
                        'common_sensing/fiji/sentinel_2/S2A_MSIL2A_20151022T222102_T01KBU/'
                        'S2A_MSIL2A_20151022T222102_T01KBU_B03_10m.tif',
                        'common_sensing/fiji/sentinel_2/S2A_MSIL2A_20151022T222102_T01KBU/'
                        'S2A_MSIL2A_20151022T222102_T01KBU_B04_10m.tif',
                        'common_sensing/fiji/sentinel_2/S2A_MSIL2A_20151022T222102_T01KBU/'
                        'S2A_MSIL2A_20151022T222102_T01KBU_B05_20m.tif',
                        'common_sensing/fiji/sentinel_2/S2A_MSIL2A_20151022T222102_T01KBU/'
                        'S2A_MSIL2A_20151022T222102_T01KBU_B06_20m.tif',
                        'common_sensing/fiji/sentinel_2/S2A_MSIL2A_20151022T222102_T01KBU/'
                        'S2A_MSIL2A_20151022T222102_T01KBU_B07_20m.tif',
                        'common_sensing/fiji/sentinel_2/S2A_MSIL2A_20151022T222102_T01KBU/'
                        'S2A_MSIL2A_20151022T222102_T01KBU_B08_10m.tif',
                        'common_sensing/fiji/sentinel_2/S2A_MSIL2A_20151022T222102_T01KBU/'
                        'S2A_MSIL2A_20151022T222102_T01KBU_B09_60m.tif',
                        'common_sensing/fiji/sentinel_2/S2A_MSIL2A_20151022T222102_T01KBU/'
                        'S2A_MSIL2A_20151022T222102_T01KBU_B11_20m.tif',
                        'common_sensing/fiji/sentinel_2/S2A_MSIL2A_20151022T222102_T01KBU/'
                        'S2A_MSIL2A_20151022T222102_T01KBU_B12_20m.tif',
                        'common_sensing/fiji/sentinel_2/S2A_MSIL2A_20151022T222102_T01KBU/'
                        'S2A_MSIL2A_20151022T222102_T01KBU_B8A_20m.tif',
                        'common_sensing/fiji/sentinel_2/S2A_MSIL2A_20151022T222102_T01KBU/'
                        'S2A_MSIL2A_20151022T222102_T01KBU_SCL_20m.tif',
                        'common_sensing/fiji/sentinel_2/S2A_MSIL2A_20151022T222102_T01KBU/'
                        'S2A_MSIL2A_20151022T222102_T01KBU_WVP_10m.tif']


@mock_s3
def test_get_smallest_product_key():
    s3 = S3(key=None, secret=None, s3_endpoint=None, region_name='us-east-1')
    initialise_cs_bucket(s3_resource=s3.s3_resource, bucket_name=BUCKET)

    repo = repository.S3Repository(s3)
    product = repo.get_smallest_product_key(bucket=BUCKET,
                                            products_prefix='common_sensing/fiji/sentinel_2/'
                                                            'S2A_MSIL2A_20151022T222102_T01KBU/')

    assert product == 'common_sensing/fiji/sentinel_2/S2A_MSIL2A_20151022T222102_T01KBU/' \
                      'S2A_MSIL2A_20151022T222102_T01KBU_B02_10m.tif'


@mock_s3
def test_get_product_raster():
    s3 = S3(key=None, secret=None, s3_endpoint=None, region_name='us-east-1')
    initialise_cs_bucket(s3_resource=s3.s3_resource, bucket_name=BUCKET)

    repo = repository.S3Repository(s3)
    product = repo.get_product_raster(bucket=BUCKET,
                                      product_key='common_sensing/fiji/sentinel_2/'
                                                  'S2A_MSIL2A_20151022T222102_T01KBU/'
                                                  'S2A_MSIL2A_20151022T222102_T01KBU_B02_10m.tif')

    file = 'tests/data/common_sensing/fiji/sentinel_2/S2A_MSIL2A_20151022T222102_T01KBU/' \
           'S2A_MSIL2A_20151022T222102_T01KBU_B02_10m.tif'

    # Open raster file as bytes
    with open(file, "rb") as r:
        raster = r.read()

    assert product == raster


@mock_s3
def test_get_catalog():
    catalog_file_path = 'tests/output/catalog.json'
    catalog_s3_key = 'stac_catalogs/cs_stac/catalog.json'

    s3 = S3(key=None, secret=None, s3_endpoint=None, region_name='us-east-1')
    s3.s3_resource.create_bucket(Bucket=BUCKET)
    s3.s3_resource.Bucket(BUCKET).upload_file(
        Filename=catalog_file_path,
        Key=catalog_s3_key
    )

    repo = repository.S3Repository(s3)
    catalog = repo.get_catalog(bucket=BUCKET, catalog_key=catalog_s3_key)

    catalog_file = load_json(catalog_file_path)
    assert catalog == catalog_file
