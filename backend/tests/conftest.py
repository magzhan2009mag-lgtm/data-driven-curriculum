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


@pytest.fixture(scope="session")
def independent_engine(tmp_path_factory):
    """Те же демо-данные, но без зависимостей между темами."""
    path = tmp_path_factory.mktemp("independent") / "test.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        generate(session, prerequisites={})
    return engine


@pytest.fixture(scope="session")
def no_textbook_effect_engine(tmp_path_factory):
    """Те же демо-данные, но учебники учат одинаково: остаётся только неравномерный выбор учебников школами."""
    path = tmp_path_factory.mktemp("no_textbook_effect") / "test.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        generate(session, textbook_effects=False)
    return engine
