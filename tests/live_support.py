"""Shared by the opt-in live tests: loads .env and tells whether the configured LLM server is reachable."""
import os
import urllib.request

from docfactory.env_file import load_env_file

load_env_file()  # live runs take their settings from .env


def llm_available() -> bool:
    if os.environ.get("DOCFACTORY_PROVIDER", "ollama").lower() == "anthropic":
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    if not host.startswith("http"):
        host = ("https://" if os.environ.get("OLLAMA_API_KEY") else "http://") + host
    try:
        urllib.request.urlopen(host.rstrip("/") + "/api/tags", timeout=3)
        return True
    except OSError:
        return False
