from datetime import datetime
from typing import Any

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class PocDefinition(SQLModel, table=True):
    __tablename__ = "poc_definitions"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=255)
    description: str = Field(default="")
    severity: str = Field(default="unknown", max_length=32, index=True)
    category: str = Field(default="", max_length=128, index=True)
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    command: str = Field(default="")
    raw_content: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_by: int = Field(default=0, foreign_key="system_users.id", index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class PocRun(SQLModel, table=True):
    __tablename__ = "poc_runs"

    id: int | None = Field(default=None, primary_key=True)
    poc_id: int = Field(default=0, foreign_key="poc_definitions.id", index=True)
    target: str = Field(default="", max_length=2048, index=True)
    sandbox_container_id: int | None = Field(default=None, foreign_key="sandbox_containers.id", index=True)
    status: str = Field(default="queued", max_length=32, index=True)
    command: str = Field(default="")
    output: str = Field(default="")
    exit_code: int | None = Field(default=None)
    duration_ms: int = Field(default=0)
    error: str = Field(default="")
    authorized_scope: str = Field(default="")
    created_by: int = Field(default=0, foreign_key="system_users.id", index=True)
    started_at: datetime = Field(default_factory=datetime.now)
    finished_at: datetime | None = Field(default=None)
