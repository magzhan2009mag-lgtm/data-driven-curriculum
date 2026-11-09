from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class School(Base):
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]

    classes: Mapped[list["SchoolClass"]] = relationship(back_populates="school")


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]

    topics: Mapped[list["Topic"]] = relationship(back_populates="subject")
    textbooks: Mapped[list["Textbook"]] = relationship(back_populates="subject")


class Textbook(Base):
    __tablename__ = "textbooks"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    name: Mapped[str]

    subject: Mapped[Subject] = relationship(back_populates="textbooks")


class SchoolClass(Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    textbook_id: Mapped[int] = mapped_column(ForeignKey("textbooks.id"), index=True)
    name: Mapped[str]

    school: Mapped[School] = relationship(back_populates="classes")
    textbook: Mapped[Textbook] = relationship()
    students: Mapped[list["Student"]] = relationship(back_populates="school_class")


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), index=True)
    name: Mapped[str]
    pretest_score: Mapped[int]

    school_class: Mapped[SchoolClass] = relationship(back_populates="students")


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    name: Mapped[str]
    hours_planned: Mapped[int]

    subject: Mapped[Subject] = relationship(back_populates="topics")
    tests: Mapped[list["Test"]] = relationship(back_populates="topic")


class Test(Base):
    __tablename__ = "tests"
    __table_args__ = (UniqueConstraint("topic_id", "number"),)
    # Имя класса начинается с Test: без этого флага pytest принял бы модель за набор тестов.
    __test__ = False

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), index=True)
    number: Mapped[int]

    topic: Mapped[Topic] = relationship(back_populates="tests")


class TestResult(Base):
    __tablename__ = "test_results"
    __table_args__ = (UniqueConstraint("test_id", "student_id"),)
    __test__ = False

    id: Mapped[int] = mapped_column(primary_key=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), index=True)
    textbook_id: Mapped[int] = mapped_column(ForeignKey("textbooks.id"), index=True)
    score: Mapped[int]


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (UniqueConstraint("test_id", "number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), index=True)
    number: Mapped[int]


class ItemResponse(Base):
    __tablename__ = "item_responses"
    __table_args__ = (UniqueConstraint("item_id", "student_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    correct: Mapped[bool]


class TopicYearStat(Base):
    """Архив прошлых лет: только средние по школе и теме."""

    __tablename__ = "topic_year_stats"
    __table_args__ = (UniqueConstraint("topic_id", "school_id", "year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), index=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    year: Mapped[int]
    avg_score: Mapped[float]
    n_students: Mapped[int]
