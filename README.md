# BioKb TaxTree

## Test MySQL import

```bash
podman-compose up -d mysql pma
logger.info("Start downloaded to taxtree")
export CONNECTION_STR="mysql+pymysql://biokb_user:biokb_passwd@localhost:3307/biokb"
fastapi run src/biokb_taxtree/api/main.py --reload
```

- Open [API](http://localhost:8000/docs#/Manage/import_data_import_data__get) -> Try it out -> Execute
- Open [phpMyAdmin](http://localhost:8081/index.php?route=/database/structure&db=biokb)

## Install

install venv and ...

```bash
pip install pdm
pdm install
```

## Documentation

Please use the documentation with

```bash
mkdocs serve
```
