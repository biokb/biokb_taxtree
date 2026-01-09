# Command Line Interface (CLI)

BioKb-TaxTree provides a command line interface (CLI) to import TaxTree data into a relational database, create RDF turtles from it, and import the turtles into a Neo4J graph database.

## CLI Options

### Import data into relational database

***Usage:*** `biokb_taxtree import-data [OPTIONS]`

```
biokb_taxtree import-data
```

-> SQLite database in `~/.biokb/biokb.db`. Open with e.g. [DB Browser for SQLite](https://sqlitebrowser.org/)

| Option | long | Description | default |
|--------|------|-------------|---------|
| -f     | --force-download | Force re-download of the source file | False   |
| -k     | --keep-files     | Keep downloaded source files after import | False   |
| -c     | --connection-string TEXT | SQLAlchemy engine URL | sqlite:///taxtree.db | 

If you want to use different relational database (MySQL, PostgreSQL, etc.), provide the connection string with `-c` option. Examples:
- MySQL: `mysql+pymysql://user:password@localhost/biokb`
- PostgreSQL: `postgresql+psycopg2://user:password@localhost/biokb`


For more examples please check [how to create database URLs](https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls)

### Create RDF turtles

***Usage:*** `biokb_taxtree create-ttls [OPTIONS]`

```
biokb_taxtree create-ttls
```
-> RDF turtles will be created in `~/.biokb/taxtree/data/ttls.zip`

| Option | long | Description | default |
|--------|------|-------------|---------|
| -c     | --connection-string TEXT | SQLAlchemy engine URL | sqlite:///taxtree.db |

### Import into Neo4J

Start Neo4J ...
```bash
podman run --rm --name biokb-neo4j-test -p7474:7474 -p7687:7687 -e NEO4J_AUTH=neo4j/neo4j_password neo4j:latest
```
***Note:*** Remove `--rm` if you want to keep the container after stopping it. Replace `podman` with `docker` if you use Docker.

... and import into Neo4J:
```
biokb_taxtree import-neo4j -p neo4j_password
```

| Option               | long                | Description          | default                  |
|----------------------|---------------------|----------------------|--------------------------|
|-i | --uri | Neo4j database URI  | bolt://localhost:7687    |
| -u                    | --user              | Neo4j username        | neo4j                    |
| -p                   | --password          | Neo4j password         | |


http://localhost:7474  (user/password: neo4j/neo4j_password)