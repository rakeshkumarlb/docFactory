"""The skills and the agent are configuration the harness parses: broken YAML silently drops settings."""
import re

import pytest

from conftest import REPO

yaml = pytest.importorskip("yaml")

ENTRY_SKILLS = {"create-shared-model", "create-entity-model", "create-document-model", "add-field", "review-models"}
FILES = sorted((REPO / ".claude" / "skills").glob("*/SKILL.md")) + sorted((REPO / ".claude" / "agents").glob("*.md"))


def frontmatter(path):
    match = re.match(r"---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.S)
    assert match, f"{path} has no frontmatter"
    return yaml.safe_load(match.group(1))


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.parent.name if p.name == "SKILL.md" else p.stem)
def test_frontmatter_parses_and_names_match(path):
    data = frontmatter(path)
    assert data["name"] == (path.parent.name if path.name == "SKILL.md" else path.stem)
    assert isinstance(data["description"], str) and data["description"].strip()


def test_entry_skills_pin_the_agent_and_model():
    found = {p.parent.name: frontmatter(p) for p in FILES if p.name == "SKILL.md"}
    assert ENTRY_SKILLS <= set(found)
    for name in ENTRY_SKILLS:
        data = found[name]
        assert data["context"] == "fork" and data["agent"] == "pydantic-developer-agent", name
        assert data["model"] and data["disable-model-invocation"] is True, name


def test_agent_preloads_existing_skills():
    agent = frontmatter(REPO / ".claude" / "agents" / "pydantic-developer-agent.md")
    existing = {p.parent.name for p in FILES if p.name == "SKILL.md"}
    assert set(agent["skills"]) <= existing


def test_skills_only_reference_scripts_that_exist():
    scripts = {p.name for p in (REPO / ".claude" / "scripts").glob("*.py")}
    for path in FILES:
        for name in re.findall(r"\.claude/scripts/(\w+\.py)", path.read_text(encoding="utf-8")):
            assert name in scripts, f"{path.name} references missing script {name}"
