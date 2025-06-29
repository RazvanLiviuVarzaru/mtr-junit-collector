from datetime import datetime
from typing import Optional

from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.schema import Index
from sqlmodel import TIMESTAMP, Column, Field, SQLModel, Text, func


class TestRun(SQLModel, table=True):
    __tablename__ = "test_run"
    id: Optional[int] = Field(default=None, primary_key=True)
    branch: Optional[str] = Field(default=None, max_length=100)
    revision: Optional[str] = Field(default=None, max_length=256)
    platform: str = Field(max_length=100)
    dt: datetime = Field(
        sa_column=Column(
            TIMESTAMP(),
            nullable=False,
            server_default=func.current_timestamp(),
            onupdate=func.current_timestamp(),
        )
    )
    bbnum: int
    typ: str = Field(max_length=32)
    info: Optional[str] = Field(default=None, max_length=255)

    # Define composite indexes
    __table_args__ = (
        Index("branch", "branch", "revision"),
        Index("dt", "dt"),
        Index("platform", "platform", "bbnum"),
    )


class TestFailure(SQLModel, table=True):
    __tablename__ = "test_failure"
    test_run_id: int = Field(foreign_key=None, primary_key=True)
    test_name: str = Field(max_length=100, primary_key=True)
    test_variant: str = Field(default=None, max_length=64, primary_key=True)
    info_text: Optional[str] = Field(default=None, max_length=255)
    failure_text: Optional[str] = Field(
        default=None,
        sa_column=Column(Text().with_variant(LONGTEXT(), "mysql", "mariadb")),
    )
