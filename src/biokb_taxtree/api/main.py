import logging
import os
import re
import secrets
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Annotated, AsyncGenerator, Generator

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import Engine, and_, create_engine, func, literal, select, union_all
from sqlalchemy.orm import Session, sessionmaker

from biokb_taxtree.api import schemas
from biokb_taxtree.api.query_tools import SASearchResults, build_dynamic_query
from biokb_taxtree.api.tags import Tag
from biokb_taxtree.constants import (
    DB_DEFAULT_CONNECTION_STR,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USER,
    ZIPPED_TTLS_PATH,
)
from biokb_taxtree.db import manager, models
from biokb_taxtree.db.manager import DbManager
from biokb_taxtree.rdf.neo4j_importer import Neo4jImporter
from biokb_taxtree.rdf.turtle import TurtleCreator

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("api")

USERNAME = os.environ.get("TAXTREE_API_USERNAME", "admin")
PASSWORD = os.environ.get("TAXTREE_API_PASSWORD", "admin")
API_ROOT_PATH = os.environ.get("API_TAXTREE_ROOT_PATH", "").rstrip("/")


def get_engine() -> Engine:
    conn_url = os.environ.get("CONNECTION_STR", DB_DEFAULT_CONNECTION_STR)
    engine: Engine = create_engine(conn_url)
    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def get_session(request: Request) -> Generator[Session, None, None]:
    session_factory: sessionmaker[Session] = request.app.state.session_factory
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def verify_credentials(credentials: HTTPBasicCredentials = Depends(HTTPBasic())):
    is_correct_username = secrets.compare_digest(credentials.username, USERNAME)
    is_correct_password = secrets.compare_digest(credentials.password, PASSWORD)
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize app resources on startup and cleanup on shutdown."""
    engine = get_engine()
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    manager.DbManager(engine)
    yield
    app.state.engine.dispose()


# 3) Create FastAPI App
app = FastAPI(
    title="NCBI TaxTree Data API",
    description="RestfulAPI for NCBI TaxTree-based data. <br><br>Reference: https://www.ncbi.nlm.nih.gov/Taxonomy/",
    version="0.1.0",
    lifespan=lifespan,
    root_path=API_ROOT_PATH,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@app.middleware("http")
async def strip_root_prefix_middleware(request, call_next):
    """Allow both prefixed and non-prefixed paths behind different proxy setups."""
    if API_ROOT_PATH:
        path = request.scope.get("path", "")
        if path == API_ROOT_PATH or path.startswith(f"{API_ROOT_PATH}/"):
            stripped_path = path[len(API_ROOT_PATH) :] or "/"
            request.scope["path"] = stripped_path
    return await call_next(request)


def run_api(host: str = "0.0.0.0", port: int = 8000) -> None:
    uvicorn.run(
        app="biokb_taxtree.api.main:app",
        host=host,
        port=port,
        log_level="warning",
    )


###############################################################################
# Manage
###############################################################################
@app.post(
    path="/import_data/",
    response_model=dict[str, int],
    tags=[Tag.DB_MANAGE],
)
async def import_data(
    credentials: HTTPBasicCredentials = Depends(verify_credentials),
    force_download: bool = Query(
        False,
        description=(
            "Whether to re-download data files even if they already exist,"
            " ensuring the newest version."
        ),
    ),
    delete_files: bool = Query(
        False,
        description=(
            "Whether to delete the downloaded files"
            " after importing them into the database."
        ),
    ),
) -> dict[str, int]:
    """Download data (if not exists) and load in database.

    Can take up to 15 minutes to complete.
    """
    try:
        dbm = DbManager()
        result = dbm.import_data(
            force_download=force_download, delete_files=delete_files
        )
    except Exception as e:
        logger.error(f"Error importing data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error importing data. {e}",
        ) from e
    return result


@app.get("/export_ttls/", tags=[Tag.DB_MANAGE])
async def get_report(
    credentials: HTTPBasicCredentials = Depends(verify_credentials),
    force_create: bool = Query(
        False,
        description="Whether to re-generate the TTL files even if they already exist.",
    ),
    list_of_tax_ids: str = Query(
        default="2157,2,2759,10239",
        description=(
            "Comma-separated list of tax IDs to generate TTL files for. "
            "If not provided, default tax IDs are used "
            "(2157=Archaea, 2=Bacteria, 2759=Eukaryota, 10239=Viruses)"
        ),
    ),
) -> FileResponse:

    file_path = ZIPPED_TTLS_PATH
    if not os.path.exists(file_path) or force_create:
        try:
            tax_ids: list[int] = [
                int(x) for x in re.findall(r"\d+", list_of_tax_ids) if x.isdigit()
            ]
            TurtleCreator().create_ttls(start_from_tax_ids=tax_ids)
        except Exception as e:
            logger.error(f"Error generating TTL files: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error generating TTL files. Data already imported?",
            ) from e
    return FileResponse(
        path=file_path, filename="taxtree_ttls.zip", media_type="application/zip"
    )


@app.get("/import_neo4j/", tags=[Tag.DB_MANAGE])
async def import_neo4j(
    credentials: HTTPBasicCredentials = Depends(verify_credentials),
    uri: str | None = Query(
        os.environ.get("NEO4J_URI", NEO4J_URI),
        description="The Neo4j URI. If not provided, "
        "the default from environment variable is used.",
    ),
    user: str | None = Query(
        os.environ.get("NEO4J_USER", NEO4J_USER),
        description="The Neo4j user. If not provided,"
        " the default from environment variable is used.",
    ),
    password: str | None = Query(
        NEO4J_PASSWORD,
        description="The Neo4j password. If not provided,"
        " the default from environment variable is used.",
    ),
) -> dict[str, str]:
    """Import RDF turtle files in Neo4j."""
    try:
        if not os.path.exists(ZIPPED_TTLS_PATH):
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail=(
                    "Zipped TTL files not found. Please "
                    "generate them first using /export_ttls/ endpoint."
                ),
            )
        importer = Neo4jImporter(neo4j_uri=uri, neo4j_user=user, neo4j_pwd=password)
        importer.import_ttls()
    except Exception as e:
        logger.error(f"Error importing data into Neo4j: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error importing data into Neo4j: {e}",
        ) from e
    return {"status": "Neo4j import completed successfully."}


###############################################################################
# Name
###############################################################################


@app.get("/names/search/", response_model=schemas.NameSearchResults, tags=[Tag.NAME])
async def search_names(
    search: Annotated[schemas.NameSearch, Query()],
    session: Session = Depends(get_session),
) -> SASearchResults | dict[str, str]:
    return build_dynamic_query(
        search_obj=search,
        model_cls=models.Name,
        db=session,
    )


@app.get("/names/classes/", response_model=list[str], tags=[Tag.NAME])
async def get_name_classes() -> list[str]:
    """Get all available name classes."""
    return [e.value for e in models.NameClassEnum]


@app.get("/names/suggestions/", response_model=schemas.NameSuggestions, tags=[Tag.NAME])
async def search_names_suggestions(
    search: schemas.NameSuggestionSearch = Depends(),
    session: Session = Depends(get_session),
) -> schemas.NameSuggestions:
    """Search for name suggestions based on partial name_txt match."""
    stmt = (
        select(
            models.Name.name_txt,
            models.Name.name_class,
            models.Node.tax_id,
            models.Node.rank,
        )
        .select_from(models.Name)
        .join(models.Node)
        .where(models.Name.name_txt.ilike(f"{search.name_txt}%"))
    )
    if search.name_class:
        stmt = stmt.where(models.Name.name_class == search.name_class)
    stmt = stmt.limit(10)
    rows = session.execute(stmt).all()
    return schemas.NameSuggestions(
        results=[
            schemas.NameSuggestion(
                name_txt=row.name_txt,
                name_class=row.name_class,
                tax_id=row.tax_id,
                rank=row.rank,
            )
            for row in rows
        ]
    )


###############################################################################
# Nodes
###############################################################################


@app.get("/node/search/", response_model=schemas.NodeSearchResults, tags=[Tag.NODE])
async def search_nodes(
    search: schemas.NodeSearch = Depends(),
    session: Session = Depends(get_session),
) -> SASearchResults | dict[str, str]:
    """
    Search nodes.
    """
    return build_dynamic_query(
        search_obj=search,
        model_cls=models.Node,
        db=session,
    )


@app.get(
    "/node/search/siblings/{tax_id}",
    response_model=schemas.NodeSiblingsSearchResults,
    tags=[Tag.NODE],
)
async def search_siblings_nodes(
    tax_id: int,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 10,
    session: Session = Depends(get_session),
):
    """Search all nodes that have the same parent as the node with the given tax_id.

    Note: This includes the node with the given tax_id itself."""
    subquery = (
        select(models.Node.parent_tax_id)
        .where(models.Node.tax_id == tax_id)
        .limit(1)
        .scalar_subquery()
    )

    # Main query to get all nodes with that parent_tax_id
    query = (
        session.query(
            models.Node.tax_id,
            models.Node.parent_tax_id,
            models.Name.name_txt.label("scientific_name"),
        )
        .join(models.Name)
        .filter(
            models.Node.parent_tax_id == subquery,
            models.Name.name_class == "scientific name",
        )
    )

    return {
        "count": query.count(),
        "limit": limit,
        "offset": offset,
        "results": query.limit(limit).offset(offset).all(),
    }


@app.get(
    "/node/search/descendent/{tax_id}",
    response_model=schemas.NodeSiblingsSearchResults,
    tags=[Tag.NODE],
)
async def search_descendent_nodes(
    tax_id: int,
    only_leafs: bool = False,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 10,
    session: Session = Depends(get_session),
):
    """Search all nodes that are descendants of the node with the given tax_id.

    Set `only_leafs` to `True` to only return leaf nodes (nodes without children).
    """
    subquery = (
        select(models.Node.tree_id, models.Node.right_tree_id)
        .where(models.Node.tax_id == tax_id)
        .subquery()
    )

    # Aliases for readability
    a = models.Node
    b = subquery.c  # column access in subquery

    # Main query with join condition
    query = (
        select(
            models.Node.tax_id,
            models.Node.parent_tax_id,
            models.Name.name_txt.label("scientific_name"),
        )
        .select_from(a)
        .join(subquery, and_(a.tree_id >= b.tree_id, a.tree_id < b.right_tree_id))
        .join(models.Name, models.Name.tax_id == a.tax_id)
        .where(models.Name.name_class == "scientific name")
    )
    if only_leafs:
        query = query.where(a.is_leaf == True)

    query_count = select(func.count()).select_from(query.subquery())

    return {
        "count": session.execute(query_count).scalar_one(),
        "limit": limit,
        "offset": offset,
        "results": session.execute(query.limit(limit).offset(offset)).all(),
    }


###############################################################################
# Ranked Lineage
###############################################################################


@app.get(
    "/ranked_lineage/search/",
    response_model=schemas.RankedLineageSearchResults,
    tags=[Tag.RANKED_LINEAGE],
)
async def search_ranked_lineage(
    search: schemas.RankedLineageSearch = Depends(),
    session: Session = Depends(get_session),
) -> SASearchResults | dict[str, str]:
    return build_dynamic_query(
        search_obj=search,
        model_cls=models.RankedLineage,
        db=session,
    )


###############################################################################
# Statistics
###############################################################################


@app.post(
    "/ranked_lineage/statistics/",
    response_model=schemas.RankedLineageStatisticsResults,
    tags=[Tag.RANKED_LINEAGE],
)
async def get_ranked_lineage_statistics_by_tax_ids(
    payload: schemas.RankedLineageStatisticsRequest,
    session: Session = Depends(get_session),
):
    """Returns ranked lineage statistics for the given list of tax IDs."""
    tax_ids = payload.tax_ids
    rank_specs = [
        ("domain", models.RankedLineage.domain_id, models.Domain),
        ("kingdom", models.RankedLineage.kingdom_id, models.Kingdom),
        ("phylum", models.RankedLineage.phylum_id, models.Phylum),
        ("class_", models.RankedLineage.class__id, models.Class_),
        ("order", models.RankedLineage.order_id, models.Order),
        ("family", models.RankedLineage.family_id, models.Family),
        ("genus", models.RankedLineage.genus_id, models.Genus),
    ]

    rank_queries = [
        select(
            literal(rank_name).label("rank"),
            rank_model.name.label("name"),
            func.count().label("count"),
        )
        .select_from(models.RankedLineage)
        .join(rank_model, lineage_column == rank_model.id)
        .where(models.RankedLineage.tax_id.in_(tax_ids))
        .group_by(rank_model.id, rank_model.name)
        for rank_name, lineage_column, rank_model in rank_specs
    ]

    stmt = union_all(*rank_queries)

    rows = session.execute(stmt).all()

    results = defaultdict(dict)
    for rank, name, count in rows:
        results[rank][name] = count

    return results
