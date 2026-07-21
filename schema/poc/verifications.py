from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from schema.common.responses import PaginatedResponse


class PocRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


class PocExecutionMode(StrEnum):
    DIRECT = "direct"
    SANDBOX = "sandbox"


class PocDefinitionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    severity: str
    category: str
    tags: list[str]
    command: str
    raw_content: dict[str, Any]
    created_by: int
    created_at: datetime
    updated_at: datetime


class PocRunSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    poc_id: int
    poc_name: str
    target: str
    sandbox_container_id: int | None
    sandbox_container_name: str
    status: PocRunStatus
    command: str
    output: str
    exit_code: int | None
    duration_ms: int
    error: str
    authorized_scope: str
    created_by: int
    started_at: datetime
    finished_at: datetime | None


class ImportPocRequest(BaseModel):
    content: str = Field(min_length=1, max_length=262_144)


class CreatePocRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=4000)
    severity: str = Field(default="unknown", max_length=32)
    category: str = Field(default="", max_length=128)
    tags: list[str] = Field(default_factory=list, max_length=32)
    command: str = Field(min_length=1, max_length=16_384)
    raw_content: dict[str, Any] = Field(default_factory=dict)

    @field_validator("severity", "category", mode="before")
    @classmethod
    def normalize_short_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, str):
            value = [item.strip() for item in value.split(",")]
        if isinstance(value, list):
            return [str(item).strip().lower() for item in value if str(item).strip()]
        return value


class RunPocRequest(BaseModel):
    target: str = Field(min_length=1, max_length=2048)
    execution_mode: PocExecutionMode = PocExecutionMode.DIRECT
    sandbox_container_id: int | None = Field(default=None, gt=0)
    authorized: bool = False
    authorized_scope: str = Field(default="", max_length=4000)
    timeout_seconds: int = Field(default=60, ge=5, le=600)

    @model_validator(mode="after")
    def validate_authorization(self):
        if not self.authorized:
            raise ValueError("authorized testing confirmation is required")
        if not self.authorized_scope.strip():
            raise ValueError("authorized_scope is required")
        if self.execution_mode == PocExecutionMode.SANDBOX and self.sandbox_container_id is None:
            raise ValueError("sandbox_container_id is required for sandbox execution")
        return self


class QueryPocsResponse(PaginatedResponse[PocDefinitionSchema]):
    pass


class QueryPocRunsResponse(PaginatedResponse[PocRunSchema]):
    pass
