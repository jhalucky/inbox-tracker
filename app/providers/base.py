from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

Category = Literal[
    "lead",
    "client",
    "investor",
    "hiring",
    "internal",
    "vendor",
    "personal",
    "other",
]


class EmailInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sender: str = Field(alias="from")
    subject: str = ""
    body: str = ""
    headers: dict[str, str] = Field(default_factory=dict)


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0


class Classification(BaseModel):
    needs_reply: bool | None
    urgency: int = Field(ge=1, le=5)
    category: Category
    deadline: str | None = None
    reason: str
    summary: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    adjusted_urgency: float | None = None

    @field_validator("summary")
    @classmethod
    def cap_summary(cls, value: str) -> str:
        return value[:200]


class LLMProvider(Protocol):
    def classify(self, email: EmailInput) -> Classification: ...
