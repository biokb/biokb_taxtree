import logging
import os
import urllib.request
import zipfile
from collections import defaultdict, namedtuple
from dataclasses import dataclass
from typing import Optional

import pandas as pd
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import sessionmaker as Sm

from biokb_taxtree.constants import (
    DATA_FOLDER,
    DB_DEFAULT_CONNECTION_STR,
    DOWNLOAD_URL,
    NAME_COLUMNS,
    NODE_COLUMNS,
    NODE_DTYPES,
    PATH_TO_ZIP_FILE,
    RANKED_LINEAGE_COLUMNS,
    RANKED_LINEAGE_DTYPES,
    DmpFileName,
)
from biokb_taxtree.db import models
from biokb_taxtree.logger import setup_logging

setup_logging()

logger = logging.getLogger("importer")


Mapper = namedtuple("Mapper", ["parent_tax_id", "tree_id"])


@dataclass
class TreeEntry:
    tree_id: int
    tree_parent_id: Optional[int]
    tax_id: int
    level: int
    right_tree_id: Optional[int] = None
    is_leaf: Optional[bool] = False


class DbImporter:

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
        self.Session: Sm = sessionmaker(bind=self.engine)
        self._path_data_folder: str = DATA_FOLDER
        self._path_zip_file: str = PATH_TO_ZIP_FILE

    def _set_path_zip_file(self, path_zip_file: str) -> None:
        if not os.path.exists(path_zip_file):
            raise FileNotFoundError(f"Zip file {path_zip_file} does not exist.")
        self._path_zip_file = path_zip_file

    def import_data(
        self, force_download: bool = False, keep_files: bool = False
    ) -> dict[str, int]:
        logger.info(f"Start import data with engine {self.engine}")

        if force_download or not os.path.exists(self._path_zip_file):
            logger.info("Start downloading")
            urllib.request.urlretrieve(DOWNLOAD_URL, self._path_zip_file)

        self.recreate_db()

        self.__activate_foreign_key_check_in_sqlite()

        import_rows: dict[str, int] = {}
        import_rows.update(self.__import_nodes())
        import_rows.update(self.__import_ranked_lineage())
        import_rows.update(self.__import_names())

        if not keep_files and os.path.exists(self._path_zip_file):
            os.remove(self._path_zip_file)
            logger.info(f"Removed download file")

        logger.info("Data imported.")
        return import_rows

    def __activate_foreign_key_check_in_sqlite(self) -> None:
        """Activate foreign key check in SQLite if engine is SQLite."""
        if self.engine.name == "sqlite":
            with self.Session() as session:
                session.execute(text("PRAGMA foreign_keys = ON"))

    def recreate_db(self):
        """Recreate the database by dropping and creating all tables."""
        models.Base.metadata.drop_all(self.engine)
        models.Base.metadata.create_all(self.engine)

    def __get_parent_child_dict(self, df_nodes: pd.DataFrame) -> dict[int, list[int]]:
        """Returns a dictionary of parent_tax_id:child_tax_ids from the nodes data

        Returns:
            dict[int, list[int]]: parent children dictionary
        """
        pc_dict = (
            df_nodes[["tax_id", "parent_tax_id"]]
            .groupby("parent_tax_id")["tax_id"]
            .apply(list)
            .to_dict()
        )
        # Remove the tax ID 1 as its own child/parent (causes problems in the database)
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

    def __get_tree_df(self, df_nodes: pd.DataFrame) -> pd.DataFrame:
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

        self.__set_right_tree_ids(tree)

        return pd.DataFrame(list(tree.values())).set_index("tax_id")

    def __set_right_tree_ids(self, tree: dict[int, TreeEntry]):
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




        Assigns the right_tree_id for entries in a parent–child tree.

        The right_tree_id of a node is the tree ID you should jump to when moving
        "to the right" of the node's subtree at the same depth:
        - If the node has right siblings (siblings with a greater tree_id), right_tree_id
            is the smallest tree_id among those right siblings (i.e., the immediate next sibling).
        - If the node has no right sibling, right_tree_id is inherited from its parent,
            meaning it points to the next position to the right of the parent's subtree.
        - For the root node (tree_id == 1), right_tree_id is set to max(existing_tree_id) + 1,
            acting as a sentinel that marks the end of the rightward traversal.

        Notes:
        - Only the root and non-leaf nodes with a parent are updated by this method; leaf nodes
            are not explicitly modified here.
        - This mapping allows constant-time jumps to the next "right" position in a pre-order/
            sibling traversal without scanning siblings.

                tree (dict[int, TreeEntry]): Dictionary of TreeEntry objects keyed by their tree_id.
                        Each entry must provide:
                        - tree_parent_id (int | None): The parent node's ID, or None for the root.
                        - is_leaf (bool): Whether the node is a leaf.
                        - right_tree_id (int | None): Will be set/updated by this method.

        Side effects:
                Mutates TreeEntry.right_tree_id for applicable nodes.

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
            elif e.tree_parent_id != None:
                # get all siblings right to entry
                sibling_tree_ids = [
                    x for x in tree_pc_dict[e.tree_parent_id] if x > tree_id
                ]
                # if siblings right to entry exists get sibling with the lowest tree id
                if sibling_tree_ids:
                    e.right_tree_id = min(sibling_tree_ids)
                # else get right tree id from parent
                else:
                    e.right_tree_id = tree[e.tree_parent_id].right_tree_id

    def __import_nodes(self) -> dict[str, int]:
        """Imports taxonomic nodes in the database."""
        logger.info(f"Start import nodes")

        with zipfile.ZipFile(PATH_TO_ZIP_FILE) as z:
            with z.open(DmpFileName.NODE) as f:
                df = pd.read_csv(
                    f,
                    sep=r"\t\|\t|\t\|$",
                    header=None,
                    names=NODE_COLUMNS,
                    dtype=NODE_DTYPES,
                    true_values=["1"],
                    false_values=["0"],
                    engine="python",
                    usecols=range(len(NODE_COLUMNS)),
                )

        df_tree = self.__get_tree_df(df)
        imported_rows = (
            df.set_index("tax_id")
            .join(df_tree)
            .to_sql(
                models.Node.__tablename__,
                self.engine,
                if_exists="append",
                index=True,
                chunksize=100000,
            )
        )
        return {models.Node.__tablename__: imported_rows or 0}

    def __import_names(self) -> dict[str, int]:
        """Imports taxonomic names into the database."""

        logger.info(f"Start import names")
        with zipfile.ZipFile(PATH_TO_ZIP_FILE) as z:
            with z.open(DmpFileName.NAME) as f:
                df = pd.read_csv(
                    f,
                    sep=r"\t\|\t|\t\|$",
                    header=None,
                    usecols=range(len(NAME_COLUMNS)),
                    names=NAME_COLUMNS,
                    engine="python",
                )
        imported_rows = df.to_sql(
            models.Name.__tablename__,
            self.engine,
            if_exists="append",
            index=False,
            chunksize=100000,
        )
        return {models.Name.__tablename__: imported_rows or 0}

    def __import_ranked_lineage(self) -> dict[str, int]:
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
        with zipfile.ZipFile(PATH_TO_ZIP_FILE) as z:
            with z.open(DmpFileName.RANKED_LINEAGE) as f:
                df = pd.read_csv(
                    f,
                    sep=r"\t\|\t|\t\|$",
                    engine="python",
                    dtype=RANKED_LINEAGE_DTYPES,
                    header=None,
                    names=RANKED_LINEAGE_COLUMNS,
                    true_values=["1"],
                    false_values=["0"],
                    index_col=False,
                )
        df.domain = df.domain.str.rstrip("\t|")
        df.replace({pd.NA: None}, inplace=True)
        df.set_index("tax_id", inplace=True)
        imported_rows = df.to_sql(
            models.RankedLineage.__tablename__,
            self.engine,
            if_exists="append",
            chunksize=100000,
        )
        return {models.RankedLineage.__tablename__: imported_rows or 0}
