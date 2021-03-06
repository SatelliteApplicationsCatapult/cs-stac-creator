import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Tuple

import rasterio
from rasterio import RasterioIOError
from rasterio.crs import CRS
from shapely.geometry import box, Polygon

from sac_stac.load_config import LOG_LEVEL, LOG_FORMAT
from sac_stac.util import extract_common_prefix


logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)

logger = logging.getLogger(__name__)


def obtain_date_from_filename(file: str, regex: str, date_format: str) -> datetime:
    """
    Return date from given file based on regular expression and date format.

    :param file: path to file
    :param regex: regular expression to search in filename
    :param date_format: format used when converting to datetime

    :return: datetime object with obtained date.
    """
    filename = Path(file).name
    match_date = re.search(regex, filename)
    date = None

    if match_date:
        date = datetime.strptime(match_date.group(0), date_format)

    return date


def get_geometry_from_cog(cog_url: str) -> Tuple[Polygon, CRS]:
    """
    Extract geometry information out of the COG file served under
    the given url.

    :param cog_url: url to cog file

    :return: A Polygon and CRS objects.
    """
    try:
        with rasterio.open(cog_url) as ds:
            geom = box(*ds.bounds)
            crs = ds.crs
        return geom, crs
    except RasterioIOError as e:
        logger.warning(f"Error extracting geometry from {cog_url}: {e}")
        return Polygon(), CRS()


def get_projection_from_cog(cog_url: str) -> Tuple[list, list]:
    """
    Extract projection information out of the COG file served under
    the given url.

    :param cog_url: url to cog file

    :return: A shape and transform lists.
    """
    try:
        with rasterio.open(cog_url) as ds:
            return list(ds.shape), list(ds.transform)
    except RasterioIOError as e:
        logger.warning(f"Error extracting projection from {cog_url}: {e}")
        return [], []


def get_bands_from_product_keys(product_keys: list) -> list:
    """
    Obtain a list of bands used for the given product keys.

    :param product_keys: list of S3 keys for products.

    :return: list of band names.
    """
    product_names = [Path(a).stem for a in product_keys]
    common_prefix = extract_common_prefix(product_names)
    return [b.replace(common_prefix, '') for b in product_names]
