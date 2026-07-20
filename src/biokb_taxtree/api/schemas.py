from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from biokb_taxtree.db.models import NameClassEnum


class OffsetLimit(BaseModel):
    limit: Annotated[int, Field(le=100)] = 10
    offset: int = 0


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


class NodeSearch(OffsetLimit):
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


class NodeSiblingsSearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    tax_id: int
    parent_tax_id: int
    scientific_name: str


class NodeSiblingsSearchResults(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    count: int
    offset: int
    limit: int
    results: List[NodeSiblingsSearchResult]


# -------------------------------------------------------------------
# Name
# -------------------------------------------------------------------
class NameBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name_txt: str
    unique_name: Optional[str]
    name_class: str
    rank: Optional[str]


class Name(NameBase):
    model_config = ConfigDict(from_attributes=True)
    tax_id: int


class NameSearch(OffsetLimit):
    name_txt: Optional[str] = Field(
        None, description="Textual name for searching", examples=["Homo sapiens"]
    )
    unique_name: Optional[str] = Field(
        None,
        description="Unique identifier name",
        examples=["Homo sapiens <sensu stricto>"],
    )
    name_class: Optional[NameClassEnum] = Field(
        None, description="Classification of the name"
    )
    tax_id: Optional[int] = Field(
        None, description="Taxonomic identifier (NCBI Taxon ID)", examples=[9606]
    )


class NameSearchSimilar(OffsetLimit):
    name_txt: str = Field(
        ..., description="Textual name for searching", examples=["Homo sapiens"]
    )
    name_class: Optional[NameClassEnum] = Field(
        None, description="Classification of the name"
    )


class NameSearchResults(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    count: int
    offset: int
    limit: int
    results: List[Name]


class NameSuggestionSearch(BaseModel):
    name_txt: str = Field(examples=["Achi"], description="Textual name for searching")
    name_class: Optional[NameClassEnum] = Field(
        None,
        description="Classification of the name",
    )
    rank: Optional[str] = Field(
        None, description="Taxonomic rank of the name", examples=["species"]
    )


class NameSuggestion(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name_txt: str
    name_class: str
    rank: str | None
    tax_id: int


class NameSuggestions(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    results: List[NameSuggestion]


# -------------------------------------------------------------------
# RankedLineage
# -------------------------------------------------------------------
class RankedLineageBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
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

    @field_validator(
        "genus",
        "family",
        "order",
        "class_",
        "phylum",
        "kingdom",
        "domain",
        mode="before",
    )
    @classmethod
    def normalize_rank_object_to_name(cls, value: object) -> Optional[str]:
        if value is None or isinstance(value, str):
            return value
        name = getattr(value, "name", None)
        if isinstance(name, str):
            return name
        return str(value)


class RankedLineageSearch(OffsetLimit):
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


class RankedLineageStatisticsResults(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    domain: dict[str, int]
    kingdom: dict[str, int]
    phylum: dict[str, int]
    class_: dict[str, int]
    order: dict[str, int]
    family: dict[str, int]
    genus: dict[str, int]


class RankedLineageStatisticsRequest(BaseModel):
    tax_ids: List[int] = Field(
        ..., description="List of tax IDs to get ranked lineage statistics for"
    )
