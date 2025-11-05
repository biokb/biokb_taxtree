import logging
import os
from typing import Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import sessionmaker as Sm

from biokb_taxtree.db.query import DbQuery
from biokb_taxtree.logger import setup_logging

setup_logging()

logger = logging.getLogger("manager")

from biokb_taxtree.constants import DB_DEFAULT_CONNECTION_STR
from biokb_taxtree.db import models
from biokb_taxtree.db.importer import DbImporter


class DbManager:
    """
    Manages database operations, including creating, dropping, and importing data from TSV files.
    """

    def __init__(
        self,
        engine: Optional[Engine] = None,
    ):
        """
        Initialize the DbManager with a database engine and path to the data files.

        Args:
            engine: SQLAlchemy database engine instance.
            path_to_file (str): Path to the directory containing TSV files.
        """
        connection_str = os.getenv("CONNECTION_STR", DB_DEFAULT_CONNECTION_STR)
        self.engine = engine if engine else create_engine(connection_str)
        logger.info("Engine %s", self.engine)
        self.Session: Sm = sessionmaker(bind=self.engine)
        self.__importer: Optional[DbImporter] = None
        self.__query: Optional[DbQuery] = None

    def create_db(self):
        """Create all tables in the database."""
        models.Base.metadata.create_all(self.engine)

    def drop_db(self):
        """Drop all tables from the database."""
        models.Base.metadata.drop_all(self.engine)

    def recreate_db(self):
        """Recreate the database by dropping and creating all tables."""
        self.drop_db()
        self.create_db()

    @property
    def _importer(self):
        if not self.__importer:
            self.__importer = DbImporter(self.engine)
        return self.__importer

    @property
    def query(self):
        if not self.__query:
            self.__query = DbQuery(self.engine)
        return self.__query
    
    def set_importer(self, importer=None):
        self.__importer = importer

    def import_data(self, force: bool = False):
        return self._importer.import_data(force=force)
