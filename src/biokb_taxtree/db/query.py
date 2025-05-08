import logging

from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from biokb_taxtree.db import models
from biokb_taxtree.logger import setup_logging

setup_logging()

logger = logging.getLogger("query")


class DbQuery:

    def __init__(self, engine: Engine) -> None:
        self.Session = sessionmaker(engine)

    def get_node_by_name(self, name: str):
        with self.Session() as session:
            query = session.query(models.Name).filter(models.Name.name_txt.like(name))
            return query.all()
