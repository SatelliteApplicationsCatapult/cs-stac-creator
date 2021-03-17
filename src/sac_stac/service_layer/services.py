import json
import logging
from pathlib import Path
from urllib.parse import urlparse

import boto3
from geopandas import GeoSeries
from pystac import Catalog, Extent, SpatialExtent, TemporalExtent, Asset, MediaType, STAC_IO
from pystac.extensions.eo import Band

from sac_stac.adapters.repository import S3Repository
from sac_stac.domain.model import SacCollection, SacItem
from sac_stac.domain.operations import obtain_date_from_filename, get_geometry_from_cog, get_bands_from_product_keys, \
    get_projection_from_cog
from sac_stac.load_config import config, LOG_LEVEL, LOG_FORMAT, get_s3_configuration
from sac_stac.util import parse_s3_url

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

S3_ENDPOINT = get_s3_configuration()["endpoint"]
S3_BUCKET = get_s3_configuration()["bucket"]
S3_STAC_KEY = get_s3_configuration()["stac_key"]
S3_CATALOG_KEY = f"{S3_STAC_KEY}/catalog.json"


def add_stac_collection(repo: S3Repository, sensor_key: str):
    STAC_IO.read_text_method = repo.stac_read_method

    catalog_dict = repo.get_dict(bucket=S3_BUCKET, key=S3_CATALOG_KEY)
    sensor_name = sensor_key.split('/')[-2]
    collection_key = f"{S3_STAC_KEY}/{sensor_name}/collection.json"

    try:
        catalog = Catalog.from_dict(catalog_dict)
    except KeyError:
        logger.info(f"No catalog found in {S3_CATALOG_KEY}")
        logger.info("Creating new catalog...")
        catalog = Catalog(
            id=config.get('id'),
            title=config.get('title'),
            description=config.get('description'),
            stac_extensions=config.get('stac_extensions')
        )

    sensors = [s for s in config.get('sensors')]
    sensor = [s for s in sensors if s.get('id') in sensor_key][0]

    if sensor:
        collection = SacCollection(
            id=sensor.get('id'),
            title=sensor.get('title'),
            description=sensor.get('description'),
            extent=Extent(SpatialExtent([[0, 0, 0, 0]]), TemporalExtent([["", ""]])),
            properties={}
        )

        collection.add_providers(sensor)
        collection.add_product_definition_extension(
            product_definition=sensor.get('extensions').get('product_definition'),
            bands_metadata=sensor.get('extensions').get('eo').get('bands')
        )

        catalog.add_child(collection)
        catalog.normalize_hrefs(config.get('output_url'))

        repo.add_json_from_dict(bucket=S3_BUCKET, key=S3_CATALOG_KEY,
                                stac_dict=catalog.to_dict())
        repo.add_json_from_dict(
            bucket=S3_BUCKET,
            key=collection_key,
            stac_dict=collection.to_dict()
        )
        logger.info(f"{sensor_name} collection added to {collection_key}")

        acquisition_keys = repo.get_acquisition_keys(bucket=S3_BUCKET,
                                                     acquisition_prefix=sensor_key)
        for acquisition_key in acquisition_keys:
            add_stac_item(repo=repo, acquisition_key=acquisition_key)

    else:
        logger.warning(f"No config found for {sensor_name} sensor")

    return 'collection', collection_key


def add_stac_item(repo: S3Repository, acquisition_key: str):
    STAC_IO.read_text_method = repo.stac_read_method

    sensor_name = acquisition_key.split('/')[-3]
    collection_key = f"{S3_STAC_KEY}/{sensor_name}/collection.json"
    collection_dict = repo.get_dict(bucket=S3_BUCKET, key=collection_key)
    logger.debug(f"[Item] Adding {acquisition_key} item to {sensor_name}...")

    try:
        collection = SacCollection.from_dict(collection_dict)
        sensor = [s for s in config.get('sensors') if s.get('id') == collection.id][0]

        # Get date from acquisition name
        date = obtain_date_from_filename(
            file=acquisition_key,
            regex=sensor.get('formatting').get('date').get('regex'),
            date_format=sensor.get('formatting').get('date').get('format')
        )

        # Get sample product and extract geometry
        product_sample_key = repo.get_smallest_product_key(
            bucket=S3_BUCKET,
            products_prefix=acquisition_key
        )
        product_sample = f"{S3_ENDPOINT}/{S3_BUCKET}/{product_sample_key}"
        geometry, crs = get_geometry_from_cog(product_sample)

        item = SacItem(
            id=Path(acquisition_key).stem,
            datetime=date,
            geometry=json.loads(GeoSeries([geometry], crs=crs).to_crs(4326).to_json()).get('features')[0].get(
                'geometry'),
            bbox=list(geometry.bounds),
            properties={}
        )

        item.ext.enable('projection')
        item.ext.projection.epsg = crs.to_epsg()

        item.add_extensions(sensor.get('extensions'))
        item.add_common_metadata(sensor.get('common_metadata'))

        bands_metadata = sensor.get('extensions').get('eo').get('bands')
        product_keys = repo.get_product_keys(bucket=S3_BUCKET, products_prefix=acquisition_key)
        bands = get_bands_from_product_keys(product_keys)

        for band_name, band_common_name in [(b.get('name'), b.get('common_name')) for b in bands_metadata]:

            asset_href = ''
            proj_shp = []
            proj_tran = []

            if band_name in bands:
                product_key = [k for k in product_keys if band_name in k][0]
                asset_href = f"{S3_ENDPOINT}/{S3_BUCKET}/{product_key}"
                proj_shp, proj_tran = get_projection_from_cog(asset_href)

            asset = Asset(
                href=asset_href,
                media_type=MediaType.COG
            )

            # Set Projection
            item.ext.projection.set_transform(proj_tran, asset)
            item.ext.projection.set_shape(proj_shp, asset)

            # Set bands
            item.ext.eo.set_bands([Band.create(
                name=band_common_name, description='TBD', common_name=band_common_name)],
                asset
            )
            logger.debug(f"[Asset] Adding {asset_href} asset to {acquisition_key}...")
            item.add_asset(key=band_common_name, asset=asset)

        collection.add_item(item)
        collection.update_extent_from_items()
        collection.normalize_hrefs(f"{config.get('output_url')}/{sensor_name}")

        repo.add_json_from_dict(bucket=S3_BUCKET,
                                key=collection_key,
                                stac_dict=collection.to_dict())
        item_key = f"{S3_STAC_KEY}/{collection.id}/{item.id}/{item.id}.json"
        repo.add_json_from_dict(
            bucket=S3_BUCKET,
            key=item_key,
            stac_dict=item.to_dict()
        )
        logger.info(f"{item.id} item added to {collection.id}")

        return 'item', item_key

    except TypeError:
        logger.error(f"Invalid collection in {collection_key}, "
                     f"could not add {acquisition_key}.")
    except KeyError:
        logger.info(f"No collection found in {collection_key},"
                    f"could not add {acquisition_key}.")
