from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from biokb_taxtree.constants import PROJECT_NAME


class Base(DeclarativeBase):
    _prefix = PROJECT_NAME + "_"


class Node(Base):
    __tablename__ = Base._prefix + "node"

    tax_id: Mapped[int] = mapped_column(
        primary_key=True, comment="node id in GenBank taxonomy database", unique=True
    )
    parent_tax_id: Mapped[int] = mapped_column(
        comment=" parent node id in GenBank taxonomy database", index=True
    )
    rank: Mapped[str] = mapped_column(
        String(20), comment="rank of this node (superkingdom, kingdom, ...) "
    )
    embl_code: Mapped[Optional[str]] = mapped_column(
        String(2), comment="locus-name prefix; not unique"
    )
    division_id: Mapped[int] = mapped_column(comment="taxonomy database division id")
    inherited_div_flag: Mapped[bool] = mapped_column(
        comment="1 if node inherits division from parent"
    )
    genetic_code_id: Mapped[int] = mapped_column(comment="GenBank genetic code id")
    inherited_gc_flag: Mapped[bool] = mapped_column(
        comment="1 if node inherits genetic code from parent"
    )
    mitochondrial_genetic_code_id: Mapped[int] = mapped_column(
        comment="GenBank genetic code id"
    )
    inherited_mgc_flag: Mapped[bool] = mapped_column(
        comment="1 if node inherits mitochondrial gencode from parent"
    )
    genbank_hidden_flag: Mapped[bool] = mapped_column(
        comment="1 if name is suppressed in GenBank entry lineage"
    )
    hidden_subtree_root_flag: Mapped[bool] = mapped_column(
        comment="1 if this subtree has no sequence data yet"
    )
    comments: Mapped[Optional[str]] = mapped_column(
        Text, comment="free-text comments and citations"
    )
    plastid_genetic_code_id: Mapped[Optional[int]] = mapped_column(
        comment="GenBank genetic code id"
    )
    inherited_pgc_flag: Mapped[Optional[bool]] = mapped_column(
        comment="1 if node inherits plastid gencode from parent"
    )
    specified_species: Mapped[Optional[bool]] = mapped_column(
        comment="1 if species in the node's lineage has formal name"
    )
    hydrogenosome_genetic_code_id: Mapped[Optional[int]] = mapped_column(
        comment="GenBank genetic code id"
    )
    inherited_hgc_flag: Mapped[Optional[bool]] = mapped_column(
        comment="1 if node inherits hydrogenosome gencode from parent"
    )
    tree_id: Mapped[int] = mapped_column(comment="Sorted tree ID", index=True)
    tree_parent_id: Mapped[Optional[int]] = mapped_column(
        comment="Sorted tree ID", index=True
    )
    level: Mapped[int] = mapped_column(comment="Level in the tree")
    right_tree_id: Mapped[Optional[int]] = mapped_column(
        comment="Level in the tree", index=True
    )
    is_leaf: Mapped[bool] = mapped_column(
        comment="Is leaf (has no children)", index=True
    )

    # relationships
    names: Mapped[list["Name"]] = relationship(back_populates="node")
    ranked_lineage: Mapped["RankedLineage"] = relationship(back_populates="node")

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} ("
            f"tax_id={self.tax_id}, "
            f"parent_tax_id={self.parent_tax_id}, "
            f"names= {[x.name_txt for x in self.names]})>"
        )


class Name(Base):
    __tablename__ = Base._prefix + "name"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name_txt: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    unique_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Unique variant of this name if not unique"
    )
    name_class: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="e.g., 'synonym', 'common name'"
    )

    # foreign keys
    tax_id: Mapped[int] = mapped_column(
        ForeignKey(Base._prefix + "node.tax_id"), nullable=False
    )
    # relationships
    node: Mapped[Node] = relationship(back_populates="names")

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} ("
            f"name_txt={self.name_txt}, "
            f"unique_name={self.unique_name}, "
            f"name_class={self.name_class}, "
            f"tax_id={self.tax_id})>"
        )


class RankedLineage(Base):
    __tablename__ = Base._prefix + "ranked_lineage"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    tax_name: Mapped[str] = mapped_column(
        String(255), comment="scientific name of the organism"
    )
    species: Mapped[Optional[str]] = mapped_column(
        String(255),
        comment="name of a species (coincide with organism name for species-level nodes)",
    )
    genus: Mapped[Optional[str]] = mapped_column(String(255), comment="genus name")
    family: Mapped[Optional[str]] = mapped_column(String(255), comment="family name")
    order: Mapped[Optional[str]] = mapped_column(String(255), comment="order name")
    class_: Mapped[Optional[str]] = mapped_column(String(255), comment="class name")
    phylum: Mapped[Optional[str]] = mapped_column(String(255), comment="phylum name")
    kingdom: Mapped[Optional[str]] = mapped_column(String(255), comment="kingdom name")
    domain: Mapped[Optional[str]] = mapped_column(String(255), comment="domain name")

    # foreign keys
    tax_id: Mapped[int] = mapped_column(
        ForeignKey(Base._prefix + "node.tax_id"),
        nullable=False,
        unique=True,
        comment="node id",
    )
    # one to one relationship
    node: Mapped[Node] = relationship(
        back_populates="ranked_lineage", single_parent=True
    )

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} ("
            f"tax_name={self.tax_name}, "
            f"species={self.species}, "
            f"genus={self.genus}, "
            f"family={self.family}, "
            f"order={self.order}, "
            f"class_={self.class_}, "
            f"phylum={self.phylum}, "
            f"kingdom={self.kingdom}, "
            f"domain={self.domain})>"
        )


# TODO: Model to be integrated

# class Division(Base):
#     __tablename__ = "divisions"

#     division_id: Mapped[int] = mapped_column(
#         Integer, primary_key=True, comment="Taxonomy database division ID"
#     )
#     division_cde: Mapped[str] = mapped_column(
#         String(3), nullable=False, comment="GenBank division code"
#     )
#     division_name: Mapped[str] = mapped_column(
#         String(255),
#         nullable=False,
#         comment="Division name (e.g., Bacteria, Plants, etc.)",
#     )
#     comments: Mapped[str | None] = mapped_column(
#         Text, nullable=True, comment="Comments"
#     )


# class GeneticCode(Base):
#     __tablename__ = "genetic_codes"

#     genetic_code_id: Mapped[int] = mapped_column(
#         Integer, primary_key=True, comment="GenBank genetic code ID"
#     )
#     abbreviation: Mapped[str] = mapped_column(
#         String(50), nullable=False, comment="Genetic code name abbreviation"
#     )
#     name: Mapped[str] = mapped_column(
#         String(255), nullable=False, comment="Genetic code name"
#     )
#     code: Mapped[str] = mapped_column(
#         Text, nullable=False, comment="Translation table for this genetic code"
#     )
#     starts: Mapped[str] = mapped_column(
#         Text, nullable=False, comment="Start codons for this genetic code"
#     )


# class DeletedNode(Base):
#     __tablename__ = "deleted_nodes"

#     tax_id: Mapped[int] = mapped_column(
#         Integer, primary_key=True, comment="Deleted node ID"
#     )


# class MergedNode(Base):
#     __tablename__ = "merged_nodes"

#     old_tax_id: Mapped[int] = mapped_column(
#         Integer, primary_key=True, comment="ID of nodes that have been merged"
#     )
#     new_tax_id: Mapped[int] = mapped_column(
#         Integer, nullable=False, comment="ID of node resulting from merging"
#     )


# class Citation(Base):
#     __tablename__ = "citations"

#     cit_id: Mapped[int] = mapped_column(
#         Integer, primary_key=True, comment="Unique ID of citation"
#     )
#     cit_key: Mapped[str] = mapped_column(
#         String(255), nullable=False, comment="Citation key"
#     )
#     pubmed_id: Mapped[int] = mapped_column(
#         Integer, nullable=False, comment="Unique ID in PubMed database"
#     )
#     medline_id: Mapped[int] = mapped_column(
#         Integer, nullable=False, comment="Unique ID in MedLine database"
#     )
#     url: Mapped[str | None] = mapped_column(
#         Text, nullable=True, comment="URL associated with citation"
#     )
#     text: Mapped[str] = mapped_column(
#         Text, nullable=False, comment="Citation text with escaped characters"
#     )
#     taxid_list: Mapped[str] = mapped_column(
#         Text, nullable=False, comment="List of node IDs separated by space"
#     )


# class OrganismImage(Base):
#     __tablename__ = "organism_images"

#     image_id: Mapped[int] = mapped_column(
#         Integer, primary_key=True, comment="Unique ID of image"
#     )
#     image_key: Mapped[str] = mapped_column(
#         String(255), nullable=False, comment="Image key"
#     )
#     url: Mapped[str] = mapped_column(
#         Text, nullable=False, comment="Image URL associated with citation"
#     )
#     license: Mapped[str] = mapped_column(
#         String(255), nullable=False, comment="Image license"
#     )
#     attribution: Mapped[str] = mapped_column(
#         Text, nullable=False, comment="Image attribution"
#     )
#     source: Mapped[str] = mapped_column(
#         Text, nullable=False, comment="Source of the image"
#     )
#     properties: Mapped[str] = mapped_column(
#         Text, nullable=True, comment="Various image properties separated by semicolon"
#     )
#     taxid_list: Mapped[str] = mapped_column(
#         Text, nullable=False, comment="List of node IDs separated by space"
#     )
