"""Evaluate the example design against the example task and print the result.

Usage: python scripts/run_heat_exchanger.py
"""
import json
from pathlib import Path

from sm_core import make_env

ROOT = Path(__file__).resolve().parents[1]


def main():
    task_params = json.loads((ROOT / "examples/task_001.json").read_text(encoding="utf-8"))
    design_params = json.loads((ROOT / "examples/design_001.json").read_text(encoding="utf-8"))

    env = make_env("heat_exchanger")
    result = env.evaluate("he_task_001", task_params, "valid_design_001", design_params)

    print("Status:", result.status)
    print("Environment: {} (simulator {}, score {})".format(
        result.environment, result.simulator_version, result.score_version))
    if result.status != "success":
        print("Error:", result.error_message)
        return

    metrics = result.metrics
    print("Heat duty:           {:.2f} W".format(metrics.get("heat_duty_W", 0)))
    print("Tube-side dP:        {:.2f} Pa".format(metrics.get("dp_tube_Pa", 0)))
    print("Shell-side dP:       {:.2f} Pa".format(metrics.get("dp_shell_Pa", 0)))
    print("Area:                {:.4f} m^2".format(metrics.get("area_m2", 0)))
    print("Effectiveness:       {:.2%}".format(metrics.get("effectiveness", 0)))
    print("Annualised cost:     {:.2f} USD/yr".format(metrics.get("cost_annualised_USD_per_yr", 0)))
    print("Design warnings:     {}".format(int(metrics.get("num_warnings", 0))))
    print("Score components:")
    for key, value in result.score.components.items():
        print("  {}: {:.4f}".format(key, value))
    print("Score: {:.4f} / 1.0000".format(result.score.normalized_total))


if __name__ == "__main__":
    main()
