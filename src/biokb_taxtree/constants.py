"""Basic constants."""

import os
from collections import defaultdict
from enum import StrEnum
from pathlib import Path

from annotated_types import T

# standard for all biokb projects, but individual set
PROJECT_NAME = "taxtree"
BASIC_NODE_LABEL = "DbTaxtree"
# standard for all biokb projects
ORGANIZATION = "biokb"
LIBRARY_NAME = f"{ORGANIZATION}_{PROJECT_NAME}"
HOME = str(Path.home())
BIOKB_FOLDER = os.path.join(HOME, f".{ORGANIZATION}")
PROJECT_FOLDER = os.path.join(BIOKB_FOLDER, PROJECT_NAME)
DATA_FOLDER = os.path.join(PROJECT_FOLDER, "data")
EXPORT_FOLDER = os.path.join(DATA_FOLDER, "ttls")
ZIPPED_TTLS_PATH = os.path.join(DATA_FOLDER, "ttls.zip")
SQLITE_PATH = os.path.join(BIOKB_FOLDER, f"{ORGANIZATION}.db")
DB_DEFAULT_CONNECTION_STR = "sqlite:///" + SQLITE_PATH
NEO4J_PASSWORD = "neo4j_password"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
LOGS_FOLDER = os.path.join(DATA_FOLDER, "logs")  # where to store log files
TABLE_PREFIX = PROJECT_NAME + "_"
os.makedirs(DATA_FOLDER, exist_ok=True)


# not standard for all biokb projects
DOWNLOAD_URL = "https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/new_taxdump/new_taxdump.zip"
PATH_TO_ZIP_FILE = os.path.join(DATA_FOLDER, "new_taxdump.zip")


class DmpFileName(StrEnum):
    NAME = "names.dmp"
    NODE = "nodes.dmp"
    RANKED_LINEAGE = "rankedlineage.dmp"


NODE_DTYPES: defaultdict[str, str] = defaultdict(
    str,
    {
        "tax_id": "int64",
        "parent_tax_id": "int64",
        "rank": "string",
        "embl_code": "string",
        "division_id": "int64",
        "inherited_div_flag": "bool",
        "genetic_code_id": "int64",
        "inherited_gc_flag": "bool",
        "mitochondrial_genetic_code_id": "int64",
        "inherited_mgc_flag": "bool",
        "genbank_hidden_flag": "bool",
        "hidden_subtree_root_flag": "bool",
        "comments": "string",
        "plastid_genetic_code_id": "Int64",
        "inherited_pgc_flag": "boolean",
        "specified_species": "boolean",
        "hydrogenosome_genetic_code_id": "Int64",
        "inherited_hgc_flag": "boolean",
    },
)

NODE_COLUMNS = list(NODE_DTYPES.keys())

NAME_DTYPES: dict[str, str] = {
    "tax_id": "int64",
    "name_txt": "string",
    "unique_name": "string",  # Nullable string
    "name_class": "string",
}
NAME_COLUMNS = list(NAME_DTYPES.keys())

RANKED_LINEAGE_DTYPES: defaultdict[str, str] = defaultdict(
    str,
    {
        "tax_id": "int32",
        "tax_name": "string",
        "species": "string",
        "genus": "string",
        "family": "string",
        "order": "string",
        "class_": "string",
        "phylum": "string",
        "kingdom": "string",
        "domain": "string",
    },
)

RANKED_LINEAGE_COLUMNS = list(RANKED_LINEAGE_DTYPES.keys())
