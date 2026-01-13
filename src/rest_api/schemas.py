from typing import Optional

from pydantic import BaseModel, ConfigDict, alias_generators

from commons.schemas import ChatEventMessage


class BaseSchema(BaseModel):
    """Base schema with camelCase aliases."""

    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
        extra="ignore",
    )


class Channel(BaseSchema):
    """Channel metadata."""

    channel_id: str
    name: Optional[str] = None
    created_at: Optional[int] = None


class ChannelMessageCreate(BaseSchema):
    """Channel message creation request model."""

    id: str
    content: str
    role: str = "user"
    sender_id: Optional[str] = None


class ChannelMessageResponse(ChatEventMessage):
    """Channel message response model."""
