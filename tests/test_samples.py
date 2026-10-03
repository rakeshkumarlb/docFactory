"""Every JSON file under samples/json/ must validate against the model of its folder, and the seed scripts must run."""
import json
from pathlib import Path

import pytest

from docfactory import db
from docfactory.entitymodels.facts.application_overview import ApplicationOverview
from docfactory.entitymodels.facts.architecture import Architecture
from docfactory.entitymodels.facts.backup_recovery import BackupRecovery
from docfactory.entitymodels.facts.deployment import Deployment
from docfactory.entitymodels.facts.environments import Environments
from docfactory.entitymodels.facts.functional_requirements import FunctionalRequirements
from docfactory.entitymodels.facts.known_errors import KnownErrors
from docfactory.entitymodels.facts.kpis import Kpis
from docfactory.entitymodels.facts.monitoring import Monitoring
from docfactory.entitymodels.facts.non_functional_requirements import NonFunctionalRequirements
from docfactory.entitymodels.facts.slo import Slo
from docfactory.entitymodels.facts.sop import Sop
from docfactory.entitymodels.facts.support import Support

SAMPLES = Path(__file__).resolve().parents[1] / "samples" / "json"

MODEL_BY_FOLDER = {
    "application_overview": ApplicationOverview,
    "architecture": Architecture,
    "backup_recovery": BackupRecovery,
    "deployment": Deployment,
    "environments": Environments,
    "functional_requirements": FunctionalRequirements,
    "known_errors": KnownErrors,
    "kpis": Kpis,
    "monitoring": Monitoring,
    "non_functional_requirements": NonFunctionalRequirements,
    "slo": Slo,
    "sop": Sop,
    "support": Support,
}

SAMPLE_FILES = sorted(SAMPLES.glob("*/*.json"))


def test_every_sample_folder_has_a_model():
    folders = {p.name for p in SAMPLES.iterdir() if p.is_dir()}
    assert folders == set(MODEL_BY_FOLDER)


@pytest.mark.parametrize("path", SAMPLE_FILES, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_sample_validates_against_its_model(path):
    model = MODEL_BY_FOLDER[path.parent.name]
    model.model_validate(json.loads(path.read_text(encoding="utf-8")))


def test_requirements_seed_stores_both_facts(tmp_db):
    from seed import seed_readmeforge_requirements

    seed_readmeforge_requirements.main()
    functional = db.get_row("KnowledgeFacts", "ReadmeForge.FunctionalRequirements")
    non_functional = db.get_row("KnowledgeFacts", "ReadmeForge.NonFunctionalRequirements")
    assert functional["Version"] == 2  # minimal sample first, then the full one
    assert non_functional["Version"] == 1
    assert functional["AppID"] == non_functional["AppID"] == "ReadmeForge"
