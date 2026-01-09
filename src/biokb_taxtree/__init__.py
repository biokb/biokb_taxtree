from importlib.metadata import PackageNotFoundError, version

from biokb_taxtree.db import models
from biokb_taxtree.db.manager import DbManager, get_session, import_data
from biokb_taxtree.rdf.neo4j_importer import Neo4jImporter, import_ttls
from biokb_taxtree.rdf.turtle import TurtleCreator, create_ttls

try:
    __version__ = version("biokb_taxtree")
except PackageNotFoundError:
    # Package is not installed (e.g., during local development)
    __version__ = "unknown"

__all__ = [
    "DbManager",
    "import_data",
    "get_session",
    "Neo4jImporter",
    "import_ttls",
    "TurtleCreator",
    "create_ttls",
    "models",
]
