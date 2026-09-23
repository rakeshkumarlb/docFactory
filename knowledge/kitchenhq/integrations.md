---
app: kitchenhq
topic: integrations
summary: 
updated: 2026-09-23
---

# Integrations

## Service interactions

- [F-0040] agent-api reaches dbmcp over MCP (`/mcp`) for every data operation the agent performs. — src: store/kitchenhq/docs/repo/README.md
- [F-0041] The only REST calls agent-api makes to dbmcp are inside the email tools: fetching the recipient address and back-filling the saved menu / pending shopping list so the model's tool call can stay minimal. — src: store/kitchenhq/docs/repo/README.md
- [F-0042] Each agent run's toolset is the remote MCP tools from dbmcp plus local in-process tools: `get_job_context` and the three `send_*_email` tools. — src: store/kitchenhq/docs/repo/README.md
- [F-0043] The three `send_*_email` tools talk SMTP directly to the mail server; when disabled they are a harmless no-op. — src: store/kitchenhq/docs/repo/README.md

## External systems

- [F-0044] The LLM provider is either OpenAI (`OPENAI_API_KEY`) or a local Ollama (`LLM_PROVIDER=ollama` plus `OLLAMA_BASE_URL`). — src: store/kitchenhq/docs/repo/README.md
- [F-0045] Optional email uses an SMTP server configured via `SMTP_HOST` (and credentials) in the root `.env`; a Gmail app password works (`smtp.gmail.com:587`). — src: store/kitchenhq/docs/repo/README.md
