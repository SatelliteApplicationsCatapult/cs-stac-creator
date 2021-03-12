import json
from pathlib import Path

from moto import mock_s3
from sac_stac.domain.s3 import S3

BUCKET = 'test'


def initialise_bucket(s3_resource, bucket_name):
    s3_resource.create_bucket(Bucket=bucket_name)
    for file in Path('tests/data/common_sensing/fiji/sentinel_2').glob('**/*.tif'):
        s3_resource.Bucket(bucket_name).upload_file(
            Filename=str(file),
            Key=f"common_sensing/fiji/sentinel_2/{file.parent.stem}/{file.name}"
        )


@mock_s3
def test_get_object_body():
    s3 = S3(key=None, secret=None, s3_endpoint=None, region_name='us-east-1')
    initialise_bucket(s3_resource=s3.s3_resource, bucket_name=BUCKET)

    obj = s3.get_object_body(bucket_name=BUCKET,
                             object_name='common_sensing/fiji/sentinel_2/'
                                         'S2A_MSIL2A_20151022T222102_T01KBU/'
                                         'S2A_MSIL2A_20151022T222102_T01KBU_AOT_10m.tif')

    assert obj


@mock_s3
def test_get_object_body_non_exist():
    s3 = S3(key=None, secret=None, s3_endpoint=None, region_name='us-east-1')
    initialise_bucket(s3_resource=s3.s3_resource, bucket_name=BUCKET)

    obj = s3.get_object_body(bucket_name=BUCKET,
                             object_name='nothing')

    assert not obj


@mock_s3
def test_list_common_prefixes():
    s3 = S3(key=None, secret=None, s3_endpoint=None, region_name='us-east-1')
    initialise_bucket(s3_resource=s3.s3_resource, bucket_name=BUCKET)

    objs = s3.list_common_prefixes(bucket_name=BUCKET, prefix='common_sensing/fiji/sentinel_2/')

    assert objs == ['common_sensing/fiji/sentinel_2/S2A_MSIL2A_20151022T222102_T01KBU/',
                    'common_sensing/fiji/sentinel_2/S2B_MSIL2A_20191023T220919_T01KBA/',
                    'common_sensing/fiji/sentinel_2/S2B_MSIL2A_20191023T220919_T01KBB/']


@mock_s3
def test_list_common_prefixes_not_exist():
    s3 = S3(key=None, secret=None, s3_endpoint=None, region_name='us-east-1')
    initialise_bucket(s3_resource=s3.s3_resource, bucket_name=BUCKET)

    objs = s3.list_common_prefixes(bucket_name=BUCKET, prefix='common_sensing/fiji/sentinel_3/')

    assert not objs


@mock_s3
def test_put_object():
    s3 = S3(key=None, secret=None, s3_endpoint=None, region_name='us-east-1')
    s3.s3_resource.create_bucket(Bucket=BUCKET)

    object_key = 'key/test/file.txt'
    object_body = 'hello world'

    resp = s3.put_object(bucket_name=BUCKET,
                         key=object_key,
                         body=object_body)

    obj = s3.s3_resource.Object(bucket_name=BUCKET, key=object_key).get()
    obj_body_decoded = obj.get('Body').read().decode('utf-8')

    assert resp.get('ResponseMetadata').get('HTTPStatusCode') == 200
    assert object_body == obj_body_decoded


@mock_s3
def test_put_object_json():
    s3 = S3(key=None, secret=None, s3_endpoint=None, region_name='us-east-1')
    s3.s3_resource.create_bucket(Bucket=BUCKET)

    object_key = 'key/test/file.txt'
    object_dict = {'k0': 'b0', 'k1': 'b1'}
    object_body = json.dumps(object_dict)

    resp = s3.put_object(bucket_name=BUCKET,
                         key=object_key,
                         body=object_body)

    obj = s3.s3_resource.Object(bucket_name=BUCKET, key=object_key).get()
    obj_body = obj.get('Body').read().decode('utf-8')
    obj_dict = json.loads(obj_body)

    assert resp.get('ResponseMetadata').get('HTTPStatusCode') == 200
    assert object_body == obj_body
    assert object_dict == obj_dict
