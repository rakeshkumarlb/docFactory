"""Usage logging of model calls (DOCFACTORY_USAGE_LOG) and its summary."""
from docfactory.agents.ollama_model_client import USAGE_LOG_ENV, log_usage
from docfactory.agents.run_usage import summarise


def test_nothing_is_logged_without_the_setting(tmp_path, monkeypatch):
    monkeypatch.delenv(USAGE_LOG_ENV, raising=False)
    log_usage("m", "submit_recognition", 10, 2)
    assert list(tmp_path.iterdir()) == []


def test_calls_are_logged_and_summarised_per_step(tmp_path, monkeypatch):
    log = tmp_path / "usage.jsonl"
    monkeypatch.setenv(USAGE_LOG_ENV, str(log))
    log_usage("m", "submit_recognition", 1000, 200)
    log_usage("m", "submit_recognition", 500, 100)
    log_usage("m", "submit_needs", 300, 50)
    text = summarise(log)
    assert "recognition" in text and "      2          1,500            300" in text
    assert text.splitlines()[-1].split() == ["total", "3", "1,800", "350"]
