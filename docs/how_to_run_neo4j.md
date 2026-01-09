# How to run Neo4J

For the options "Run BioKb-TaxTree as ..."

1. [From command line](run_the_pipeline.md#from-command-line)
2. [As RESTful API server](run_the_pipeline.md#as-restful-api-server)

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