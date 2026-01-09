import logging
import sys
from datetime import date, datetime
from decimal import Decimal
from typing import Sequence, Type, TypeAlias, Union, get_args, get_origin

from pydantic import BaseModel
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session, selectinload

from biokb_taxtree.db import models

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
from sqlalchemy.dialects import mysql

SASearchResults: TypeAlias = dict[
    str,
    int | Sequence[models.Base] | None,
]


def build_dynamic_query(
    search_obj: BaseModel,
    model_cls: Type[models.Base],
    db: Session,
) -> SASearchResults | dict[str, str]:
    try:
        return _build_dynamic_query(
            search_obj=search_obj,
            model_cls=model_cls,
            db=db,
        )
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logger.error(f"Error in node search: {e}\n{exc_traceback}")
        return {"error": str(e)}


def _build_dynamic_query(
    search_obj: BaseModel,
    model_cls: Type[models.Base],
    db: Session,
) -> SASearchResults:
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

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_count = db.execute(count_stmt).scalar()

    limit = payload.get("limit")
    if limit is not None:
        stmt = stmt.limit(limit)
    offset = payload.get("offset")
    if offset is not None:
        stmt = stmt.offset(offset)

    logger.info(
        stmt.compile(dialect=mysql.dialect(), compile_kwargs={"literal_binds": True})
    )

    return {
        "count": total_count,
        "limit": limit,
        "offset": offset,
        "results": db.execute(stmt).scalars().all(),
    }
