# main.py
from typing import Annotated, List

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.orm import Session

from ipni.api import schemas
from ipni.api.tags import Tag
from ipni.constants import DB_DEFAULT_CONNECTION_STR
from ipni.db import models
from ipni.db.manager import DbManager

# 1) Configure Database
dbm = DbManager()
dbm.import_data(only_if_db_empty=True)


def get_db():
    session = dbm.Session()
    try:
        yield session
    finally:
        session.close()


# 3) Create FastAPI App
app = FastAPI(
    title="IPNI Data API",
    description="RestfulAPI for IPNI-based data. <br><br>Reference: https://www.ipni.org/",
    version="0.1.0",
)


###############################################################################
# Root
###############################################################################
@app.get("/", tags=["General"])
def root() -> dict:
    return {"message": "Welcome to the IPNI Data API!"}


###############################################################################
# Name
###############################################################################
@app.get("/name/{name_id}", response_model=schemas.Name, tags=[Tag.NAME])
def get_name(name_id: str, session: Session = Depends(get_db)) -> models.Name | None:
    obj = session.get(models.Name, name_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Name with id={name_id} not found.",
        )
    return obj


@app.get("/names/", response_model=List[schemas.Name], tags=[Tag.NAME])
def list_names(
    offset: int = 0,
    limit: Annotated[int, Query(le=10)] = 3,
    session: Session = Depends(get_db),
) -> List[models.Name]:
    return session.query(models.Name).offset(offset).limit(limit).all()


@app.get("/names/search/", response_model=List[schemas.Name], tags=[Tag.NAME])
def search_names(
    offset: int = 0,
    limit: Annotated[int, Query(le=10)] = 3,
    session: Session = Depends(get_db),
) -> List[models.Name]:
    return session.query(models.Name).offset(offset).limit(limit).all()


###############################################################################
# Reference
###############################################################################
@app.get("/reference/{ref_id}", response_model=schemas.Reference, tags=[Tag.REFERENCE])
def get_reference(
    ref_id: str, session: Session = Depends(get_db)
) -> models.Reference | None:
    obj = session.get(models.Reference, ref_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference with id={id} not found.",
        )
    return obj


@app.get("/references/", response_model=List[schemas.Reference], tags=[Tag.REFERENCE])
def list_references(
    offset: int = 0,
    limit: Annotated[int, Query(le=10)] = 3,
    session: Session = Depends(get_db),
) -> List[models.Reference]:
    return session.query(models.Reference).offset(offset).limit(limit).all()


# ###############################################################################
# # Taxon
# ###############################################################################
@app.get("/taxon/{id}", response_model=schemas.Taxon, tags=[Tag.TAXON])
def get_taxon(id: str, session: Session = Depends(get_db)) -> models.Taxon | None:
    obj = session.get(models.Taxon, id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Taxon with id={id} not found.",
        )
    return obj


@app.get("/taxons/", response_model=List[schemas.Taxon], tags=[Tag.TAXON])
def list_taxons(
    offset: int = 0,
    limit: Annotated[int, Query(le=10)] = 3,
    session: Session = Depends(get_db),
) -> List[models.Taxon]:
    return session.query(models.Taxon).offset(offset).limit(limit).all()


# ###############################################################################
# # NameRelation
# ###############################################################################
@app.get(
    "/name_relation/{id}",
    response_model=schemas.NameRelation,
    tags=[Tag.NAME_RELATION],
)
def get_name_relation(
    id: str, session: Session = Depends(get_db)
) -> models.NameRelation | None:
    obj = session.get(models.NameRelation, id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Name Relation with id={id} not found.",
        )
    return obj


@app.get(
    "/name_relations/",
    response_model=List[schemas.NameRelation],
    tags=[Tag.NAME_RELATION],
)
def list_name_relations(
    offset: int = 0,
    limit: Annotated[int, Query(le=10)] = 3,
    session: Session = Depends(get_db),
) -> List[models.NameRelation]:
    return session.query(models.NameRelation).offset(offset).limit(limit).all()


# ###############################################################################
# # TypeMaterial
# ###############################################################################
@app.get(
    "/type_material/{id}",
    response_model=schemas.TypeMaterial,
    tags=[Tag.TYPE_MATERIAL],
)
def get_type_material(
    id: int, session: Session = Depends(get_db)
) -> models.TypeMaterial | None:
    obj = session.get(models.TypeMaterial, id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Type material with id={id} not found.",
        )
    return obj


@app.get(
    "/type_materials/",
    response_model=List[schemas.TypeMaterial],
    tags=[Tag.TYPE_MATERIAL],
)
def list_type_materials(
    offset: int = 0,
    limit: Annotated[int, Query(le=10)] = 3,
    session: Session = Depends(get_db),
) -> List[models.TypeMaterial]:
    return session.query(models.TypeMaterial).offset(offset).limit(limit).all()
