## 🏗️ Tech Stack

- **Framework**: Streamlit
- **Language**: Python 3.12+
- **Dependency Management**: uv (pyproject.toml + uv.lock only - **NO requirements.txt**)

---

## ✅ Required Patterns

1. **Dependency Management** — **ONLY** use `pyproject.toml` and `uv.lock` for dependencies. **NEVER** use
   `requirements.txt`. Always run `uv lock` locally to generate/update `uv.lock` before committing.
2. **Testing** — See `tests/agents.md` for testing guidelines.

---

*These rules are specific to the frontend module. For general project rules, see `.specify/memory/constitution.md`.*
