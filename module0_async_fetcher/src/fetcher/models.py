from pydantic import BaseModel, Field, model_validator
from typing import Literal

class FetchResult(BaseModel):
    url: str
    status: Literal["ok", "error"]
    status_code: int | None = None
    response_size: int | None = None
    error_message: str | None = None
    error_type: Literal["timeout", "http_error", "connection", "unknown"] | None = None
    attempts: int = Field(ge=1)
    duration: float = Field(ge=0.0)

    @model_validator(mode="after")
    def check_consistency(self) -> "FetchResult":
        if self.status == "ok":
            if self.status_code is None:
                raise ValueError("status='ok' требует указания status_code")
            if self.error_message is not None:
                raise ValueError("status='ok' запрещает наличие error_message")
        elif self.status == "error":
            if self.error_message is None:
                raise ValueError("status='error' требует указания error_message")
            if self.error_type is None:
                raise ValueError("status='error' требует указания error_type")
        return self

class FetchStats(BaseModel):
    total: int
    ok: int
    failed: int
    total_duration: float
    avg_duration: float
    total_attempts: int
    by_error_type: dict[str, int]