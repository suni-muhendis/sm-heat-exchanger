"""The package is found through sm-core and stamps its versions on results."""
import json
from pathlib import Path

import pytest

from sm_core import list_environments, make_env
from sm_heat_exchanger.env import HeatExchangerEnv
from sm_heat_exchanger.score import SCORE_REGISTRY

ROOT = Path(__file__).resolve().parents[1]
TASK = json.loads((ROOT / "examples/task_001.json").read_text())
DESIGN = json.loads((ROOT / "examples/design_001.json").read_text())


def test_sm_core_finds_the_heat_exchanger():
    # Read from the installed distribution metadata: this fails if the
    # package was not (re)installed after pyproject.toml changed.
    assert "heat_exchanger" in list_environments()
    env = make_env("heat_exchanger")
    assert isinstance(env, HeatExchangerEnv)
    assert env.name == "heat_exchanger"


def test_score_versions_are_named_by_their_registry_key():
    for key, score_class in SCORE_REGISTRY.items():
        assert score_class.VERSION == key


@pytest.mark.parametrize("design, status", [(DESIGN, "success"), ({"geometry_type": "shell_and_tube"}, "schema_error")])
def test_every_result_is_stamped_whatever_stage_it_stopped_at(design, status):
    result = make_env("heat_exchanger").evaluate("t", TASK, "d", design)
    assert result.status == status
    assert result.environment == "heat_exchanger"
    assert result.simulator_version == "v4"
    assert result.score_version == TASK.get("score_version", "heat_exchanger_score_v1")


def test_the_stamped_score_version_is_the_one_the_task_names():
    task = dict(TASK, score_version="heat_exchanger_score_v3")
    result = make_env("heat_exchanger").evaluate("t", task, "d", DESIGN)
    assert result.score_version == "heat_exchanger_score_v3"
