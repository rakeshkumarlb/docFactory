"""The Ollama embedder, document read side and saver resolution."""
import pytest

from docfactory import db, documents
from docfactory.agents.ollama_model_client import OllamaModelClient
from docfactory.retrieval.ollama_embedder import OllamaEmbedder
from docfactory.saver_resolution import document_saver_classes, document_saver_for_key

class _Client(OllamaModelClient):
    def __init__(self, replies):
        super().__init__(model="m", host="http://x")
        self.replies, self.sent = replies, []

    def post_json(self, path, body):
        self.sent.append((path, body))
        return self.replies.pop(0)


def test_ollama_embedder_batches_and_checks_the_count():
    client = _Client([{"embeddings": [[1.0, 0.0]] * 32}, {"embeddings": [[0.0, 1.0]]}])
    vectors = OllamaEmbedder(model="emb", client=client).embed([f"t{i}" for i in range(33)])
    assert len(vectors) == 33 and [path for path, _ in client.sent] == ["/api/embed"] * 2
    assert client.sent[0][1]["model"] == "emb" and len(client.sent[1][1]["input"]) == 1
    with pytest.raises(RuntimeError, match="embedding model"):
        OllamaEmbedder(model="emb", client=_Client([{"embeddings": []}])).embed(["a"])


def test_ollama_embedder_model_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("DOCFACTORY_EMBED_MODEL", "my-embed")
    assert OllamaEmbedder(client=_Client([])).model == "my-embed"


@pytest.mark.usefixtures("tmp_db")
def test_get_document_and_list_documents():
    assert documents.get_document("A.Outputs.Overview") is None
    db.write_row("DocumentOutputs", "A.Outputs.Overview", "{}", "h", "A", 50.0, 2)
    db.write_row("DocumentOutputs", "B.Outputs.Overview", "{}", "h", "B", 10.0, 1)
    record = documents.get_document("A.Outputs.Overview")
    assert (record.key, record.value, record.version, record.app_id, record.completeness) == ("A.Outputs.Overview", "{}", 2, "A", 50.0)
    assert [r.key for r in documents.list_documents()] == ["A.Outputs.Overview", "B.Outputs.Overview"]
    assert [r.key for r in documents.list_documents("B")] == ["B.Outputs.Overview"]


def test_every_document_body_key_resolves_to_exactly_one_saver():
    assert sorted(cls.model.__name__ for cls in document_saver_classes()) == ["OverviewDocument", "SmtdDocument", "SopDocument", "SrsDocument"]
    for doc_type, model in (("Overview", "OverviewDocument"), ("SMTD", "SmtdDocument"), ("SOP", "SopDocument"), ("SRS", "SrsDocument")):
        assert document_saver_for_key(f"ReadmeForge.Outputs.{doc_type}").model.__name__ == model
    assert document_saver_for_key("ReadmeForge.Outputs.SMTD.DocumentControl") is None
    assert document_saver_for_key("ReadmeForge.Architecture") is None


def test_the_embed_host_replaces_the_chat_host_and_never_gets_the_chat_key(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "https://ollama.com")
    monkeypatch.setenv("OLLAMA_API_KEY", "chat-secret")
    monkeypatch.delenv("DOCFACTORY_EMBED_API_KEY", raising=False)
    monkeypatch.setenv("DOCFACTORY_EMBED_HOST", "http://localhost:11434")
    embedder = OllamaEmbedder(model="emb")
    assert embedder._client.host == "http://localhost:11434" and embedder._client.api_key is None
    monkeypatch.setenv("DOCFACTORY_EMBED_API_KEY", "embed-key")
    assert OllamaEmbedder(model="emb")._client.api_key == "embed-key"
    monkeypatch.delenv("DOCFACTORY_EMBED_HOST")
    assert OllamaEmbedder(model="emb")._client.api_key == "chat-secret"
