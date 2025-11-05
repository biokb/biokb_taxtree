"""Module to create RDF turtle files from the BRENDA imported data."""

import io
import logging
import os.path
import shutil
import zipfile
from urllib.parse import urlparse
from urllib.request import urlretrieve

import numpy as np
import pandas as pd
from pandas import DataFrame
from rdflib import RDF, XSD, Graph, Literal, Namespace, URIRef
from sqlalchemy import Engine

from biokb_taxtree.constants.basic import DATA_FOLDER, EXPORT_FOLDER
from biokb_taxtree.constants.ncbi import TAXONOMY_URL
from biokb_taxtree.db.manager import DbManager
from biokb_taxtree.rdf import namespaces


def get_empty_graph():
    """Return an empty RDFlib.Graph with all needed namespaces"""
    graph = Graph()
    graph.bind(prefix="chebi", namespace=namespaces.chebi_ns)
    graph.bind(prefix="node", namespace=namespaces.node)
    graph.bind(prefix="rel", namespace=namespaces.relation)
    graph.bind(prefix="xs", namespace=XSD)
    graph.bind(prefix="ec", namespace=namespaces.ec_ns)
    graph.bind(prefix="reac", namespace=namespaces.reaction_ns)
    graph.bind(prefix="tax", namespace=namespaces.tax_ns)
    graph.bind(prefix="acti", namespace=namespaces.activation_ns)
    graph.bind(prefix="cof", namespace=namespaces.cofactor_ns)
    graph.bind(prefix="ic50", namespace=namespaces.ic50_ns)
    graph.bind(prefix="kcatkm", namespace=namespaces.kcat_km_ns)
    graph.bind(prefix="ki", namespace=namespaces.ki_ns)
    graph.bind(prefix="km", namespace=namespaces.km_ns)
    graph.bind(prefix="comp", namespace=namespaces.compound_ns)
    graph.bind(prefix="loc", namespace=namespaces.location_ns)
    graph.bind(prefix="mi", namespace=namespaces.metal_ion_ns)
    graph.bind(prefix="nspreac", namespace=namespaces.nsp_reaction_ns)
    graph.bind(prefix="spreac", namespace=namespaces.sp_reaction_ns)
    return graph


def recursive_get_parents(
    df_tree: DataFrame, parent_id: int, tax_ids: set[int] = set()
) -> set[int]:
    """Get all parents up to the root for a given parent_id.

    Args:
        parent_id (_type_): starting taxonomy ID
        tax_ids (set[int], optional): Collected taxonomy IDs. Defaults to set().

    Returns:
        set[int]: whole path up to the root
    """
    tax_ids.add(parent_id)
    current_id = df_tree.loc[parent_id, "parent_tax_id"]
    if parent_id != current_id and isinstance(current_id, np.integer):
        recursive_get_parents(
            df_tree=df_tree,
            parent_id=int(current_id),
            tax_ids=tax_ids,
        )
    return tax_ids


class TurtleCreator:
    def __init__(
        self,
        engine: Engine | None = None,
        export_to_folder: str | None = None,
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
        if export_to_folder:
            ttls_folder = os.path.join(export_to_folder, "ttls")
            self.__ttls_folder = ttls_folder
        else:
            self.__ttls_folder = EXPORT_FOLDER
        if not os.path.exists(self.__ttls_folder):
            os.makedirs(self.__ttls_folder)

        if data_folder:
            if os.path.exists(data_folder):
                taxonomy_file_name = os.path.basename(urlparse(TAXONOMY_URL).path)
                if taxonomy_file_name not in os.listdir(data_folder):
                    raise Exception(
                        f"Make sure {taxonomy_file_name} is in {data_folder}"
                    )
                self.__data_folder = data_folder
            else:
                raise FileExistsError(f"Data folder {data_folder} not exists")
        else:
            self.__data_folder = DATA_FOLDER

        self.__engine = DbManager(engine).engine

    def create_all_ttls(self) -> str:
        """Create all RDF turtle, zip all files and returns the path to the zipped file.

        Returns:
            str: path to zip file
        """
        logging.info("Start creating turtle files.")
        self.create_enzyme_nodes()
        self.create_reactions()
        self.create_substrate_product_reaction()
        self.create_nsp_reaction()
        self.create_compound()
        self.create_compound_reaction()
        self.create_substrate_product_reaction_compound()
        self.create_natural_substrate_product_reaction_compound()
        self.create_taxonomy()
        self.create_standard_ttls()
        path_to_zip_file: str = self.create_zip_from_all_ttls()
        logging.info(f"Turtle files zipped in {path_to_zip_file} .")
        return path_to_zip_file

    def create_standard_ttl(
        self,
        table: str,
        node_label: str,
        file_name_suffix: str,
        namespace: Namespace,
        rel_name_1: str,
        rel_name_2: str | None = None,
        value_prop_name: str | None = None,
    ):
        """Create RDF turtle from MySQL table and save as file.

        Args:
            table (str): MySQL table name
            node_label (str): RDF node label
            file_name_suffix (str): _description_
            namespace (Namespace): _description_
            rel_name_1 (str): _description_
            rel_name_2 (str | None, optional): _description_. Defaults to None.
            value_prop_name (str | None, optional): _description_. Defaults to None.
        """
        logging.info(f"Create RDF turtle file for {table}")
        graph: Graph = get_empty_graph()

        sql_value_columns = ""
        value_prop_name_max = ""
        if value_prop_name is not None:
            value_prop_name_max = value_prop_name + "_max"
            sql_value_columns = f"x.{value_prop_name},x.{value_prop_name_max},"

        with_compound_join = ""
        extra_column = ""
        if rel_name_2 is None:
            extra_column = f"x.{table},"
        else:
            with_compound_join = (
                "brenda_compound c on (c.id=x.brenda_compound_id) inner join"
            )
            extra_column = "c.ligand_identifier,"

        sql = f"""Select 
            x.id,
            x.comment,
            {sql_value_columns}
            rb.ec_number,
            {extra_column}
            rb.taxid 
        from 
            brenda_{table} x inner join 
            {with_compound_join}
            reference_brenda rb on (x.reference_brenda_id=rb.id)"""

        df: DataFrame = pd.read_sql(sql=sql, con=self.__engine)
        for _, row in df.iterrows():
            ec_node: URIRef = namespaces.ec_ns[str(row.ec_number)]
            n: URIRef = namespace[str(row.id)]
            graph.add(triple=(n, RDF.type, namespaces.node[node_label]))
            graph.add(triple=(n, RDF.type, namespaces.node["DbBRENDA"]))
            graph.add(triple=(ec_node, namespaces.relation[rel_name_1.upper()], n))
            if not pd.isna(row.comment):
                graph.add(
                    triple=(
                        n,
                        namespaces.relation["comment"],
                        Literal(row.comment, datatype=XSD.string),
                    )
                )
            if not pd.isna(row.taxid):
                graph.add(
                    triple=(
                        n,
                        namespaces.relation["HAS_ORGANISM"],
                        namespaces.tax_ns[str(int(row.taxid))],
                    )
                )
            if value_prop_name is not None:
                for column in [value_prop_name, value_prop_name_max]:
                    if not pd.isna(row[column]):
                        graph.add(
                            triple=(
                                n,
                                namespaces.relation[column],
                                Literal(row[column], datatype=XSD.float),
                            )
                        )

            if rel_name_2 is None:
                graph.add(
                    triple=(
                        n,
                        namespaces.relation[table],
                        Literal(row[table], datatype=XSD.string),
                    )
                )
            elif not np.isnan(row.ligand_identifier):
                compound: URIRef = namespaces.compound_ns[
                    str(int(row.ligand_identifier))
                ]
                graph.add((n, namespaces.relation[rel_name_2.upper()], compound))
        ttl_path = os.path.join(self.__ttls_folder, f"brenda_{file_name_suffix}.ttl")
        graph.serialize(ttl_path, format="turtle")
        del graph

    def create_enzyme_nodes(self):
        """Create all enzymes nodes."""
        logging.info("Create RDF enzyme turtle file.")
        sql = (
            "SELECT ec_number, systematic_name, recommended_name  FROM brenda_ec_number"
        )
        df = pd.read_sql(sql, self.__engine)
        df.head(1)

        graph = get_empty_graph()
        for i, row in df.iterrows():
            subject: URIRef = namespaces.ec_ns[str(row.ec_number)]
            graph.add(triple=(subject, RDF.type, namespaces.node["EnzymeClass"]))
            graph.add(triple=(subject, RDF.type, namespaces.node["DbBRENDA"]))

            for column in ["systematic_name", "recommended_name", "ec_number"]:
                if not pd.isna(row[column]):
                    graph.add(
                        triple=(
                            subject,
                            namespaces.relation[column],
                            Literal(lexical_or_value=row[column], datatype=XSD.string),
                        )
                    )
        del df

        ttl_path = os.path.join(self.__ttls_folder, "brenda_enzyme_class.ttl")
        graph.serialize(ttl_path, format="turtle")
        del graph

    def create_reactions(self):
        """Create reactions."""
        logging.info("Create RDF reaction turtle file.")
        sql = "SELECT id, reaction, ec_number FROM brenda_reaction"
        df = pd.read_sql(sql=sql, con=self.__engine)

        graph = get_empty_graph()
        for i, row in df.iterrows():
            subject: URIRef = namespaces.reaction_ns[str(row.id)]
            graph.add(triple=(subject, RDF.type, namespaces.node["ReactionEC"]))
            graph.add(triple=(subject, RDF.type, namespaces.node["DbBRENDA"]))
            enzyme_class: URIRef = namespaces.ec_ns[str(row.ec_number)]
            graph.add((enzyme_class, namespaces.relation["HAS_REACTION_EC"], subject))
            graph.add(
                triple=(
                    subject,
                    namespaces.relation["reaction"],
                    Literal(lexical_or_value=row.reaction, datatype=XSD.string),
                )
            )
        del df

        ttl_path = os.path.join(self.__ttls_folder, "brenda_reaction_ec.ttl")
        graph.serialize(ttl_path, format="turtle")
        del graph

    def create_substrate_product_reaction(self):
        logging.info("Create RDF substrate and reaction turtle file.")
        """Create Substrate/Product reaction."""
        sql = """
            SELECT
                n.id,
                r.ec_number, 
                r.taxid, 
                n.reaction, 
                n.reversibility, 
                n.comment 
            FROM 
                brenda_substrate_product_reaction n INNER JOIN 
                reference_brenda r ON (r.id=n.reference_brenda_id) 
            """
        df = pd.read_sql(sql=sql, con=self.__engine)

        graph = get_empty_graph()
        for i, row in df.iterrows():
            sp_reac_node: URIRef = namespaces.sp_reaction_ns[str(row.id)]
            graph.add(triple=(sp_reac_node, RDF.type, namespaces.node["ReactionSP"]))
            graph.add(triple=(sp_reac_node, RDF.type, namespaces.node["DbBRENDA"]))
            enzyme_class: URIRef = namespaces.ec_ns[str(row.ec_number)]
            graph.add(
                (enzyme_class, namespaces.relation["HAS_REACTION_SP"], sp_reac_node)
            )
            for col in ["comment", "reversibility", "reaction"]:
                if not pd.isna(row[col]):
                    graph.add(
                        triple=(
                            sp_reac_node,
                            namespaces.relation[col],
                            Literal(row[col], datatype=XSD.string),
                        )
                    )

            if not pd.isna(row.taxid):
                graph.add(
                    triple=(
                        sp_reac_node,
                        namespaces.relation["HAS_ORGANISM"],
                        namespaces.tax_ns[str(int(row.taxid))],
                    )
                )
        del df

        ttl_path = os.path.join(self.__ttls_folder, "brenda_reaction_sp.ttl")
        graph.serialize(ttl_path, format="turtle")
        del graph

    def create_nsp_reaction(self):
        logging.info("Create RDF Natural substrate and product reaction turtle file.")
        sql = """
            SELECT
                n.id,
                r.ec_number, 
                r.taxid, 
                n.reaction, 
                n.reversibility, 
                n.comment 
            FROM 
                brenda_natural_substrate_product_reaction n INNER JOIN 
                reference_brenda r ON (r.id=n.reference_brenda_id) 
            """
        df = pd.read_sql(sql=sql, con=self.__engine)

        graph = get_empty_graph()
        for i, row in df.iterrows():
            nsp_reac_node: URIRef = namespaces.nsp_reaction_ns[str(row.id)]
            graph.add(triple=(nsp_reac_node, RDF.type, namespaces.node["ReactionNSP"]))
            graph.add(triple=(nsp_reac_node, RDF.type, namespaces.node["DbBRENDA"]))
            enzyme_class: URIRef = namespaces.ec_ns[str(row.ec_number)]
            graph.add(
                (enzyme_class, namespaces.relation["HAS_REACTION_NSP"], nsp_reac_node)
            )
            for col in ["comment", "reversibility", "reaction"]:
                if not pd.isna(row[col]):
                    graph.add(
                        triple=(
                            nsp_reac_node,
                            namespaces.relation[col],
                            Literal(row[col], datatype=XSD.string),
                        )
                    )

            if not pd.isna(row.taxid):
                graph.add(
                    triple=(
                        nsp_reac_node,
                        namespaces.relation["HAS_ORGANISM"],
                        namespaces.tax_ns[str(int(row.taxid))],
                    )
                )
        del df

        ttl_path = os.path.join(self.__ttls_folder, "brenda_reaction_nsp.ttl")
        graph.serialize(ttl_path, format="turtle")
        del graph

    def create_compound(self):
        logging.info("Create RDF compound turtle file.")
        sql = """SELECT
            compound AS name,
            first_ligand_identifier,
            ligand_identifier,
            chebi_identifier as chebi_id,
            inchi_key
        FROM 
            brenda_compound
        WHERE
            ligand_identifier IS NOT NULL"""
        df: DataFrame = pd.read_sql(sql=sql, con=self.__engine)

        graph: Graph = get_empty_graph()
        for i, row in df.iterrows():
            compound: URIRef = namespaces.compound_ns[str(int(row.ligand_identifier))]
            graph.add((compound, RDF.type, namespaces.node["Compound"]))
            graph.add((compound, RDF.type, namespaces.node["DbBRENDA"]))
            graph.add(
                triple=(
                    compound,
                    namespaces.relation["name"],
                    Literal(row["name"], datatype=XSD.string),
                )
            )
            if not pd.isna(row.ligand_identifier):
                graph.add(
                    (
                        compound,
                        namespaces.relation["ligand_id"],
                        Literal(row.ligand_identifier, datatype=XSD.integer),
                    )
                )

            if not pd.isna(row.chebi_id):
                graph.add(
                    triple=(
                        compound,
                        namespaces.relation["SAME_AS"],
                        namespaces.chebi_ns[str(int(row.chebi_id))],
                    )
                )

            if not pd.isna(row.inchi_key):
                graph.add(
                    triple=(
                        compound,
                        namespaces.relation["HAS_INCHI_KEY"],
                        namespaces.chebi_ns[row.inchi_key],
                    )
                )
        del df

        ttl_path = os.path.join(self.__ttls_folder, "brenda_compound.ttl")
        graph.serialize(ttl_path, format="turtle")
        del graph

    def create_compound_reaction(self):
        """Create RDF compound in reaction turtle file."""
        logging.info("Create RDF compound in reaction turtle file.")
        sql = """SELECT
            r.brenda_reaction_id,
            r.compound_type,
            c.ligand_identifier
        FROM 
            brenda_compound c inner join 
            brenda_reaction_compound r on (r.brenda_compound_id=c.id)
        WHERE c.ligand_identifier IS NOT NULL"""
        df: DataFrame = pd.read_sql(sql=sql, con=self.__engine)

        graph: Graph = get_empty_graph()
        for i, row in df.iterrows():
            reaction_node: URIRef = namespaces.reaction_ns[
                str(int(row.brenda_reaction_id))
            ]
            compound: URIRef = namespaces.compound_ns[str(int(row.ligand_identifier))]
            graph.add(
                triple=(
                    reaction_node,
                    namespaces.relation[f"HAS_{row.compound_type.upper()}"],
                    compound,
                )
            )
        del df

        ttl_path = os.path.join(self.__ttls_folder, "brenda_reaction_compound.ttl")
        graph.serialize(ttl_path, format="turtle")
        del graph

    def create_substrate_product_reaction_compound(self):
        """Create RDF compound in substrate and product reaction turtle file."""
        logging.info(
            "Create RDF compound in substrate and product reaction turtle file."
        )
        sql = """
            SELECT
                r.brenda_substrate_product_reaction_id as reaction_id,
                r.compound_type,
                c.ligand_identifier
            FROM 
                brenda_compound c inner join 
                brenda_substrate_product_reaction_compound r on (r.brenda_compound_id=c.id)
            WHERE c.ligand_identifier IS NOT NULL"""
        df: DataFrame = pd.read_sql(sql=sql, con=self.__engine)

        graph: Graph = get_empty_graph()
        for i, row in df.iterrows():
            sp_reaction_node: URIRef = namespaces.sp_reaction_ns[
                str(int(row.reaction_id))
            ]
            compound: URIRef = namespaces.compound_ns[str(int(row.ligand_identifier))]
            graph.add(
                triple=(
                    sp_reaction_node,
                    namespaces.relation[f"HAS_{row.compound_type.upper()}"],
                    compound,
                )
            )
        del df

        ttl_path = os.path.join(self.__ttls_folder, "brenda_reaction_sp_compound.ttl")
        graph.serialize(ttl_path, format="turtle")
        del graph

    def create_natural_substrate_product_reaction_compound(self):
        """Create RDF compound in natural substrate and product reaction turtle file."""
        logging.info(
            "Create RDF compound in natural substrate and product reaction turtle file."
        )
        sql = """
            SELECT
                r.brenda_natural_substrate_product_reaction_id as reaction_id,
                r.compound_type,
                c.ligand_identifier
            FROM 
                brenda_compound c inner join 
                brenda_natural_substrate_product_reaction_compound r on (r.brenda_compound_id=c.id)
            WHERE c.ligand_identifier IS NOT NULL"""
        df: DataFrame = pd.read_sql(sql=sql, con=self.__engine)

        graph: Graph = get_empty_graph()
        for i, row in df.iterrows():
            nsp_reaction_node: URIRef = namespaces.nsp_reaction_ns[
                str(int(row.reaction_id))
            ]
            compound: URIRef = namespaces.compound_ns[str(int(row.ligand_identifier))]
            graph.add(
                triple=(
                    nsp_reaction_node,
                    namespaces.relation[f"HAS_{row.compound_type.upper()}"],
                    compound,
                )
            )
        del df

        ttl_path = os.path.join(self.__ttls_folder, "brenda_reaction_nsp_compound.ttl")
        graph.serialize(ttl_path, format="turtle")
        del graph

    def create_taxonomy(self):
        """Create RDF taxonomy turtle file."""
        logging.info("Create RDF taxonomy turtle file.")

        # download NCBI taxonomy if needed
        file_name = os.path.basename(urlparse(TAXONOMY_URL).path)
        taxdmp_path = os.path.join(self.__data_folder, file_name)

        if not os.path.exists(taxdmp_path):
            urlretrieve(TAXONOMY_URL, taxdmp_path)

        archive = zipfile.ZipFile(taxdmp_path, "r")

        # load nodes in Dataframe
        nodes = archive.read("nodes.dmp")
        df_tree = pd.read_csv(
            io.StringIO(nodes.decode("utf-8")),
            usecols=[0, 1],
            sep=r"\t\|\t",
            engine="python",
            names=["tax_id", "parent_tax_id"],
            index_col="tax_id",
        )

        # load names in Dataframe
        names_column_names = ["tax_id", "name_txt", "unique_name", "name_class"]
        names = archive.read("names.dmp")
        df_tax_names: DataFrame = pd.read_csv(
            io.StringIO(names.decode("utf-8")),
            sep=r"\t\|\t",
            engine="python",
            names=names_column_names,
            index_col="tax_id",
        )
        df_tax_names.name_class = df_tax_names.name_class.str.replace("\t|", "")
        df_names: DataFrame = df_tax_names[
            df_tax_names.name_class == "scientific name"
        ][["name_txt"]]

        df_taxid: DataFrame = pd.read_sql(
            "Select distinct taxid from reference_brenda", self.__engine
        )
        brenda_taxids: list[int] = df_taxid.dropna().taxid.astype(int).to_list()
        del df_taxid
        needed_taxids = set()

        for brenda_taxid in brenda_taxids:
            needed_taxids.update(
                recursive_get_parents(df_tree=df_tree, parent_id=brenda_taxid)
            )

        graph: Graph = get_empty_graph()
        for tax_id in needed_taxids:
            taxonomy_node: URIRef = namespaces.tax_ns[str(tax_id)]
            graph.add(triple=(taxonomy_node, RDF.type, namespaces.node["Organism"]))
            graph.add(
                triple=(taxonomy_node, RDF.type, namespaces.node["_NCBI_Taxonomy"])
            )
            name = df_names.loc[tax_id, "name_txt"]
            graph.add(
                triple=(
                    taxonomy_node,
                    namespaces.relation["name"],
                    Literal(name, datatype=XSD.string),
                )
            )
            graph.add(
                triple=(
                    taxonomy_node,
                    namespaces.relation["taxid"],
                    Literal(tax_id, datatype=XSD.integer),
                )
            )
            parent_tax_id = df_tree.loc[tax_id, "parent_tax_id"]
            if tax_id != parent_tax_id:
                parent_taxonomy_node: URIRef = namespaces.tax_ns[str(parent_tax_id)]
                graph.add(
                    triple=(
                        taxonomy_node,
                        namespaces.relation["HAS_PARENT"],
                        parent_taxonomy_node,
                    )
                )

        ttl_path: str = os.path.join(self.__ttls_folder, "brenda_organism.ttl")
        graph.serialize(destination=ttl_path, format="turtle")
        del graph

    def create_standard_ttls(self):
        """Create RDF turtle files for tables in standard format."""

        self.create_standard_ttl(
            table="ic50_value",
            node_label="IC50Value",
            rel_name_1="has_ic50_value",
            rel_name_2="has_ic50_value_compound",
            file_name_suffix="ic50_value",
            namespace=namespaces.ic50_ns,
            value_prop_name="ic50_value",
        )
        self.create_standard_ttl(
            table="kcat_km_value",
            node_label="KcatKmValue",
            rel_name_1="has_kcat_km_value",
            rel_name_2="has_kcat_km_value_compound",
            file_name_suffix="kcat_km_value",
            namespace=namespaces.kcat_km_ns,
            value_prop_name="kcat_km_value",
        )

        self.create_standard_ttl(
            table="ki_value",
            node_label="KiValue",
            rel_name_1="has_ki_value",
            rel_name_2="has_ki_value_compound",
            file_name_suffix="ki_value",
            namespace=namespaces.ki_ns,
            value_prop_name="ki_value",
        )
        self.create_standard_ttl(
            table="km_value",
            node_label="KmValue",
            rel_name_1="has_km_value",
            rel_name_2="has_km_value_compound",
            file_name_suffix="km_value",
            namespace=namespaces.km_ns,
            value_prop_name="km_value",
        )

        self.create_standard_ttl(
            table="localization",
            node_label="Localization",
            rel_name_1="has_localization",
            file_name_suffix="localization",
            namespace=namespaces.location_ns,
        )

        self.create_standard_ttl(
            table="general_information",
            node_label="Information",
            rel_name_1="has_information",
            file_name_suffix="general_information",
            namespace=namespaces.information_ns,
        )
        self.create_standard_ttl(
            table="activating_compound",
            node_label="Activation",
            rel_name_1="has_activation",
            rel_name_2="has_activating_compound",
            file_name_suffix="activating_compound",
            namespace=namespaces.activation_ns,
        )

        self.create_standard_ttl(
            table="metal_ion",
            node_label="MetalIon",
            rel_name_1="has_metal_ion",
            rel_name_2="has_metal_ion_compound",
            file_name_suffix="metals_ion",
            namespace=namespaces.metal_ion_ns,
        )

        self.create_standard_ttl(
            table="cofactor",
            node_label="CofactorInteraction",
            rel_name_1="has_cofactor_interaction",
            rel_name_2="has_cofactor",
            file_name_suffix="cofactor",
            namespace=namespaces.cofactor_ns,
        )

        self.create_standard_ttl(
            table="inhibitor",
            node_label="Inhibition",
            rel_name_1="has_inhibition",
            rel_name_2="has_inhibitor",
            file_name_suffix="inhibitor",
            namespace=namespaces.inhibition_ns,
        )

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
