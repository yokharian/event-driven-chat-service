## 🧪 Testing Guidelines

### Testing Tools

- **Backend**: pytest, pytest-asyncio, moto (mocking AWS)
- **Frontend**: streamlit.testing.v1 (AppTest)

---

## ✅ Required Patterns

### Backend Testing

1. **No Actual AWS Calls in Unit Tests** — Use `moto` for mocking aws services.
2. **Moto for Testing** — Use `moto` decorators (`@mock_aws`) for unit tests that involve aws services.
3. **Core Flow Coverage** — Core flows (publish → agent → consume → deliver) must be covered with unit and integration
   tests.
