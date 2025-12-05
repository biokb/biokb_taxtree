import logging
import zipfile
from os import getenv, listdir, path
from typing import LiteralString, cast

from neo4j import GraphDatabase
from rdflib import Graph
from rdflib_neo4j import HANDLE_VOCAB_URI_STRATEGY, Neo4jStore, Neo4jStoreConfig
from tqdm import tqdm

from biokb_taxtree.constants import (
    BASIC_NODE_LABEL,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USER,
    ZIPPED_TTLS_PATH,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger: logging.Logger = logging.getLogger(name=__name__)


class Neo4jImporter:

    def __init__(
        self,
        neo4j_uri: str | None = None,
        neo4j_user: str | None = None,
        neo4j_pwd: str | None = None,
    ) -> None:
        """
        Initialize the Neo4j importer with connection credentials.
        Args:
            neo4j_uri (str | None, optional): Neo4j database URI.
                Defaults to NEO4J_URI environment variable or NEO4J_URI constant.
            neo4j_user (str | None, optional): Neo4j database username.
                Defaults to NEO4J_USER environment variable or NEO4J_USER constant.
            neo4j_pwd (str | None, optional): Neo4j database password.
                Defaults to NEO4J_PASSWORD environment variable or NEO4J_PASSWORD constant.
        Attributes:
            neo4j_uri (str): The Neo4j connection URI used by the driver.
            neo4j_user (str): The Neo4j username for authentication.
            neo4j_pwd (str): The Neo4j password for authentication.
            driver: Neo4j GraphDatabase driver instance for executing queries.
        Note:
            Connection parameters are resolved with the following priority:
            1. Explicitly provided parameters
            2. Environment variables (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
            3. Module-level constants (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        """
        self.neo4j_uri = neo4j_uri if neo4j_uri else getenv("NEO4J_URI", NEO4J_URI)
        self.neo4j_user = neo4j_user if neo4j_user else getenv("NEO4J_USER", NEO4J_USER)
        self.neo4j_pwd = (
            neo4j_pwd if neo4j_pwd else getenv("NEO4J_PASSWORD", NEO4J_PASSWORD)
        )

        self.driver = GraphDatabase.driver(
            self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_pwd)
        )

    def _delete_nodes_with_label(self, node_label: str = BASIC_NODE_LABEL):
        """Delete an existing graph in Neo4J.

        Args:
            node_label (str): The label of the nodes to delete.
        """
        logger.info("Delete an existing graph in Neo4J with node label %s.", node_label)
        with self.driver.session() as session:
            cypher: str = f"""MATCH (n:{node_label})
                CALL (n) {{
                WITH n
                DETACH DELETE n
                }} IN TRANSACTIONS OF 1000 ROWS;"""
            cypher = cast(LiteralString, cypher)
            session.run(cypher)

    def import_ttl(self, path_or_list: str | list[str]) -> bool:
        """Import single turtle file in Neo4J.

        Args:
            path_or_list (str | list[str]): Path to the turtle file, list of files, or zip file.
            delete_nodes_label (str | None): If provided, delete nodes with this label before import.

        Returns:
            bool: True if import is successful.
        """
        logger.info("Start importing all turtle file in Neo4J.")
        self._delete_nodes_with_label()
        self._delete_nodes_with_label("DbTdwgLocation")
        neo4j_db = self.__get_neo4j_db()

        if isinstance(path_or_list, list):
            for p in path_or_list:
                neo4j_db.parse(p, format="ttl")
        elif path_or_list.endswith(".ttl"):
            neo4j_db.parse(path_or_list, format="ttl")
        elif path.isdir(path_or_list):
            ttl_files = [
                path.join(path_or_list, f)
                for f in listdir(path_or_list)
                if f.endswith(".ttl")
            ]
            with tqdm(ttl_files) as pbar:
                for ttl_file in pbar:
                    pbar.set_description(f"Processing {ttl_file}")
                    neo4j_db.parse(ttl_file, format="ttl")
        elif path_or_list.endswith(".zip"):
            self.__import_turtle_files_from_zip(path, neo4j_db)
        neo4j_db.close(True)

        return True

    def __import_turtle_files_from_zip(self, path_ttl_file_or_zip, neo4j_db):
        """Import turtle files from a zip file into Neo4J.
        Args:
            path_ttl_file_or_zip (str): Path to the zip file containing turtle files.
            neo4j_db (Graph): The Neo4J Graph database connection.
        """
        with zipfile.ZipFile(path_ttl_file_or_zip, "r") as z:
            turtle_file_names = [x for x in z.namelist() if x.endswith(".ttl")]
            with tqdm(turtle_file_names) as pbar:
                for turtle_file_name in pbar:
                    pbar.set_description(f"Processing {turtle_file_name}")
                    with z.open(turtle_file_name) as file_io:
                        neo4j_db.parse(file_io, format="ttl")

    def __get_neo4j_db(self) -> Graph:
        """Get the Neo4j Graph database connection."""
        with self.driver.session() as session:
            cypher = (
                "CREATE CONSTRAINT n10s_unique_uri IF NOT EXISTS "
                "FOR (r:Resource) REQUIRE r.uri IS UNIQUE"
            )
            session.run(cypher)
            self.driver.close()

        auth_data = {
            "uri": self.neo4j_uri,
            "database": "neo4j",
            "user": self.neo4j_user,
            "pwd": self.neo4j_pwd,
        }

        config = Neo4jStoreConfig(
            auth_data=auth_data,
            custom_prefixes={},
            handle_vocab_uri_strategy=HANDLE_VOCAB_URI_STRATEGY.IGNORE,
            batching=True,
        )

        neo4j_db = Graph(store=Neo4jStore(config=config))
        return neo4j_db

    def import_ttls(self, delete_existing_graph: bool = True) -> bool:
        """Import all turtle file in Neo4J from zipped turtle files.

        Args:
            delete_existing_graph (bool): Whether to delete existing graph before import.
        Returns:
            bool: True if import is successful."""
        logger.info("Start importing all turtle file in Neo4J.")

        if delete_existing_graph:
            self._delete_nodes_with_label()
        neo4j_db = self.__get_neo4j_db()

        self.__import_turtle_files_from_zip(ZIPPED_TTLS_PATH, neo4j_db)
        neo4j_db.close(True)

        return True
