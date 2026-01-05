## 🧪 Testing Guidelines

### Testing Tools

- **Backend**: pytest, pytest-asyncio, moto (mocking AWS)
- **Frontend**: streamlit.testing.v1 (AppTest)

---

## ✅ Required Patterns

### Backend Testing

1. **No Actual AWS Calls in Unit Tests** — Use `moto` for mocking SNS/SQS in unit tests.
2. **Moto for Testing** — Use `moto` decorators (`@mock_aws`) for unit tests that involve SNS or SQS.
3. **Core Flow Coverage** — Core flows (publish → agent → consume → deliver) must be covered with unit and integration
   tests.

### Frontend Testing

1. **Streamlit Testing** — Use `streamlit.testing.v1.AppTest` for verifying frontend behavior.

---

*These rules are specific to testing. For backend-specific rules, see `src/rest_api/agents.md`. For frontend-specific
rules, see `src/frontend/agents.md`. For general project rules, see `.specify/memory/constitution.md`.*

