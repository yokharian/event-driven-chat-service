from typing import Literal

from pydantic import BaseModel

from .enums import MessageDynamoRole


# DynamoDB Models
class ChannelDynamoModel(BaseModel):
    """DynamoDB model for messages."""
    
    conversation_id: str
    created_at: int  # unix timestamp


class MessageDynamoModel(BaseModel):
    """DynamoDB model for messages."""
    
    channel_id: str
    created_at: int  # unix timestamp
    item_type: Literal["message"] = "message"
    role: MessageDynamoRole = MessageDynamoRole.user
    content: str
