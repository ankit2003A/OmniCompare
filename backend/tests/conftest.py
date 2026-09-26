import os, pytest
os.environ["DATABASE_URL"] = "sqlite:///./test_omnicompare.db"
from app.config import get_settings
get_settings.cache_clear()
from app.seed.seed import run_seed
from app.db import SessionLocal
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def seeded():
    run_seed(verbose=False)
    yield
    if os.path.exists("test_omnicompare.db"):
        os.remove("test_omnicompare.db")


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    s = SessionLocal()
    yield s
    s.close()
