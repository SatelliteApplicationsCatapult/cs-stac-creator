import json
import logging
from pathlib import Path

from geopandas import GeoSeries
from pystac import Catalog, Extent, SpatialExtent, TemporalExtent, Asset, MediaType
from pystac.extensions.eo import Band
from sac_stac.adapters import repository
from sac_stac.domain.model import SacCollection, SacItem
from sac_stac.domain.operations import obtain_date_from_filename, get_geometry_from_cog, get_bands_from_product_keys, \
    get_projection_from_cog
from sac_stac.domain.s3 import S3
from sac_stac.load_config import config, LOG_LEVEL, LOG_FORMAT, get_s3_configuration

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

S3_ACCESS_KEY_ID = get_s3_configuration()["key_id"]
S3_SECRET_ACCESS_KEY = get_s3_configuration()["access_key"]
S3_REGION = get_s3_configuration()["region"]
S3_ENDPOINT = get_s3_configuration()["endpoint"]
S3_BUCKET = get_s3_configuration()["bucket"]
S3_STAC_KEY = get_s3_configuration()["stac_key"]
S3_CATALOG_KEY = f"{S3_STAC_KEY}/catalog.json"


def add_stac_collection(sensor_key: str):

    s3 = S3(key=S3_ACCESS_KEY_ID, secret=S3_SECRET_ACCESS_KEY,
            s3_endpoint=S3_ENDPOINT, region_name=S3_REGION)
    repo = repository.S3Repository(s3)

    catalog_dict = repo.get_dict(bucket=S3_BUCKET, key=S3_CATALOG_KEY)

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

    sensor = [s for s in config.get('sensors') if s.get('title') in sensor_key][0]

    if sensor:
        collection = SacCollection(
            id=sensor.get('id'),
            title=sensor.get('title'),
            description=sensor.get('description'),
            extent=Extent(SpatialExtent([[]]), TemporalExtent([[]])),
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
            key=f"{S3_CATALOG_KEY}/{collection.id}/collection.json",
            stac_dict=collection.to_dict()
        )

        acquisition_keys = repo.get_acquisition_keys(bucket=S3_BUCKET,
                                                     acquisition_prefix=sensor_key)
        for acquisition_key in acquisition_keys:
            add_stac_item(acquisition_key)

    else:
        logger.warning(f"No config found for {sensor_key.split('/')[:-1]} sensor")


def add_stac_item(acquisition_key: str):

    s3 = S3(key=S3_ACCESS_KEY_ID, secret=S3_SECRET_ACCESS_KEY,
            s3_endpoint=S3_ENDPOINT, region_name=S3_REGION)
    repo = repository.S3Repository(s3)

    collection_key = f"{'/'.join(acquisition_key.split('/')[:-1])}/collection.json"
    collection_dict = repo.get_dict(bucket=S3_BUCKET, key=collection_key)

    try:
        collection = SacCollection.from_dict(collection_dict)
        sensor = [s for s in config.get('sensors') if s.get('title') == collection.id][0]

        # Get date from acquisition name
        date = obtain_date_from_filename(
            file=acquisition_key,
            regex=sensor.get('formatting').get('date').get('regex'),
            date_format=sensor.get('formatting').get('date').get('format')
        )

        # Get sample product and extract geometry
        product_sample = repo.get_smallest_product_key(bucket=S3_BUCKET,
                                                       products_prefix=acquisition_key)
        #                  ** ONLY FOR TESTING **
        product_sample = f'tests/data/{product_sample}'
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

            product_key = ''
            proj_shp = []
            proj_tran = []

            if band_name in bands:
                product_key = [k for k in product_keys if band_name in k][0]
                #                                               ** ONLY FOR TESTING **
                proj_shp, proj_tran = get_projection_from_cog(f'tests/data/{product_key}')

            asset = Asset(
                href=product_key,
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

            item.add_asset(key=band_common_name, asset=asset)

        collection.add_item(item)
        collection.update_extent_from_items()

        repo.add_json_from_dict(bucket=S3_BUCKET, key=S3_CATALOG_KEY,
                                stac_dict=collection.to_dict())
        repo.add_json_from_dict(
            bucket=S3_BUCKET,
            key=f"{S3_STAC_KEY}/{collection.id}/{item.id}/{item.id}.json",
            stac_dict=item.to_dict()
        )

    except TypeError:
        logger.error(f"Invalid collection in {collection_key}, "
                     f"could not add {acquisition_key}.")
    except KeyError:
        logger.info(f"No collection found in {collection_key},"
                    f"could not add {acquisition_key}.")