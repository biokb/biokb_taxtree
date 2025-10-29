
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from biokb_taxtree.api.main import app, get_db
from biokb_taxtree.db.manager import DbManager
from biokb_taxtree.db.importer import DbImporter

# Create a new test database engine (SQLite in-memory for testing)
os.makedirs("tests/dbs", exist_ok=True)
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
    #di._path_data_folder = test_data_folder
    di._path_zip_file = os.path.join(test_data_folder,"dummy_taxtree_dump.zip")
    di._path_unzipped_data_folder = os.path.join(test_data_folder,"unzipped")
    dm.__importer = di

    dm.import_data()
    return TestClient(app)


def test_server(client_with_data: TestClient):
    response = client_with_data.get("/")
    assert response.status_code == 200
    assert response.json() == {"msg": "Running!"}
