# Installation

## Without Podman/Docker

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install biokb_taxtree
```


## With Podman/Docker

If you have [docker](https://www.docker.com/get-started) or [podman](https://podman.io/getting-started/installation) on your system, the easiest way to run all components (relational database, RESTful API server, phpMyAdmin GUI) is to use networked containers with `podman-compose`/`docker-compose`.

```bash
git clone https://github.com/biokb/biokb_taxtree.git
cd biokb_taxtree
python3 -m venv .venv
source .venv/bin/activate
pip install podman-compose
podman-compose -f docker-compose.mysql_neo4j_pma.yml --env-file .env_template up -d
```

Tip: Change the default passwords in the `.env_template` file before starting the containers for better security.