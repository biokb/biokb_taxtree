import click
from sqlalchemy import create_engine

from biokb_taxtree.db.manager import DbManager


# we are creating a group
@click.group()
def main():
    pass


# advanced method with many different options
@main.command()
@click.option(
    "-c",
    "--sqlalchemy_connection_string",
    help="SQLAlchemy connection string (dialect+driver://username:password@host:port/database). More info at https://docs.sqlalchemy.org/en/20/core/engines.html",
)
def import_data(
    sqlalchemy_connection_string: str | None = None,
):
    engine = None
    if sqlalchemy_connection_string:
        engine = create_engine(sqlalchemy_connection_string)
    DbManager(engine=engine).import_data()
