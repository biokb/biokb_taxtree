import logging
import os
import shutil
from collections import defaultdict, namedtuple
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import sessionmaker as Sm

from biokb_taxtree.constants import (
    DB_DEFAULT_CONNECTION_STR,
    DEFAULT_PATH_UNZIPPED_DATA_FOLDER,
    NAME_COLUMNS,
    NODE_COLUMNS,
    NODE_DTYPES,
    RANKED_LINEAGE_COLUMNS,
    RANKED_LINEAGE_DTYPES,
    DmpFileName,
)
from biokb_taxtree.db import models
from biokb_taxtree.db.models import Name, Node
from biokb_taxtree.tools import download_and_unzip

# Setup logging for debugging and better error tracking
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Mapper = namedtuple("Mapper", ["parent_tax_id", "tree_id"])


@dataclass
class TreeEntry:
    tree_id: int
    tree_parent_id: Optional[int]
    tax_id: int
    level: int
    right_tree_id: Optional[int] = None
    is_leaf: Optional[bool] = False


class DbManager:
    """
    Manages database operations, including creating, dropping, and importing data from TSV files.
    """

    def __init__(
        self,
        engine: Optional[Engine] = None,
        path_data_folder: Optional[str] = None,
        force_download: bool = False,
    ):
        """
        Initialize the DbManager with a database engine and path to the data files.

        Args:
            engine: SQLAlchemy database engine instance.
            path_to_file (str): Path to the directory containing TSV files.
        """
        connection_str = os.getenv("CONNECTION_STR", DB_DEFAULT_CONNECTION_STR)
        self.engine = engine if engine else create_engine(connection_str)
        self.Session: Sm = sessionmaker(bind=self.engine)
        self.path_data_folder = path_data_folder
        self.force_download = force_download

    def __get_parent_child_dict(self, df_nodes: pd.DataFrame) -> dict[int, list[int]]:
        """Returns a dictionary of parent_tax_id:child_tax_ids

        Returns:
            dict[int, list[int]]: parent children dictionary
        """
        pc_dict = (
            df_nodes[["tax_id", "parent_tax_id"]]
            .groupby("parent_tax_id")["tax_id"]
            .apply(list)
            .to_dict()
        )
        pc_dict[1].remove(1)
        return pc_dict

    def __get_tree(
        self,
        tree_entry: TreeEntry,
        pc_dict: dict[int, list[int]],
        level=0,
        tree_id=1,
        tree: dict[int, TreeEntry] = {},
    ):
        tax_id = tree_entry.tax_id
        tree[tree_entry.tree_id] = tree_entry
        children = pc_dict.get(tax_id, [])
        level += 1
        for child_tax_id in children:
            new_tree_id = tree_id + 1
            new_tree_entry = TreeEntry(
                tree_id=new_tree_id,
                tree_parent_id=tree_entry.tree_id,
                tax_id=child_tax_id,
                level=level,
                is_leaf=not bool(child_tax_id in pc_dict),
            )
            tree, tree_id = self.__get_tree(
                tree_entry=new_tree_entry,
                pc_dict=pc_dict,
                level=level,
                tree_id=new_tree_id,
                tree=tree,
            )
        return tree, tree_id

    def get_tree_df(self, df_nodes: pd.DataFrame) -> pd.DataFrame:
        """Get taxonomy tree as DataFrame

        Args:
            df_nodes (pd.DataFrame): _description_

        Returns:
            pd.DataFrame: _description_
        """
        pc_dict = self.__get_parent_child_dict(df_nodes)
        root = TreeEntry(
            tree_id=1, tax_id=1, tree_parent_id=None, level=1, is_leaf=False
        )
        tree, number_of_nodes = self.__get_tree(root, pc_dict)

        self.set_right_tree_ids(tree)

        return pd.DataFrame(list(tree.values())).set_index("tax_id")

    def set_right_tree_ids(self, tree: dict[int, TreeEntry]):
        """
        Assigns the `right_tree_id` attribute for each entry in the tree.

        Calculates and sets the `right_tree_id` for each `TreeEntry` in the
        provided tree structure. The `right_tree_id` is determined based on the tree's
        hierarchical relationships and sibling positions.

        Args:
            tree (dict[int, TreeEntry]): A dictionary representing the tree structure,
                where the keys are tree IDs and the values are `TreeEntry` objects.

        Modifies:
            The `right_tree_id` attribute of each `TreeEntry` in the `tree` dictionary.
        """

        tree_pc_dict = defaultdict(list)
        for child_tree_id, e in tree.items():
            if e.tree_parent_id:
                tree_pc_dict[e.tree_parent_id].append(child_tree_id)

        tree_cp_dict = {}
        for child_tree_id, tree_entry in tree.items():
            if tree_entry.tree_parent_id:
                tree_cp_dict[child_tree_id] = tree_entry.tree_parent_id

        max_tree_id = max(tree_cp_dict)
        e: TreeEntry
        for tree_id, e in tree.items():
            if tree_id == 1:
                e.right_tree_id = max_tree_id + 1
            # check if id not leaf and parent tree id exists
            elif not e.is_leaf and e.tree_parent_id != None:
                # get all siblings right to entry
                sibling_tree_ids = [
                    x for x in tree_pc_dict[e.tree_parent_id] if x > tree_id
                ]
                # if siblings right to entry exists get sibling with the lowest tree id
                if sibling_tree_ids:
                    e.right_tree_id = min(sibling_tree_ids)
                else:
                    e.right_tree_id = tree[e.tree_parent_id].right_tree_id

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
    def all_tables_have_data(self) -> bool:
        """Checks if all tables have data

        Returns:
            bool: True if all tables have data.
        """
        self.create_db()  # create tables if not exists
        with self.Session() as session:
            exists = []
            for model in (Name, Node):
                exists.append(session.query(model).count())
        return all(exists)

    def activate_foreign_key_check_in_sqlite(self):
        """Activate foreign key check in SQLite if engine is SQLite."""
        if self.engine.name == "sqlite":
            with self.Session() as session:
                session.execute(text("PRAGMA foreign_keys = ON"))

    def deactivate_foreign_key_check_in_sqlite(self):
        if self.engine.name == "sqlite":
            with self.Session() as session:
                session.execute(text("PRAGMA foreign_keys = OFF"))

    def import_data(self, only_if_db_empty: Optional[bool] = True):
        """Import downloaded data into database.

        If only_if_db_empty=True imports data, if at least one table is empty.

        Args:
            only_if_db_empty (bool, optional): imports if at least one table is empty. Defaults to False.
        """
        if only_if_db_empty and self.all_tables_have_data:
            return

        logger.info(f"Start import data with engine {self.engine}")
        if not self.path_data_folder:
            self.path_data_folder = download_and_unzip(self.force_download)

        self.recreate_db()

        self.activate_foreign_key_check_in_sqlite()

        self.import_nodes()
        self.import_ranked_lineage()
        self.import_names()

        if self.path_data_folder == DEFAULT_PATH_UNZIPPED_DATA_FOLDER:
            shutil.rmtree(DEFAULT_PATH_UNZIPPED_DATA_FOLDER)

        logger.info("Data imported.")

    def import_ranked_lineage(self):
        """
        Imports ranked lineage data from `rankedlineage.dmp` into the database.

        Reads `rankedlineage.dmp` containing ranked lineage data,
        processes it, and inserts the data into the database table associated
        with the `RankedLineage` model.



        Raises:
            FileNotFoundError: If the ranked lineage file does not exist.
            pandas.errors.ParserError: If there is an error while parsing the file.
            sqlalchemy.exc.SQLAlchemyError: If there is an error during the database
                insertion process.
        """

        logger.info(f"Start import ranked lineage")
        file_path = os.path.join(
            DEFAULT_PATH_UNZIPPED_DATA_FOLDER, DmpFileName.RANKED_LINEAGE
        )
        df = pd.read_csv(
            file_path,
            sep=r"\t\|\t",
            engine="python",
            dtype=RANKED_LINEAGE_DTYPES,
            header=None,
            names=RANKED_LINEAGE_COLUMNS,
            index_col=False,
        )
        df.superkingdom = df.superkingdom.str.rstrip("\t|")
        df.replace({pd.NA: None}, inplace=True)
        df.set_index("tax_id", inplace=True)
        df.to_sql(
            models.RankedLineage.__tablename__,
            self.engine,
            if_exists="append",
            chunksize=100000,
        )

    def import_nodes(self):
        """
        Imports taxonomic nodes data from `names.dmp`, processes it, and stores it in the database.

        Reads `names.dmp` containing taxonomic node information, processes the data
        to generate a tree structure, and inserts the resulting data into the database table associated
        with the `Node` model.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If the file format is invalid or does not match the expected structure.
        """

        logger.info(f"Start import nodes")
        path = os.path.join(DEFAULT_PATH_UNZIPPED_DATA_FOLDER, DmpFileName.NODE)
        df = pd.read_csv(
            path,
            sep=r"\t\|\t",
            header=None,
            names=NODE_COLUMNS,
            engine="python",
            dtype=NODE_DTYPES,
        )
        df_tree = self.get_tree_df(df)
        df.set_index("tax_id").join(df_tree).to_sql(
            Node.__tablename__,
            self.engine,
            if_exists="append",
            index=True,
            chunksize=100000,
        )

    def import_names(self):
        """
        Imports taxonomic names from `names.dmp` into the database.

        Reads `names.dmp` containing taxonomic names,
        processes the data, and inserts it into the database table associated
        with the `Name` model.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            pandas.errors.ParserError: If there is an issue parsing the file.
            sqlalchemy.exc.SQLAlchemyError: If there is an error during the database operation.
        """

        logger.info(f"Start import names")
        path = os.path.join(DEFAULT_PATH_UNZIPPED_DATA_FOLDER, DmpFileName.NAME)
        df = pd.read_csv(
            path,
            sep=r"\t\|\t",
            header=None,
            names=NAME_COLUMNS,
            engine="python",
        )
        df.name_class = df.name_class.str.rstrip("\t|")
        df.to_sql(
            Name.__tablename__,
            self.engine,
            if_exists="append",
            index=False,
            chunksize=100000,
        )
