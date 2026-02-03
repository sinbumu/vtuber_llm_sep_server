from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request schema for /v1/chat."""

    conf_uid: str = Field(..., description="Configuration UID")
    history_uid: str | None = Field(None, description="History UID")
    text: str = Field(..., description="User input text")


class ChatResponse(BaseModel):
    """Response schema for /v1/chat."""

    history_uid: str = Field(..., description="History UID")
    text: str = Field(..., description="Assistant response text")
