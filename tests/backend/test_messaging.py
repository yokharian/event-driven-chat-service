from workers import agent_worker


class FakeRepo:
    def __init__(self):
        self.created = []

    def create(self, item):
        self.created.append(item)
        return item


def make_stream_record(role: str = "user", content: str = "hi"):
    return {
        "eventName": "INSERT",
        "dynamodb": {
            "NewImage": {
                "channel_id": {"S": "ch-1"},
                "created_at": {"N": "1700000000"},
                "item_type": {"S": "message"},
                "role": {"S": role},
                "content": {"S": content},
            }
        },
    }


def test_agent_worker_processes_user_and_creates_ai(monkeypatch):
    repo = FakeRepo()
    monkeypatch.setattr(agent_worker, "repository", repo)
    monkeypatch.setattr(agent_worker, "generate_ai_response", lambda msg: "AI:" + msg)

    agent_worker.process_user_message(make_stream_record(role="user", content="hello"))

    assert len(repo.created) == 1
    ai = repo.created[0]
    assert ai["role"] == "assistant"
    assert ai["content"] == "AI:hello"
    assert ai["channel_id"] == "ch-1"


def test_agent_worker_skips_non_insert(monkeypatch):
    repo = FakeRepo()
    monkeypatch.setattr(agent_worker, "repository", repo)

    record = make_stream_record()
    record["eventName"] = "MODIFY"
    agent_worker.process_user_message(record)

    assert repo.created == []


def test_agent_worker_skips_non_user_role(monkeypatch):
    repo = FakeRepo()
    monkeypatch.setattr(agent_worker, "repository", repo)

    agent_worker.process_user_message(make_stream_record(role="assistant", content="echo"))

    assert repo.created == []
