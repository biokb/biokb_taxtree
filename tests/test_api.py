import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from biokb_taxtree.api.main import app, get_db
from biokb_taxtree.db.importer import DbImporter
from biokb_taxtree.db.manager import DbManager

# Create a new test database engine (SQLite in-memory for testing)
os.makedirs("tests/dbs", exist_ok=True)
if os.path.exists(os.path.join("tests", "dbs", "test.db")):
    os.remove(os.path.join("tests", "dbs", "test.db"))

test_engine = create_engine("sqlite:///tests/dbs/test.db")
# test_engine = create_engine(
#     "mysql+pymysql://biokb_user:biokb_passwd@127.0.0.1:3307/biokb"
# )
TestSessionLocal = sessionmaker(bind=test_engine)

### NOTE: If you want to test the API yourself in your browser, remember to export the connection string first (`export CONNECTION_STR="sqlite:///tests/dbs/test.db"` in a Python terminal)


# Dependency override to use test database
def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Apply the override to the FastAPI dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture()
def client_with_data():
    # Create tables in the test database
    test_data_folder = os.path.join("tests", "dummy_data")
    dm = DbManager(test_engine)
    # Work around to setting the test data folder - could maybe implement this directly into the dbmanager
    di = DbImporter(engine=test_engine)
    zipped_file_path = di._set_path_zip_file(
        os.path.join(test_data_folder, "dummy_taxtree_dump.zip")
    )
    di._path_zip_file = os.path.join(test_data_folder, "dummy_taxtree_dump.zip")
    unzipped_data_folder_path = di._set_path_unziped_data_folder(
        os.path.join(test_data_folder, "unzipped")
    )
    dm.set_importer(di)
    dm.import_data()
    return TestClient(app)


def test_server(client_with_data: TestClient):
    response = client_with_data.get("/")
    assert response.status_code == 200
    assert response.json() == {"msg": "Running!"}


class TestName:
    def test_get_name(self, client_with_data: TestClient):
        response = client_with_data.get("/names/search/?name_txt=ancestor")
        assert response.status_code == 200
        data = response.json()
        expected = {
            "count": 1,
            "offset": 0,
            "limit": 10,
            "results": [
                {
                    "name_txt": "ancestor",
                    "unique_name": None,
                    "name_class": "synonym",
                    "tax_id": 1,
                }
            ],
        }
        assert data == expected

    def test_list_names(self, client_with_data: TestClient):
        response = client_with_data.get("/names/search/")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 3

    def test_list_names_offset(self, client_with_data: TestClient):
        response = client_with_data.get("/names/search/?offset=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1

    def test_list_names_limit(self, client_with_data: TestClient):
        response = client_with_data.get("/names/search/?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2

    def test_list_names_offset_limit(self, client_with_data: TestClient):
        response = client_with_data.get("/names/search/?offset=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        expected = {
            "count": 3,
            "offset": 2,
            "limit": 2,
            "results": [
                {
                    "name_txt": "child",
                    "unique_name": "Child <child>",
                    "name_class": "scientific name",
                    "tax_id": 3,
                }
            ],
        }
        assert data == expected


class TestNode:
    def test_get_node(self, client_with_data: TestClient):
        response = client_with_data.get("/node/search/?tax_id=1")
        assert response.status_code == 200
        data = response.json()
        expected = {
            "count": 1,
            "offset": 0,
            "limit": 10,
            "results": [
                {
                    "tax_id": 1,
                    "parent_tax_id": 1,
                    "rank": "no rank",
                    "embl_code": None,
                    "division_id": 8,
                    "inherited_div_flag": False,
                    "genetic_code_id": 1,
                    "inherited_gc_flag": False,
                    "mitochondrial_genetic_code_id": 0,
                    "inherited_mgc_flag": False,
                    "genbank_hidden_flag": False,
                    "hidden_subtree_root_flag": False,
                    "comments": None,
                    "plastid_genetic_code_id": None,
                    "inherited_pgc_flag": None,
                    "specified_species": False,
                    "hydrogenosome_genetic_code_id": 0,
                    "inherited_hgc_flag": True,
                    "tree_id": 1,
                    "tree_parent_id": None,
                    "level": 1,
                    "right_tree_id": 4,
                    "is_leaf": False,
                    "names": [
                        {
                            "name_txt": "ancestor",
                            "unique_name": None,
                            "name_class": "synonym",
                        }
                    ],
                    "ranked_lineage": {
                        "tax_id": 1,
                        "tax_name": "root",
                        "species": None,
                        "genus": None,
                        "family": None,
                        "order": None,
                        "class_": None,
                        "phylum": None,
                        "kingdom": None,
                        "domain": "",
                    },
                }
            ],
        }
        assert data == expected

    def test_list_nodes(self, client_with_data: TestClient):
        response = client_with_data.get("/node/search/")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 3

    def test_list_nodes_offset(self, client_with_data: TestClient):
        response = client_with_data.get("/node/search/?offset=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1

    def test_list_nodes_limit(self, client_with_data: TestClient):
        response = client_with_data.get("/node/search/?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2

    def test_list_nodes_offset_limit(self, client_with_data: TestClient):
        response = client_with_data.get("/node/search/?offset=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        expected = {
            "count": 3,
            "offset": 2,
            "limit": 2,
            "results": [
                {
                    "tax_id": 3,
                    "parent_tax_id": 2,
                    "rank": "genus",
                    "embl_code": None,
                    "division_id": 0,
                    "inherited_div_flag": True,
                    "genetic_code_id": 11,
                    "inherited_gc_flag": True,
                    "mitochondrial_genetic_code_id": 0,
                    "inherited_mgc_flag": True,
                    "genbank_hidden_flag": False,
                    "hidden_subtree_root_flag": False,
                    "comments": "code compliant",
                    "plastid_genetic_code_id": None,
                    "inherited_pgc_flag": None,
                    "specified_species": False,
                    "hydrogenosome_genetic_code_id": 0,
                    "inherited_hgc_flag": True,
                    "tree_id": 3,
                    "tree_parent_id": 2,
                    "level": 2,
                    "right_tree_id": None,
                    "is_leaf": True,
                    "names": [
                        {
                            "name_txt": "child",
                            "unique_name": "Child <child>",
                            "name_class": "scientific name",
                        }
                    ],
                    "ranked_lineage": {
                        "tax_id": 3,
                        "tax_name": "Archaea",
                        "species": None,
                        "genus": None,
                        "family": None,
                        "order": None,
                        "class_": None,
                        "phylum": None,
                        "kingdom": None,
                        "domain": "",
                    },
                }
            ],
        }
        assert data == expected


class TestRankedLineage:
    def test_get_lineage(self, client_with_data: TestClient):
        response = client_with_data.get("/ranked_lineage/search/?tax_id=1")
        assert response.status_code == 200
        data = response.json()
        expected = {
            "count": 1,
            "offset": 0,
            "limit": 10,
            "results": [
                {
                    "tax_id": 1,
                    "tax_name": "root",
                    "species": None,
                    "genus": None,
                    "family": None,
                    "order": None,
                    "class_": None,
                    "phylum": None,
                    "kingdom": None,
                    "domain": "",
                }
            ],
        }
        assert data == expected

    def test_list_lineages(self, client_with_data: TestClient):
        response = client_with_data.get("/ranked_lineage/search/")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 3

    def test_list_lineages_offset(self, client_with_data: TestClient):
        response = client_with_data.get("/ranked_lineage/search/?offset=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1

    def test_list_lineages_limit(self, client_with_data: TestClient):
        response = client_with_data.get("/ranked_lineage/search/?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2

    def test_list_lineages_offset_limit(self, client_with_data: TestClient):
        response = client_with_data.get("/ranked_lineage/search/?offset=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        expected = {
            "count": 3,
            "offset": 2,
            "limit": 2,
            "results": [
                {
                    "tax_id": 3,
                    "tax_name": "Archaea",
                    "species": None,
                    "genus": None,
                    "family": None,
                    "order": None,
                    "class_": None,
                    "phylum": None,
                    "kingdom": None,
                    "domain": "",
                }
            ],
        }
        assert data == expected
