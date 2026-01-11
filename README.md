![docs/imgs/](https://raw.githubusercontent.com/biokb/biokb_taxtree/refs/heads/main/docs/imgs/biokb_logo_writing.png)
# BioKb-TaxTree

![](https://img.shields.io/pypi/v/biokb-taxtree?style=flat-square)
![](https://img.shields.io/pypi/pyversions/biokb-taxtree?style=flat-square)
![](https://img.shields.io/github/actions/workflow/status/biokb/biokb_taxtree/pypi-publish.yml?style=flat-square)
![](https://img.shields.io/github/license/biokb/biokb_taxtree?style=flat-square)



BioKb-TaxTree (biokb_taxtree) is a python package to import TaxTree data into a relational database and create RDF triples (turtles) from it. The turtles can be imported into a Neo4J graph database. The package is part of the [BioKb family of packages](https://github.com/biokb) to create and connect biological and medical knowledge bases and graphs.

![Components](https://raw.githubusercontent.com/biokb/biokb_taxtree/refs/heads/main/docs/imgs/components.png)

The package provides different options to run it: from command line, as RESTful API server, as Podman/Docker container, or as Podman/Docker networked containers with Neo4J and a relational database.

## Features

biokb_taxtree allows to ...

1. Query TaxTree data with SQLAlchemy or raw SQL
2. Load, query and manage TaxTree data with GUIs for knowledge base and graphs (phpMyAdmin, Neo4J Browser)
3. Query data via a RESTful API (FastAPI) with OpenAPI documentation and interactive Swagger-UI

to provide this ***biokb_taxtree*** ...

- imports [TaxTree](https://www.ebi.ac.uk/taxtree/) data into a relational database 
- creates [RDF](https://www.w3.org/RDF/) triples (turtles) from the relational database
- imports the RDF triples into a [Neo4J](https://neo4j.com) graph database

***Supported databases***: [SQLite](https://sqlite.org/), [MariaDB](https://go.mariadb.com)/[MySQL](https://www.mysql.com/), [PostgreSQL](https://www.postgresql.org/), [Oracle](https://www.oracle.com/database/), [Microsoft SQL Server](https://www.microsoft.com/en-us/sql-server), and any other database [supported by SQLAlchemy](https://docs.sqlalchemy.org/en/20/core/engines.html#supported-databases).


### Options to run BioKb-TaxTree

All biokb packages share the same API and CLI structure. You have different options to run the packages:
1. [from command line](#from-command-line) (simplest way to get started)
2. [as RESTful API server](#as-restful-api-server) (can start directly from command line)
3. [as Podman/Docker container](#as-podmandocker-container) (without import into Neo4J, but export of turtles possible)
4. [as Podman/Docker networked containers](#as-podmandocker-networked-containers) (with all features) and 3 containers: 
   1. high-performance relational databases (PostgreSQL, Oracle, MySQL, ...)
   2. RESTful API (fastAPI) for queries, data import and export
   3. GUI for querying and administration of MySQL over the Web


## Installation

If [uv](https://docs.astral.sh/uv/) is installed:

```bash
uv venv
source .venv/bin/activate
uv pip install biokb_taxtree
```
Otherwise:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install biokb_taxtree
```

## Run BioKb-TaxTree

### From command line

For sure the simplest way is to run all steps:

```bash
biokb_taxtree import-data
biokb_taxtree create-ttls
```
Before importing into Neo4J, make sure Neo4J is running (see below "[How to run Neo4J](#how-to-run-neo4j)").

Then import into Neo4J:
```bash
biokb_taxtree import-neo4j -p neo4j_password
```

http://localhost:7474  (user/password: neo4j/neo4j_password)

For more options see the [CLI options](#cli-options) section below.


### As RESTful API server

***Usage:*** `biokb_taxtree run-api [OPTIONS]`

```bash
biokb_taxtree run-api
```

- ***user***: admin  
- ***password***: admin

| Option | long | Description | default |
|--------|------|-------------|---------|
| -P     | --port | API server port | 8000 |
| -u     | --user     | API username | admin   |
| -p     | --password | API password | admin | 

http://localhost:8000/docs#/

1. [Import data](http://localhost:8000/docs#/Database%20Management/import_data_import_data__post)
2. [Export ttls](http://localhost:8000/docs#/Database%20Management/get_report_export_ttls__get)
3. Run Neo4J (see below "[How to run Neo4J](#how-to-run-neo4j)")
4. [Import Neo4J](http://localhost:8000/docs#/Database%20Management/import_neo4j_import_neo4j__get)

Be patient, each step takes several minutes.


### As Podman/Docker container

For docker just replace `podman` with `docker` in the commands below.

Build & run with Podman:
```bash
git clone https://github.com/biokb/biokb_taxtree.git
cd biokb_taxtree
podman build -t biokb_taxtree_image .
podman run -d --rm --name biokb_taxtree_simple -p 8000:8000 biokb_taxtree_image
```

- Login: admin  
- Password: admin

With environment variable for user and password for more security:
```bash
podman run -d --rm --name biokb_taxtree_simple -p 8000:8000 -e API_PASSWORD=your_secure_password -e API_USER=your_secure_user biokb_taxtree_image
```

http://localhost:8000/docs

On the website:
1. [Import data](http://localhost:8000/docs#/Database%20Management/import_data_import_data__post)
2. [Export ttls](http://localhost:8000/docs#/Database%20Management/get_report_export_ttls__get)

Neo4j import in this context is not possible because Neo4J is not running in the same network as service, but the exported turtles can be imported into any Neo4J instance using the CLI (`biokb_taxtree import-neo4j`).

to stop the container:
```bash
podman stop biokb_taxtree_simple
```
to rerun the container:
```bash
podman start biokb_taxtree_simple
```

### Run as Podman/Docker networked containers

### As Podman/Docker networked containers

If you have docker or podman on your system, the easiest way to run all components (relational database, RESTful API server, phpMyAdmin GUI) is to use networked containers with `podman-compose`/`docker-compose`.

```bash
git clone https://github.com/biokb/biokb_taxtree.git
cd biokb_taxtree
podman-compose -f docker-compose.db_neo.yml --env-file .env_template up -d
podman-compose --env-file .env_template up -d
```
http://localhost:8001/docs

On the website:
1. [Import data](http://localhost:8001/docs#/Database%20Management/import_data_import_data__post)
2. [Export ttls](http://localhost:8001/docs#/Database%20Management/get_report_export_ttls__get)
3. [Import Neo4J](http://localhost:8001/docs#/Database%20Management/import_neo4j_import_neo4j__get)

stop with:
```bash
podman pod stop pod_biokb_db
podman-compose stop
```

rerun with:
```bash
podman pod start pod_biokb_db
podman-compose start
```

***Tip***: Copy the `.env_template` to `.env` and change the default passwords in the `.env` file before starting the containers for better security. If you have done that you need to use `--env-file .env` instead of `--env-file .env_template` in the commands above or just omit the `--env-file` option (because the default is `.env`).

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



## How to run Neo4J

For the options "Run BioKb-TaxTree as ..."
1. [From command line](#from-command-line)
2. [As RESTful API server](#as-restful-api-server)

you need to run Neo4J separately.


If you have not already a Neo4j instance running, the easiest way is to run Neo4J as Podman/ Docker container.


For docker just replace `podman` with `docker` in the commands below.
```bash
podman run -d --rm --name biokb-neo4j -p7474:7474 -p7687:7687 -e NEO4J_AUTH=neo4j/neo4j_password neo4j:latest
# Remove `--rm` if you want to keep the container after stopping it.
```
Neo4J is then available at:
http://localhost:7474  (user/password: neo4j/neo4j_password

Stop Neo4J with:

```bash
podman stop biokb-neo4j
```
if you have not used `--rm` above, you can restart Neo4J with:
```bash
podman start biokb-neo4j
```

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.