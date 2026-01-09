"""Module to create RDF turtle files from the BRENDA imported data."""

import logging
import os.path
import shutil
from typing import Optional

from rdflib import RDF, XSD, Graph, Literal, URIRef
from sqlalchemy import Engine, create_engine, event, select
from sqlalchemy.orm import sessionmaker

from biokb_taxtree import constants
from biokb_taxtree.db import models
from biokb_taxtree.rdf import namespaces as ns

logger = logging.getLogger(__name__)


def get_empty_graph() -> Graph:
    """Return an empty RDFlib.Graph with all needed namespaces"""
    graph = Graph()
    graph.bind(prefix="n", namespace=ns.NODE_NS)
    graph.bind(prefix="r", namespace=ns.RELATION_NS)
    graph.bind(prefix="t", namespace=ns.NCBI_TAXON_NS)
    graph.bind(prefix="xs", namespace=XSD)
    return graph


class TurtleCreator:
    def __init__(
        self,
        engine: Engine | None = None,
        data_folder: str | None = None,
    ) -> None:
        """Class to create turtle files.

        Args:
            engine (Engine | None, optional): Default MySQL engine from congif.ini if None.
            export_to_folder (str | None, optional): Default export folder if None.
            data_folder (str | None, optional): Default data folder if None.

        Raises:
            Exception: _description_
        """
        self.__ttls_folder = constants.EXPORT_FOLDER
        connection_str = os.getenv(
            "CONNECTION_STR", constants.DB_DEFAULT_CONNECTION_STR
        )
        self.__engine = engine if engine else create_engine(connection_str)
        logger.info(f"Using database connection: {self.__engine.url}")
        self.Session = sessionmaker(bind=self.__engine)

    def _set_ttls_folder(self, export_to_folder: str) -> None:
        """Sets the export folder path.

        This is mainly for testing purposes.
        """
        self.__ttls_folder = export_to_folder

    def create_ttls(
        self,
        start_from_tax_ids: list[int] = [2157, 2, 2759, 10239],
    ) -> str:
        """Create all RDF turtle, zip all files and returns the path to the zipped file.

        By default it creates 6 files for the following tax ids:
        - 2157: Archaea
        - 2: Bacteria
        - 2759: Eukaryota
        - 10239: Viruses

        Not included:
        - 28384: other sequences
        - 12908: unclassified sequences



        Returns:
            str: path to zip file
        """
        os.makedirs(constants.EXPORT_FOLDER, exist_ok=True)
        logging.info("Start creating turtle files.")
        self.__create_nodes_ttl(start_from_tax_ids)
        path_to_zip_file: str = self.create_zip_from_all_ttls()
        return path_to_zip_file

    def __create_nodes_ttl(self, start_from_tax_ids: list[int]) -> None:
        """Create the nodes turtle file."""
        no = models.Node
        na = models.Name

        with self.Session() as session:
            if start_from_tax_ids:
                for start_from_tax_id in start_from_tax_ids:
                    graph = get_empty_graph()
                    taxon = (
                        session.query(no).filter_by(tax_id=start_from_tax_id).first()
                    )
                    if not taxon:
                        logging.warning(
                            "Tax id %s not found in database. Skipping...",
                            start_from_tax_id,
                        )
                        continue
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
                        node = URIRef(ns.NCBI_TAXON_NS[str(taxon.tax_id)])
                        graph.add(
                            (
                                node,
                                RDF.type,
                                ns.NODE_NS.DbNCBITaxTree,
                            )
                        )
                        graph.add(
                            (
                                node,
                                RDF.type,
                                ns.NODE_NS.Taxon,
                            )
                        )
                        graph.add(
                            (
                                node,
                                ns.RELATION_NS.scientific_name,
                                Literal(
                                    taxon.name_txt,
                                    datatype=XSD.string,
                                ),
                            )
                        )
                        graph.add(
                            (
                                node,
                                ns.RELATION_NS.rank,
                                Literal(
                                    taxon.rank,
                                    datatype=XSD.string,
                                ),
                            )
                        )
                        graph.add(
                            (
                                ns.NCBI_TAXON_NS[str(taxon.tax_id)],
                                ns.RELATION_NS.HAS_PARENT,
                                ns.NCBI_TAXON_NS[str(int(taxon.parent_tax_id))],
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


def create_ttls(
    engine: Optional[Engine] = None,
    export_to_folder: Optional[str] = None,
) -> str:
    """Create all turtle files.

    If engine=None tries to get the settings from config ini file

    If export_to_folder=None takes the default path.

    Args:
        engine (Engine | None, optional): SQLAlchemy class. Defaults to None.
        export_to_folder (str | None, optional): Folder to export ttl files.
            Defaults to None.

    Returns:
        str: path zipped file with ttls.
    """
    ttl_creator = TurtleCreator(engine=engine)
    if export_to_folder:
        ttl_creator._set_ttls_folder(export_to_folder)
    return ttl_creator.create_ttls()
