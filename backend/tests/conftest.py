import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Base
from scripts.seed import generate


@pytest.fixture(scope="session")
def seeded_engine(tmp_path_factory):
    path = tmp_path_factory.mktemp("analytics") / "test.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        generate(session)
    return engine
