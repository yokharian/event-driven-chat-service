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
    name: str | None = None
    created_at: int | None = None


# /channels/{channel}/messages


class ChannelMessageCreate(BaseSchema):
    """Channel message creation request model."""

    id: str
    content: str
    role: str = "user"
    sender_id: str


class ChannelMessageResponse(ChatEventMessage):
    """Channel message response model."""


# /channels/{channel}/messages/websocket


class ChannelMessageCreateWebsocket(ChannelMessageCreate):
    """Request schema for REST-to-WebSocket message publishing."""


class ChannelMessageWebsocket(ChannelMessageResponse):
    """Response schema returned after WebSocket broadcast."""
