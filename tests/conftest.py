import pytest


@pytest.fixture(autouse=True)
def _skip_db_migrations(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("api.main.run_migrations", lambda _url: None)
