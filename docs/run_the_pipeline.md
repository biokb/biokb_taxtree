## Run BioKb-TaxTree

### From command line

For sure the simplest way is to run all steps. After installation (see [Installation](installation.md)) just run:

```bash
biokb_taxtree import-data
biokb_taxtree create-ttls
```
Before importing into Neo4J, make sure Neo4J is running (see below "[How to run Neo4J](how_to_run_neo4j.md)").

Then import into Neo4J:
```bash
biokb_taxtree import-neo4j -p neo4j_password
```

http://localhost:7474  (user/password: neo4j/neo4j_password)

For more options see the [CLI options](cli.md) section below.


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
3. Run Neo4J (see below "[How to run Neo4J](how_to_run_neo4j.md#how-to-run-neo4j)")
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

### As Podman/Docker networked containers

If you have docker or podman on your system, the easiest way to run all components (relational database, RESTful API server, phpMyAdmin GUI) is to use networked containers with `podman-compose`/`docker-compose`.

```bash
git clone https://github.com/biokb/biokb_taxtree.git
cd biokb_taxtree
podman-compose -f docker-compose.db_neo.yml --env-file .env_template up -d
podman-compose --env-file .env_template up -d
```
http://localhost:8000/docs

On the website:
1. [Import data](http://localhost:8000/docs#/Database%20Management/import_data_import_data__post)
2. [Export ttls](http://localhost:8000/docs#/Database%20Management/get_report_export_ttls__get)
3. [Import Neo4J](http://localhost:8000/docs#/Database%20Management/import_neo4j_import_neo4j__get)

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
