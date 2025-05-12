import logging
import os
import urllib.request
import zipfile

from biokb_taxtree.logger import setup_logging

setup_logging()

logger = logging.getLogger("importer")


from biokb_taxtree.constants import (
    DATA_FOLDER,
    DEFAULT_PATH_UNZIPPED_DATA_FOLDER,
    DOWNLOAD_URL,
    PATH_TO_ZIP_FILE,
)


def download_and_unzip() -> str:
    """Download IPNI data in local download folder, unzipped and return path.

    Args:
        force (bool, optional): Force to download the file. Defaults to False.

    Returns:
        str: _description_
    """
    os.makedirs(DATA_FOLDER, exist_ok=True)
    logger.info("Start downloaded to taxtree")
    urllib.request.urlretrieve(DOWNLOAD_URL, PATH_TO_ZIP_FILE)
    logger.info(f"{DOWNLOAD_URL} downloaded to {PATH_TO_ZIP_FILE}")

    with zipfile.ZipFile(PATH_TO_ZIP_FILE, "r") as zip_ref:
        os.makedirs(DEFAULT_PATH_UNZIPPED_DATA_FOLDER, exist_ok=True)
        zip_ref.extractall(DEFAULT_PATH_UNZIPPED_DATA_FOLDER)
        logger.info(f"Unzip fies to {DEFAULT_PATH_UNZIPPED_DATA_FOLDER}")

    return DEFAULT_PATH_UNZIPPED_DATA_FOLDER
