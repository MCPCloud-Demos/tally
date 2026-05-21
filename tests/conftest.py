import os
import tempfile

# Point the app at a throwaway database before it is imported.
_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_db.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_db.name}"
os.environ["DEMO_API_KEY"] = "tally_sk_test"
os.environ["SEED_ON_STARTUP"] = "true"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def auth():
    return {"Authorization": "Bearer tally_sk_test"}
