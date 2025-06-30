# main.py
import logging
import os
import secrets
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Optional, Union, get_args, get_origin

from fastapi import Body, Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from sqlalchemy import and_, create_engine, func, select
from sqlalchemy.orm import Session

# from database import SessionLocal
from sqlalchemy.sql import text

from biokb_taxtree.api import schemas
from biokb_taxtree.api.tags import Tag
from biokb_taxtree.constants import DB_DEFAULT_CONNECTION_STR
from biokb_taxtree.db import models
from biokb_taxtree.db.manager import DbManager

# TODO: Change method to check the user and password
USERNAME = os.environ.get("API_USERNAME", "admin")
PASSWORD = os.environ.get("API_PASSWORD", "admin")


def verify_credentials(credentials: HTTPBasicCredentials = Depends(HTTPBasic())):
    is_correct_username = secrets.compare_digest(credentials.username, USERNAME)
    is_correct_password = secrets.compare_digest(credentials.password, PASSWORD)
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("api")

# 1) Configure Database
SQLALCHEMY_DATABASE_URL = os.getenv("CONNECTION_STR", DB_DEFAULT_CONNECTION_STR)

engine = create_engine(SQLALCHEMY_DATABASE_URL)


def get_db():
    dbm = DbManager(engine=engine)
    session = dbm.Session()
    try:
        yield session
    finally:
        session.close()


# 3) Create FastAPI App
app = FastAPI(
    title="NCBI TaxTree Data API",
    description="RestfulAPI for NCBI TaxTree-based data. <br><br>Reference: https://www.ncbi.nlm.nih.gov/Taxonomy/",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


def build_dynamic_query(
    search_obj: BaseModel,
    model_cls,
    db: Session,
    limit: Optional[int] = None,  # default limit for pagination
    offset: Optional[int] = None,  # default offset for pagination
):
    try:
        return _build_dynamic_query(
            search_obj=search_obj,
            model_cls=model_cls,
            db=db,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error(f"Error in node search: {e}")
        return {"error": str(e)}


def _build_dynamic_query(
    search_obj: BaseModel,
    model_cls,
    db: Session,
    limit: Optional[int] = None,  # default limit for pagination
    offset: Optional[int] = None,  # default offset for pagination
):
    """
    Build and execute a SQLAlchemy 2.0-style SELECT based on the non-None
    attributes of a Pydantic model instance.  The operator is inferred from
    each field's *declared* type, not the runtime value.
    """
    filters = []

    # Only the attributes the client actually supplied (`exclude_none`)
    payload = search_obj.model_dump(exclude_none=True)

    for field_name, value in payload.items():

        # Skip if the SQLAlchemy model has no matching column / hybrid attr
        if not hasattr(model_cls, field_name):
            continue
        column = getattr(model_cls, field_name)

        # ↓ The type you wrote in the Pydantic model definition
        declared_type = search_obj.__pydantic_fields__[field_name].annotation
        # Handle Optional types (e.g., Optional[str] or Union[str, None])
        if get_origin(declared_type) is Union:
            args = [arg for arg in get_args(declared_type) if arg is not type(None)]
            if args:
                declared_type = args[0]
        origin = get_origin(declared_type) or declared_type

        # STRING ......................................................................
        if origin is str:
            logger.info("used string filter")
            filters.append(column.like(value) if ("%" in value) else column == value)

        # NUMBERS .....................................................................
        elif origin in (int, float, Decimal):
            filters.append(column == value)

        # BOOLEANS ....................................................................
        elif origin is bool:
            filters.append(column.is_(value))

        # DATE / DATETIME – supports equality or simple closed range ...................
        elif origin in (date, datetime):
            if isinstance(value, (list, tuple)) and len(value) == 2:
                filters.append(column.between(value[0], value[1]))
            else:
                filters.append(column == value)

        # FALLBACK .....................................................................
        else:
            logger.warning(
                f"Unsupported type for field '{field_name}': {declared_type}. "
                "Using equality operator as fallback."
            )
            filters.append(column == value)

    stmt = select(model_cls).where(*filters)

    count_stmt = select(func.count()).select_from(model_cls).where(*filters)
    total_count = db.execute(count_stmt).scalar()

    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    logger.info(stmt.compile(compile_kwargs={"literal_binds": True}))

    return {
        "count": total_count,
        "limit": limit,
        "offset": offset,
        "results": db.execute(stmt).scalars().all(),
    }


###############################################################################
# Manage
###############################################################################
@app.get("/", tags=["Manage"])
async def check_status() -> dict:
    return {"msg": "Running!"}


@app.get("/import_data/", tags=["Manage"])
async def import_data(
    session: Session = Depends(get_db),
    force: bool = False,
    credentials: HTTPBasicCredentials = Depends(verify_credentials),
):
    return DbManager(engine=engine).import_data(force=force)


###############################################################################
# Name
###############################################################################


@app.get("/names/search/", response_model=schemas.NameSearchResults, tags=[Tag.NAME])
async def search_names(
    search: schemas.NameSearch = Depends(),
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 10,
    session: Session = Depends(get_db),
):
    return build_dynamic_query(
        search_obj=search,
        model_cls=models.Name,
        db=session,
        limit=limit,
        offset=offset,
    )


###############################################################################
# Nodes
###############################################################################


@app.get("/node/search/", response_model=schemas.NodeSearchResults, tags=[Tag.NODE])
async def search_nodes(
    search: schemas.NodeSearch = Depends(),
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 10,
    session: Session = Depends(get_db),
):
    """
    Search nodes.
    """
    return build_dynamic_query(
        search_obj=search,
        model_cls=models.Node,
        db=session,
        limit=limit,
        offset=offset,
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
    session: Session = Depends(get_db),
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
    query = session.query(models.Node).filter(models.Node.parent_tax_id == subquery)

    return {
        "count": query.count(),
        "limit": limit,
        "offset": offset,
        "results": query.limit(limit).offset(offset).all(),
    }


@app.get(
    "/node/search/leafs_of/{tax_id}",
    response_model=schemas.NodeSiblingsSearchResults,
    tags=[Tag.NODE],
)
async def search_leaf_nodes(
    tax_id: int,
    only_leafs: bool = True,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 10,
    session: Session = Depends(get_db),
):
    """Search all leaf nodes that are descendants of the node with the given tax_id."""
    subquery = (
        select(models.Node.tree_id, models.Node.right_tree_id)
        .where(models.Node.tax_id == tax_id)
        .subquery()
    )

    # Aliases for readability
    a = models.Node
    b = subquery.c  # column access in subquery

    # Main query with join condition
    query = session.query(a).join(
        subquery, and_(a.tree_id >= b.tree_id, a.tree_id <= b.right_tree_id)
    )
    if only_leafs:
        query = query.filter(a.is_leaf == True)

    return {
        "count": query.count(),
        "limit": limit,
        "offset": offset,
        "results": query.limit(limit).offset(offset).all(),
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
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 10,
    session: Session = Depends(get_db),
):
    return build_dynamic_query(
        search_obj=search,
        model_cls=models.RankedLineage,
        db=session,
        limit=limit,
        offset=offset,
    )
