from rest_api.schemas import ChannelMessageCreate
from rest_api.services import (
    GetChannelMessagesService,
    SendChannelMessageService,
)


class FakeRepo:
    def __init__(self, items=None):
        self.items = items or []

    def get_list(self):
        return list(self.items)

    def create(self, item):
        self.items.append(item)
        return item

    def get_by_key(self, **_kwargs):
        return None


def test_get_channel_messages_service_filters_and_sorts():
    repo = FakeRepo(
        items=[
            {
                "channel_id": "general",
                "ts": 200,
                "created_at": 200,
                "created_at_iso": "2024-01-01T00:03:20Z",
                "id": "m-2",
                "sender_id": "user-1",
                "role": "user",
                "content": "second",
            },
            {
                "channel_id": "general",
                "ts": 100,
                "created_at": 100,
                "created_at_iso": "2024-01-01T00:01:40Z",
                "id": "m-1",
                "sender_id": "user-1",
                "role": "user",
                "content": "first",
            },
            {
                "channel_id": "random",
                "ts": 150,
                "created_at": 150,
                "created_at_iso": "2024-01-01T00:02:30Z",
                "id": "m-3",
                "sender_id": "user-2",
                "role": "user",
                "content": "other-channel",
            },
        ]
    )
    service = GetChannelMessagesService(repository=repo)

    result = service(channel_id="general")

    assert [msg.id for msg in result] == ["m-1", "m-2"]
    assert all(msg.channel_id == "general" for msg in result)


def test_send_channel_message_service_persists_message():
    message_repo = FakeRepo()
    service = SendChannelMessageService(repository=message_repo)

    payload = ChannelMessageCreate(content="Hello", role="user", sender_id="alice")
    result = service(channel_id="general", message_data=payload)

    assert result.channel_id == "general"
    assert result.content == "Hello"
    assert result.role == "user"
    assert result.sender_id == "alice"
    assert len(message_repo.items) == 1
    assert message_repo.items[0]["channel_id"] == "general"
    assert message_repo.items[0]["id"] == result.id
