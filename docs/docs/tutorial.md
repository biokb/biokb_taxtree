# Tutorial

## Installation

It's highly recommended to install a virtual environment with

```bash
python3 -m venv .venv
```
After setup activate the environment with
```bash
source .venv/bin/activate
```
#TODO: change the text here if the lib is published 
Now you can install the library (once it is)

```bash
pip install biokb_taxtree
```

If you want to install it from GitHub use
```bash
pip install 
```

## Import data

```python
from biokb_taxtree.db.manager import DbManager
from sqlalchemy import create_engine
```