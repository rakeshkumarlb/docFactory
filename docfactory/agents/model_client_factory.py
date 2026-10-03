import os

from docfactory.agents.model_client import ModelClient

PROVIDER_ENV = "DOCFACTORY_PROVIDER"
DEFAULT_PROVIDER = "ollama"


def default_client() -> ModelClient:
    """The model client chosen by env DOCFACTORY_PROVIDER ('ollama' by default, or 'anthropic')."""
    provider = (os.environ.get(PROVIDER_ENV) or DEFAULT_PROVIDER).lower()
    if provider == "ollama":
        from docfactory.agents.ollama_model_client import OllamaModelClient

        return OllamaModelClient()
    if provider == "anthropic":
        from docfactory.agents.anthropic_model_client import AnthropicModelClient

        return AnthropicModelClient()
    raise ValueError(f"unknown {PROVIDER_ENV} {provider!r}; expected 'ollama' or 'anthropic'")
