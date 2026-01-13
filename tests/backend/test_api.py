from rest_api.schemas import ChannelMessageCreate
from rest_api.services import (
    GetChannelMessagesService,
    SendChannelMessageService,
)


class FakeRepo:
    def __init__(self, items=None):
        self.items = items or []
        self.table_hash_key = "channel_id"

    def get_list(self):
        return list(self.items)

    def create(self, item):
        self.items.append(item)
        return item

    def get_by_key(self, *, raise_not_found=True, filter_attributes=None, limit=1, **keys):
        partition_key = self.table_hash_key
        partition_value = keys.get(partition_key)
        results = [item for item in self.items if item.get(partition_key) == partition_value]
        if filter_attributes:
            for name, value in filter_attributes.items():
                results = [item for item in results if item.get(name) == value]
        item = results[0] if results else None
        if item:
            return item
        if raise_not_found:
            raise KeyError(f"Object {keys} was not found")
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

    payload = ChannelMessageCreate(id="msg-1", content="Hello", role="user", sender_id="alice")
    result = service(channel_id="general", message_data=payload)

    assert result.channel_id == "general"
    assert result.content == "Hello"
    assert result.role == "user"
    assert result.sender_id == "alice"
    assert len(message_repo.items) == 1
    assert message_repo.items[0]["channel_id"] == "general"
    assert message_repo.items[0]["id"] == result.id


def test_send_channel_message_service_is_idempotent():
    message_repo = FakeRepo()
    service = SendChannelMessageService(repository=message_repo)

    payload = ChannelMessageCreate(id="test-123", content="Hello", role="user", sender_id="alice")

    first = service(channel_id="general", message_data=payload)
    second = service(channel_id="general", message_data=payload)

    assert len(message_repo.items) == 1
    assert first.id == "test-123"
    assert second.id == "test-123"
    assert first.content == second.content
