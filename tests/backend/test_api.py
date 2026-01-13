from rest_api.schemas import ChannelMessageCreate
from rest_api.services import (
    GetChannelMessagesService,
    SendChannelMessageService,
)
from rest_api.schemas import ChannelMessageCreateWebsocket
from rest_api.services.send_channel_message_websocket import (
    SendChannelMessageWebsocketService,
)
from botocore.exceptions import ClientError
import json


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


class FakeConnectionsRepo:
    def __init__(self, connections=None):
        self.connections = connections or []
        self.deleted = []

    def get_list(self):
        return list(self.connections)

    def delete(self, connectionId: str):
        self.deleted.append(connectionId)


class FakeApigwClient:
    def __init__(self, gone_id: str | None = None):
        self.sent = []
        self.gone_id = gone_id

    def post_to_connection(self, ConnectionId: str, Data):
        if self.gone_id and ConnectionId == self.gone_id:
            raise ClientError(
                {"Error": {"Code": "GoneException", "Message": "gone"}},
                "PostToConnection",
            )
        self.sent.append({"id": ConnectionId, "data": Data})


def test_send_channel_message_websocket_service_broadcasts_and_embeds_channel_id():
    connections_repo = FakeConnectionsRepo(
        connections=[{"connectionId": "c-1"}, {"connectionId": "c-2"}]
    )
    client = FakeApigwClient()

    service = SendChannelMessageWebsocketService(connections_repository=connections_repo)
    service._apigw_client = client  # inject fake client

    payload = ChannelMessageCreateWebsocket(content="hi", user_id="u-1", metadata={"foo": "bar"})

    result = service(channel_id="general", message_data=payload)

    assert result.channel_id == "general"
    assert len(client.sent) == 2
    body = json.loads(client.sent[0]["data"])
    assert body["channelId"] == "general"
    assert body["userId"] == "u-1"
    assert body["content"] == "hi"
    assert body["metadata"] == {"foo": "bar"}


def test_send_channel_message_websocket_service_prunes_stale_connections():
    connections_repo = FakeConnectionsRepo(connections=[{"connectionId": "gone-1"}])
    client = FakeApigwClient(gone_id="gone-1")

    service = SendChannelMessageWebsocketService(connections_repository=connections_repo)
    service._apigw_client = client

    payload = ChannelMessageCreateWebsocket(content="hi", user_id="u-1")
    service(channel_id="general", message_data=payload)

    assert connections_repo.deleted == ["gone-1"]
