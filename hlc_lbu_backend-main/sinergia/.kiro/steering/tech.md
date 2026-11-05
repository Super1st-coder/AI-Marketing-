---
inclusion: always
---

# Tech Stack - Flask Service

## Core Stack

- Language: Python 3.8. Do not use syntax or stdlib features newer than 3.8 (no `match`, no `X | Y` union types, no built-in generics like `list[str]`; use `typing.List`, `Optional`, `Dict`, etc.).
- Framework: Flask 1.1.2 (pinned). Write code compatible with Flask 1.x and its ecosystem (e.g. `flask-restplus`, `Flask-SQLAlchemy` 2.x, `Flask-JWT-Extended` 3.x). Do not upgrade or add dependencies unless explicitly asked.
- Dependencies: `requirements.txt` (runtime) and `requirements-test.txt` (test). Keep versions pinned.

## Environment

- Always use the local virtual environment at `venv/` (Python 3.8).
- Run commands through the venv interpreter rather than the system Python:
  - Tests: `venv/bin/python -m pytest tests/`
  - Single file: `venv/bin/python -m pytest tests/v2/unit/<file>.py -q`
- Never install packages globally.

## Testing

- Framework: pytest.
- Plugins and helpers:
  - `pytest-mock` (`mocker` fixture) to mock internal services, repositories, and external API clients. Unit tests must not hit real databases or third-party APIs.
  - `blinker` for Flask signals, only when signal behavior is under test.
  - `hypothesis` is available for property-based tests.
- Layout: tests live in `tests/`, split by API version and type (`tests/v2/unit/`, `tests/v2/integration/`). Name files `test_<subject>.py`.
- Prefer testing use cases in isolation by mocking their collaborators.

## Coding Standards

- Follow PEP 8.
- Use explicit type hints on service/use case functions and methods (parameters and return types) and on test functions (`-> None`).
- Match the existing style and patterns of the surrounding module before introducing new ones.
