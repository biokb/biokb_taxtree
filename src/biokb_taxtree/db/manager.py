import logging
import os
import sqlite3
from typing import Optional

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session
from sqlalchemy.orm.session import sessionmaker as Sm

from biokb_taxtree.constants import DB_DEFAULT_CONNECTION_STR
from biokb_taxtree.db import models
from biokb_taxtree.db.importer import DbImporter
from biokb_taxtree.db.query import DbQuery
from biokb_taxtree.logger import setup_logging

setup_logging()

logger = logging.getLogger("manager")


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(
    dbapi_connection: sqlite3.Connection, _connection_record: object
) -> None:
    """Enable foreign key constraint for SQLite."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class DbManager:
    """
    Manages database operations, including creating, dropping, and importing data from TSV files.
    """

    def __init__(
        self,
        engine: Optional[Engine] = None,
    ) -> None:
        """
        Initialize the DbManager with a database engine and path to the data files.

        Args:
            engine: SQLAlchemy database engine instance.
            path_to_file (str): Path to the directory containing TSV files.
        """
        connection_str = os.getenv("CONNECTION_STR", DB_DEFAULT_CONNECTION_STR)
        self.__engine = engine if engine else create_engine(connection_str)
        logger.info("Engine %s", self.__engine)
        self.Session: Sm = sessionmaker(bind=self.__engine)
        self.__importer: Optional[DbImporter] = None
        self.__query: Optional[DbQuery] = None

    @property
    def session(self) -> Session:
        """Get a new SQLAlchemy session.

        Returns:
            Session: SQLAlchemy session
        """
        return self.Session()

    def recreate_db(self) -> None:
        """Recreate the database by dropping and creating all tables."""
        models.Base.metadata.create_all(self.__engine)
        models.Base.metadata.drop_all(self.__engine)

    @property
    def _importer(self) -> DbImporter:
        if not self.__importer:
            self.__importer = DbImporter(self.__engine)
        return self.__importer

    @property
    def query(self) -> DbQuery:
        if not self.__query:
            self.__query = DbQuery(self.__engine)
        return self.__query

    def set_importer(self, importer=None) -> None:
        self.__importer = importer

    def import_data(
        self, force_download: bool = False, keep_files: bool = False
    ) -> dict[str, int]:
        return self._importer.import_data(
            force_download=force_download, keep_files=keep_files
        )


def import_data(
    engine: Optional[Engine] = None,
    force_download: bool = False,
    keep_files: bool = False,
) -> dict[str, int]:
    """Import all data in database.

    Args:
        engine (Optional[Engine]): SQLAlchemy engine. Defaults to None.
        force_download (bool, optional): If True, will force download the data, even if
            files already exist. If False, it will skip the downloading part if files
            already exist locally. Defaults to False.
        keep_files (bool, optional): If True, downloaded files are kept after import.
            Defaults to False.

    Returns:
        Dict[str, int]: table=key and number of inserted=value
    """
    db_manager = DbManager(engine)
    return db_manager.import_data(force_download=force_download, keep_files=keep_files)


def get_session(engine: Optional[Engine] = None) -> Session:
    """Get a new SQLAlchemy session.

    Returns:
        Session: SQLAlchemy session
    """
    db_manager = DbManager(engine)
    return db_manager.session
