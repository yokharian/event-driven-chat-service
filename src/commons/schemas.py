import uuid
from datetime import timezone, datetime
from typing import Any
from typing import Optional

from pydantic import BaseModel, ConfigDict, alias_generators, Field


class BaseSchema(BaseModel):
    """Base schema with camelCase aliases."""

    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )


class ChatEventMessage(BaseSchema):
    """Message item stored in the `chat_events` DynamoDB table."""

    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))  # idempotency key
    channel_id: str
    ts: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp()))
    sender_id: str
    role: str
    content: str
    content_type: str = "text"
    created_at_iso: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Optional[dict[str, Any]] = None
