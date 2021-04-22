import json
from typing import List
from urllib.parse import urlparse

import botocore
from pystac import STAC_IO
from sac_stac.domain.s3 import S3, NoObjectError
from sac_stac.load_config import get_s3_configuration
from sac_stac.util import parse_s3_url

S3_ENDPOINT = get_s3_configuration()["endpoint"]


class S3Repository:

    def __init__(self, s3: S3):
        self.s3 = s3

    def get_acquisition_keys(self, bucket: str, acquisition_prefix: str) -> List[str]:
        return self.s3.list_common_prefixes(bucket_name=bucket, prefix=acquisition_prefix)

    def get_product_keys(self, bucket: str, products_prefix: str) -> List[str]:
        product_objs = self.s3.list_objects(bucket_name=bucket, prefix=products_prefix, suffix='.tif')
        return [p.key for p in product_objs]

    def get_smallest_product_key(self, bucket: str, products_prefix: str) -> str:
        try:
            product_objs = self.s3.list_objects(bucket_name=bucket, prefix=products_prefix, suffix='.tif')
            product_objs_size = {p.size: p.key for p in product_objs if p.size > 1}
            product_min_size = min(list(product_objs_size.keys()))
            return product_objs_size.get(product_min_size)
        except NoObjectError:
            raise

    def get_product_raster(self, bucket: str, product_key: str) -> bytes:
        return self.s3.get_object_body(bucket_name=bucket, object_name=product_key)

    def get_dict(self, bucket: str, key: str) -> dict:
        try:
            catalog_body = self.s3.get_object_body(bucket_name=bucket, object_name=key)
            return json.loads(catalog_body.decode('utf-8'))
        except NoObjectError:
            raise

    def add_json_from_dict(self, bucket: str, key: str, stac_dict: dict):
        response = self.s3.put_object(
            bucket_name=bucket,
            key=key,
            body=json.dumps(stac_dict)
        )
        return response.get('ResponseMetadata').get('HTTPStatusCode')

    def stac_read_method(self, uri):
        parsed = urlparse(uri)
        if parsed.hostname in S3_ENDPOINT:
            try:
                bucket, key = parse_s3_url(uri)
                body = self.s3.get_object_body(bucket_name=bucket, object_name=key)
                return body.decode('utf-8')
            except NoObjectError:
                raise
        else:
            return STAC_IO.default_read_text_method(uri)
