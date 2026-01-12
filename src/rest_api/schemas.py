from typing import Optional

from pydantic import BaseModel, ConfigDict, alias_generators


class BaseSchema(BaseModel):
    """Base schema with camelCase aliases."""

    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )


class ChannelMessageCreate(BaseSchema):
    """Channel message creation request model."""

    content: str
    role: str = "user"
    sender_id: Optional[str] = None


class ChannelMessageResponse(BaseSchema):
    """Channel message response model."""

    message_id: str
    channel_id: str
    content: str
    role: str
    sender_id: str
    created_at: int
    created_at_iso: str
