# schemas.py
from datetime import date as date_type
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

# -------------------------------------------------------------------
# Node
# -------------------------------------------------------------------


class NodeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    tax_id: int
    parent_tax_id: int
    rank: str
    embl_code: Optional[str]
    division_id: int
    inherited_div_flag: bool
    genetic_code_id: int
    inherited_gc_flag: bool
    mitochondrial_genetic_code_id: int
    inherited_mgc_flag: bool
    genbank_hidden_flag: bool
    hidden_subtree_root_flag: bool
    comments: Optional[str]
    plastid_genetic_code_id: Optional[int]
    inherited_pgc_flag: Optional[bool]
    specified_species: bool
    hydrogenosome_genetic_code_id: Optional[int]
    inherited_hgc_flag: bool


class NodeSearch(BaseModel):
    tax_id: Optional[int] = None
    parent_tax_id: Optional[int] = None
    rank: Optional[str] = None
    embl_code: Optional[str] = None
    division_id: Optional[int] = None
    inherited_div_flag: Optional[bool] = None
    genetic_code_id: Optional[int] = None
    inherited_gc_flag: Optional[bool] = None
    mitochondrial_genetic_code_id: Optional[int] = None
    inherited_mgc_flag: Optional[bool] = None
    genbank_hidden_flag: Optional[bool] = None
    hidden_subtree_root_flag: Optional[bool] = None
    comments: Optional[str] = None
    plastid_genetic_code_id: Optional[int] = None
    inherited_pgc_flag: Optional[bool] = None
    specified_species: Optional[bool] = None
    hydrogenosome_genetic_code_id: Optional[int] = None
    inherited_hgc_flag: Optional[bool] = None


class Node(NodeBase):
    model_config = ConfigDict(from_attributes=True)
    tree_id: int
    tree_parent_id: Optional[int]
    level: int
    right_tree_id: Optional[int]
    is_leaf: bool

    # relationships
    names: list["NameBase"]
    ranked_lineage: Optional["RankedLineageBase"]


class NodeSearchResults(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    count: int
    offset: int
    limit: int
    results: List[Node]


class NodeSiblingsSearchResults(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    count: int
    offset: int
    limit: int
    results: List[Node]


# -------------------------------------------------------------------
# Name
# -------------------------------------------------------------------
class NameBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name_txt: str
    unique_name: Optional[str]
    name_class: str


class Name(NameBase):
    model_config = ConfigDict(from_attributes=True)
    tax_id: int


class NameSearch(BaseModel):
    name_txt: Optional[str] = Field(
        None, examples=["Homo sapiens"], description="Textual name for searching"
    )
    unique_name: Optional[str] = Field(
        None, examples=["Homo_sapiens"], description="Unique identifier name"
    )
    name_class: Optional[str] = Field(
        None,
        examples=["species"],
        description="Classification level (e.g., genus, species)",
    )
    tax_id: Optional[int] = Field(
        None, examples=[9606], description="Taxonomic identifier (NCBI Taxon ID)"
    )


class NameSearchResults(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    count: int
    offset: int
    limit: int
    results: List[Name]


# -------------------------------------------------------------------
# RankedLineage
# -------------------------------------------------------------------
class RankedLineageBase(BaseModel):
    tax_id: int
    tax_name: str
    species: Optional[str]
    genus: Optional[str]
    family: Optional[str]
    order: Optional[str]
    class_: Optional[str]
    phylum: Optional[str]
    kingdom: Optional[str]
    domain: Optional[str]


class RankedLineageSearch(BaseModel):
    tax_id: Optional[int] = None
    tax_name: Optional[str] = None
    species: Optional[str] = None
    genus: Optional[str] = None
    family: Optional[str] = None
    order: Optional[str] = None
    class_: Optional[str] = None
    phylum: Optional[str] = None
    kingdom: Optional[str] = None
    domain: Optional[str] = None


class RankedLineageSearchResults(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    count: int
    offset: int
    limit: int
    results: List[RankedLineageBase]
