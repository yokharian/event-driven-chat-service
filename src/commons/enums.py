from enum import Enum


# DynamoDB Models
class MessageDynamoRole(str, Enum):
    user = "user"
    assistant = "assistant"
