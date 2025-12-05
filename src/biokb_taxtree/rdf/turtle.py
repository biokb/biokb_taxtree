"""Module to create RDF turtle files from the BRENDA imported data."""

import logging
import os.path
import shutil
from typing import Optional

from rdflib import RDF, XSD, Graph, Literal, Namespace, URIRef
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import sessionmaker

from biokb_taxtree import constants
from biokb_taxtree.db import models
from biokb_taxtree.db.manager import DbManager
from biokb_taxtree.rdf import namespaces

logger = logging.getLogger(__name__)


def get_empty_graph():
    """Return an empty RDFlib.Graph with all needed namespaces"""
    graph = Graph()
    graph.bind(prefix="n", namespace=namespaces.NODE_NS)
    graph.bind(prefix="r", namespace=namespaces.RELATION_NS)
    graph.bind(prefix="t", namespace=namespaces.NCBI_TAXON_NS)
    graph.bind(prefix="xs", namespace=XSD)
    return graph


class TurtleCreator:
    def __init__(
        self,
        engine: Engine | None = None,
        data_folder: str | None = None,
    ):
        """Class to create turtle files.

        Args:
            engine (Engine | None, optional): Default MySQL engine from congif.ini if None.
            export_to_folder (str | None, optional): Default export folder if None.
            data_folder (str | None, optional): Default data folder if None.

        Raises:
            Exception: _description_
        """
        self.__ttls_folder = constants.TTL_EXPORT_FOLDER
        self.__data_folder = data_folder or constants.DATA_FOLDER
        connection_str = os.getenv(
            "MYSQL_CONNECTION_STR", constants.DB_DEFAULT_CONNECTION_STR
        )
        self.engine = engine if engine else create_engine(connection_str)
        logger.info(f"Using database connection: {self.engine.url}")
        self.Session = sessionmaker(bind=self.engine)

        self.__engine = DbManager(engine).engine

    def create_ttls(self, start_from_tax_ids: list[int] = [1]) -> str:
        """Create all RDF turtle, zip all files and returns the path to the zipped file.

        Returns:
            str: path to zip file
        """
        os.makedirs(constants.TTL_EXPORT_FOLDER, exist_ok=True)
        logging.info("Start creating turtle files.")
        self.__create_nodes_ttl(start_from_tax_ids)
        path_to_zip_file: str = self.create_zip_from_all_ttls()
        logging.info(f"Turtle files zipped in {path_to_zip_file} .")
        return path_to_zip_file

    def __create_nodes_ttl(self, start_from_tax_ids: Optional[list[int]] = None):
        """Create the nodes turtle file."""
        no = models.Node
        na = models.Name

        with self.Session() as session:
            if start_from_tax_ids:
                for start_from_tax_id in start_from_tax_ids:
                    graph = get_empty_graph()
                    taxon = session.query(no).filter_by(tax_id=start_from_tax_id).one()
                    stmt = (
                        select(no.tax_id, no.parent_tax_id, no.rank, na.name_txt)
                        .join(na)
                        .where(
                            no.tree_id >= taxon.tree_id,
                            no.tree_id <= taxon.right_tree_id,
                            na.name_class == "scientific name",
                        )
                    )
                    taxons = session.execute(stmt).all()
                    for taxon in taxons:
                        node = URIRef(namespaces.NCBI_TAXON_NS[str(taxon.tax_id)])
                        graph.add(
                            (
                                node,
                                RDF.type,
                                namespaces.NODE_NS.DbNCBITaxTree,
                            )
                        )
                        graph.add(
                            (
                                node,
                                RDF.type,
                                namespaces.NODE_NS.Taxon,
                            )
                        )
                        graph.add(
                            (
                                node,
                                namespaces.RELATION_NS.scientific_name,
                                Literal(
                                    taxon.name_txt,
                                    datatype=XSD.string,
                                ),
                            )
                        )
                        graph.add(
                            (
                                node,
                                namespaces.RELATION_NS.rank,
                                Literal(
                                    taxon.rank,
                                    datatype=XSD.string,
                                ),
                            )
                        )
                        graph.add(
                            (
                                namespaces.NCBI_TAXON_NS[str(taxon.tax_id)],
                                namespaces.RELATION_NS.HAS_PARENT,
                                namespaces.NCBI_TAXON_NS[str(int(taxon.parent_tax_id))],
                            )
                        )
                    # Serialize and save the graph
                    ttl_path = os.path.join(
                        self.__ttls_folder,
                        f"{no.__tablename__}_{start_from_tax_id}.ttl",
                    )
                    graph.serialize(ttl_path, format="turtle")
                    del graph

    def create_zip_from_all_ttls(self) -> str:
        """Create a zipped file from all turtle file and return the path.

        Returns:
            str: path to zipped file
        """
        path_to_zip_file = shutil.make_archive(
            base_name=self.__ttls_folder, format="zip", root_dir=self.__ttls_folder
        )
        shutil.rmtree(self.__ttls_folder)
        return path_to_zip_file
