import pytest


@pytest.fixture(autouse=True)
def _set_fake_keys(monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "fake")
    monkeypatch.setenv("MOONSHOT_API_KEY", "fake")
    monkeypatch.setenv("FIREWORKS_API_KEY", "fake")
