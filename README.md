# sm-heat-exchanger

A heat-exchanger evaluation environment for machine-generated engineering
designs. It takes a design as JSON, checks it, simulates it with real
engineering correlations, and returns a score in `[0, 1]`. It is one
environment of the Suni Muhendis benchmark and plugs into
[sm-core](https://github.com/suni-muhendis/sm-core).

```
design (JSON) → schema → design rules → simulation → score
```

- **Geometries:** shell-and-tube and concentric-tube.
- **Physics:** tube side with `ht` (Nusselt, ε-NTU) and `fluids` (friction);
  shell side hand-coded Kern / Bell-Delaware; TEMA and ASME mechanical
  checks; a cost model. Fluid properties are fixed (water), so evaluation is
  deterministic.
- **Versions:** simulator `v4`; scores `heat_exchanger_score_v1` … `v4`.
  Score V4 is a gated optimisation score and is what new tasks should use.

## Install

```bash
pip install "sm-heat-exchanger @ git+https://github.com/suni-muhendis/sm-heat-exchanger.git@v0.8.0"
```

This pulls in `sm-core` at the matching tag.

## Use

```python
from sm_core import make_env

env = make_env("heat_exchanger")
task = {
    "score_version": "heat_exchanger_score_v4",
    "target_heat_duty": 150000.0,
    "max_dp_tube": 50000.0,
    "max_dp_shell": 50000.0,
}
design = {
    "geometry_type": "shell_and_tube",
    "length": 3.0,
    "inner_tube_di": 0.016,
    "inner_tube_do": 0.019,
    "outer_shell_di": 0.35,
    "number_of_tubes": 60,
    "baffle_spacing": 0.3,
}
result = env.evaluate("task", task, "design", design)
result.status, result.score.normalized_total, result.metrics["heat_duty_W"]
```

A task can fix its operating point (`operating_conditions`), add further
operating points the same design must survive (`secondary_operating_points`),
and offer reference designs as witnesses to its own feasibility.
`env.audit_task(task)` checks a task for walls before any model is run
against it. [AGENTS.md](AGENTS.md) describes each of these in detail.

`sm_heat_exchanger.prompts.build_heat_exchanger_prompt(task)` builds the
benchmark prompt, and `sm_heat_exchanger.samplers` holds model-free design
samplers for baselines.

## History

This package was extracted, with its git history, from
[SM-Bench](https://github.com/suni-muhendis/sm-bench), where it shipped as
`sunimuhendis.environments.heat_exchanger` up to `envs-v0.7.0`. Every design
SM-Bench has on record re-scores identically with this package.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
