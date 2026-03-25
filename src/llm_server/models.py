from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatImageInput(BaseModel):
    """Image payload schema for /v1/chat."""

    source: Literal["screen", "camera", "clipboard", "upload"] = Field(
        ..., description="Image source"
    )
    mime_type: str = Field(..., description="Image MIME type")
    data: str = Field(..., description="Data URL encoded image payload")


class ChatRequest(BaseModel):
    """Request schema for /v1/chat."""

    conf_uid: str = Field(..., description="Configuration UID")
    history_uid: str | None = Field(None, description="History UID")
    text: str = Field(..., description="User input text")
    images: list[ChatImageInput] | None = Field(
        None, description="Optional image attachments"
    )


class ChatResponse(BaseModel):
    """Response schema for /v1/chat."""

    history_uid: str = Field(..., description="History UID")
    text: str = Field(..., description="Assistant response text")
