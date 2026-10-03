"""Manual trigger for the ingestion agent: `python -m docfactory.agents.run_ingestion`.

Reads settings from .env (see .env.example). Uses a local Ollama server by default (env DOCFACTORY_MODEL picks the model, default llama3.2); set DOCFACTORY_PROVIDER=anthropic
to use the Anthropic API instead (needs ANTHROPIC_API_KEY).
"""
from docfactory.agents.ingestion_agent import IngestionAgent
from docfactory.agents.model_client_factory import default_client
from docfactory.env_file import load_env_file


def main() -> None:
    load_env_file()  # settings from .env; variables already set in the shell win
    agent = IngestionAgent(default_client())
    print(agent.run())


if __name__ == "__main__":
    main()
