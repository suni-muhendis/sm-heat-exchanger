"""
Tests for Score V5: V4's gate with a logarithmic cost band and a firmer gate.

V5 changes two things in V4 and nothing else. Cost is judged on a ratio scale,
so a design at 5x a reference cost and one at 40x no longer score alike; and a
design that misses a requirement earns at most half the gate share, so any
design that meets every requirement outranks any design that does not.
"""

import math

import pytest

from sm_core import make_env
from sm_heat_exchanger.score import SCORE_REGISTRY, get_score_function


TASK = {
    "task_id": "score_v5_test",
    "score_version": "heat_exchanger_score_v5",
    "target_heat_duty": 250000.0,
    "max_dp_tube": 10000.0,
    "max_dp_shell": 10000.0,
    "gate_share": 0.30,
    "cost_good": 2000.0,
    "warning_penalty_per_warning": 0.10,
}


@pytest.fixture(scope="module")
def score():
    return get_score_function("heat_exchanger_score_v5")


def metrics(**overrides):
    base = {
        "heat_duty_W": 260000.0,
        "dp_tube_Pa": 8000.0,
        "dp_shell_Pa": 3000.0,
        "effectiveness": 0.414,
        "cost_annualised_USD_per_yr": 2000.0,
        "num_warnings": 0.0,
    }
    base.update(overrides)
    return base


def total(score, task=TASK, **overrides):
    return score.calculate_score(task, metrics(**overrides)).normalized_total


def test_v5_is_registered_and_v1_to_v4_are_unchanged():
    assert list(SCORE_REGISTRY) == [f"heat_exchanger_score_v{i}" for i in range(1, 6)]
    assert get_score_function("heat_exchanger_score_v5").VERSION == "heat_exchanger_score_v5"


def test_the_environment_applies_v5_when_a_task_names_it():
    env = make_env("heat_exchanger")
    assert env.get_score_function(TASK).VERSION == "heat_exchanger_score_v5"


def test_invalid_design_scores_zero(score):
    result = score.calculate_score(TASK, {}, is_valid=False, error_message="DRC")
    assert result.normalized_total == 0.0 and not result.is_valid


def test_a_perfect_design_scores_one(score):
    assert total(score) == pytest.approx(1.0)


def test_cost_is_judged_on_a_log_scale(score):
    # Full credit at cost_good; at the geometric midpoint of the band the cost
    # term is exactly half; at cost_good * span it is zero.
    span = 80.0
    mid = 2000.0 * math.sqrt(span)
    assert total(score, cost_annualised_USD_per_yr=mid) == pytest.approx(0.30 + 0.70 * 0.5)
    assert total(score, cost_annualised_USD_per_yr=2000.0 * span) == pytest.approx(0.30)
    assert total(score, cost_annualised_USD_per_yr=1e9) == pytest.approx(0.30)


def test_oversized_designs_are_told_apart(score):
    # Under V4's 4x cut-off these three all scored the gate share alone.
    five, twenty, forty = (total(score, cost_annualised_USD_per_yr=2000.0 / 0.8 * k) for k in (5, 20, 40))
    assert five > twenty > forty > 0.30


def test_equal_cost_ratios_cost_equal_points(score):
    # A ratio scale: doubling the cost always removes the same amount.
    a, b, c = (total(score, cost_annualised_USD_per_yr=x) for x in (4000.0, 8000.0, 16000.0))
    assert a - b == pytest.approx(b - c)


def test_cost_span_is_a_task_parameter(score):
    narrow = {**TASK, "cost_span": 10.0}
    assert total(score, task=narrow, cost_annualised_USD_per_yr=20000.0) == pytest.approx(0.30)
    assert total(score, cost_annualised_USD_per_yr=20000.0) > 0.30


def test_cost_bad_is_not_read(score):
    assert total(score, task={**TASK, "cost_bad": 2500.0}, cost_annualised_USD_per_yr=4000.0) == \
        pytest.approx(total(score, cost_annualised_USD_per_yr=4000.0))


def test_a_miss_earns_at_most_half_the_gate_share(score):
    near_miss = total(score, heat_duty_W=249999.0)
    assert 0.0 < near_miss < 0.15


def test_any_design_meeting_every_requirement_beats_any_miss(score):
    worst_pass = total(score, cost_annualised_USD_per_yr=1e12, num_warnings=10.0)
    best_miss = total(score, heat_duty_W=249999.999)
    assert worst_pass == pytest.approx(0.30)
    assert best_miss < worst_pass


def test_miss_credit_is_continuous_in_how_close_the_design_came(score):
    far, near = total(score, heat_duty_W=150000.0), total(score, heat_duty_W=240000.0)
    assert 0.0 < far < near < 0.15


def test_each_unmet_requirement_counts(score):
    one = total(score, dp_tube_Pa=15000.0)
    two = total(score, dp_tube_Pa=15000.0, dp_shell_Pa=15000.0)
    assert two < one < 0.15


def test_miss_share_is_a_task_parameter(score):
    v4_like = {**TASK, "miss_share": 1.0}
    assert total(score, task=v4_like, heat_duty_W=225000.0) == pytest.approx(0.30 * (0.9 + 1 + 1) / 3)


def test_each_warning_costs_a_tenth_of_the_quality_term(score):
    assert total(score, num_warnings=1.0) == pytest.approx(0.30 + 0.70 * 0.9)
    assert total(score, num_warnings=20.0) == pytest.approx(0.30)


def test_effectiveness_does_not_affect_the_score(score):
    assert total(score, effectiveness=0.1) == total(score, effectiveness=0.9)


def test_components_add_up_to_the_score(score):
    for m in ({}, {"heat_duty_W": 200000.0}, {"cost_annualised_USD_per_yr": 30000.0, "num_warnings": 2.0}):
        r = score.calculate_score(TASK, metrics(**m))
        assert r.components["gate_component"] + r.components["quality_component"] == pytest.approx(r.normalized_total)


@pytest.mark.parametrize("bad", [
    {"gate_share": 1.5}, {"miss_share": -0.1}, {"miss_share": 1.1}, {"cost_good": 0.0},
    {"cost_span": 1.0}, {"target_heat_duty": 0.0}, {"warning_penalty_per_warning": -1.0},
])
def test_invalid_task_configuration_is_rejected(score, bad):
    with pytest.raises(ValueError):
        score.calculate_score({**TASK, **bad}, metrics())


def test_deterministic(score):
    m = metrics(heat_duty_W=255000.0, cost_annualised_USD_per_yr=13579.0, num_warnings=1.0)
    first = score.calculate_score(TASK, m)
    for _ in range(5):
        again = score.calculate_score(TASK, m)
        assert again.normalized_total == first.normalized_total
        assert again.components == first.components
