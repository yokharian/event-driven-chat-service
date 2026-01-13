import json

from botocore.exceptions import ClientError

from workers import delivery_worker


class FakeApiGateway:
    def __init__(self, fail_first: bool = False):
        self.fail_first = fail_first
        self.sent = []

    def post_to_connection(self, ConnectionId, Data):
        if self.fail_first and not self.sent:
            # Simulate a single stale connection failure, then allow subsequent sends
            self.fail_first = False
            error_response = {"Error": {"Code": "GoneException"}}
            raise ClientError(error_response, "PostToConnection")
        self.sent.append((ConnectionId, Data))


class FakeConnectionsRepo:
    def __init__(self, items=None):
        self.items = items or []
        self.deleted = []

    def get_list(self):
        return list(self.items)

    def delete(self, **keys):
        if "connectionId" in keys:
            self.deleted.append(keys["connectionId"])


def make_delivery_record(channel_id: str = "ch-1", role: str = "assistant", content: str = "hi"):
    return {
        "eventName": "INSERT",
        "dynamodb": {
            "NewImage": {
                "channel_id": {"S": channel_id},
                "created_at": {"N": "1700000000"},
                "item_type": {"S": "message"},
                "role": {"S": role},
                "content": {"S": content},
                "created_at_iso": {"S": "2024-01-01T00:00:00Z"},
                "id": {"S": "m-1"},
            }
        },
    }


def test_delivery_worker_broadcasts_to_connections(monkeypatch):
    connections_repo = FakeConnectionsRepo([{"connectionId": "c-1"}, {"connectionId": "c-2"}])
    api = FakeApiGateway()

    monkeypatch.setattr(delivery_worker, "connections_repo", connections_repo)
    monkeypatch.setattr(delivery_worker, "api_gateway", api)

    delivery_worker.deliver_message(make_delivery_record())

    assert len(api.sent) == 2
    payload = json.loads(api.sent[0][1].decode())
    assert payload["conversation_id"] == "ch-1"
    assert payload["content"] == "hi"


def test_delivery_worker_removes_gone_connections(monkeypatch):
    connections_repo = FakeConnectionsRepo([{"connectionId": "stale"}, {"connectionId": "alive"}])
    api = FakeApiGateway(fail_first=True)

    monkeypatch.setattr(delivery_worker, "connections_repo", connections_repo)
    monkeypatch.setattr(delivery_worker, "api_gateway", api)

    delivery_worker.deliver_message(make_delivery_record())

    assert "stale" in connections_repo.deleted
    # One failure, one success
    assert len(api.sent) == 1
