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


def download_and_unzip(path_zip_file=PATH_TO_ZIP_FILE, path_unzip_folder=DEFAULT_PATH_UNZIPPED_DATA_FOLDER) -> str:
    """Download Taxtree data, unzipped and return path.

    This function downloads the NCBI Taxonomy data from the specified URL,
    unzips it, and returns the path to the unzipped data folder.
    Returns:
        str: The path to the unzipped data folder.
    """
    os.makedirs(DATA_FOLDER, exist_ok=True)

    if not path_zip_file:
        path_zip_file = PATH_TO_ZIP_FILE

    if not path_unzip_folder:
        path_unzip_folder = DEFAULT_PATH_UNZIPPED_DATA_FOLDER

    if not os.path.exists(path_zip_file):
        logger.info("Start downloading")
        urllib.request.urlretrieve(DOWNLOAD_URL, path_zip_file)
        logger.info(f"{DOWNLOAD_URL} downloaded to {path_zip_file}")

    with zipfile.ZipFile(path_zip_file, "r") as zip_ref:
        os.makedirs(path_unzip_folder, exist_ok=True)
        zip_ref.extractall(path_unzip_folder)
        logger.info(f"Unzip files to {path_unzip_folder}")

    return path_unzip_folder
