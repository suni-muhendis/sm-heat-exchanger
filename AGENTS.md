# AGENTS.md

Guidance for AI coding agents (Claude Code, Codex, and others) working in this
repository.

## What this is

`sm-heat-exchanger` (import `sm_heat_exchanger`) is the heat-exchanger
evaluation environment of the Suni Muhendis benchmark. It implements the
`sm-core` contract (schema, design-rule check, simulator, score) and registers
itself as `heat_exchanger` in the `sm_core.environments` entry-point group, so
`sm_core.make_env("heat_exchanger")` finds it once it is installed.

The benchmark harness, recorded results, dashboard and site live in
[SM-Bench](https://github.com/suni-muhendis/sm-bench); the shared contract in
[sm-core](https://github.com/suni-muhendis/sm-core).

## Commands

- Setup: `python3.12 -m venv .venv`, activate it,
  `python -m pip install -e ".[dev,samplers]"`.
- Tests: `python -m pytest tests -q`.
- Demo: `python scripts/run_heat_exchanger.py`.
- Wheel check: `python -m build` then `python scripts/check_wheel.py dist`.

## Rules

- **Versions are real.** The simulator is `HeatExchangerSimulator.VERSION`;
  each score function has its own `VERSION` (`heat_exchanger_score_v1…v5`).
  Any change that can move a number needs a new simulator or score version,
  and results from different versions are never pooled.
- **Re-score before releasing.** Every design SM-Bench has on record must
  re-score identically unless the version changed on purpose.
- **Determinism is a hard requirement.** Identical input gives identical
  output; fluid properties are fixed and nothing in the evaluation path is
  random.
- Prefer "score" over "reward" in new code and documentation.
- Consumers pin tags (`@v0.9.0`), never branches. Record user-visible changes
  in `CHANGELOG.md`.

## Layout

- `src/sm_heat_exchanger/schema.py`: the design schema (Pydantic, extra fields forbidden).
- `drc.py`: design-rule checks. `geometry.py`: shared geometry helpers.
- `simulator.py`: the physics. `score.py`: score V1–V5 and `SCORE_REGISTRY`.
- `env.py`: `HeatExchangerEnv`, operating conditions, secondary points, audit hooks.
- `prompts.py`: `build_heat_exchanger_prompt`, the benchmark prompt.
- `samplers/`: random, heuristic and Latin-hypercube design samplers.
- `tests/fixtures/`: copies of SM-Bench task definitions and calibration
  records that the physics tests pin. The originals live in SM-Bench.
- `docs/simulator_v3_physics_audit.md`: the audit behind simulator V4.

## Operating conditions belong to the task (`prepare_simulation_inputs`)

A third environment-agnostic hook, alongside `evaluate()` and `audit_task()`.
`BaseEnvironment.prepare_simulation_inputs(design_params, task_params)` builds
the dict handed to `simulator.simulate()`. Its default returns the design
unchanged, so every other environment is untouched.

**Why it exists.** Stages 1 and 2 must see the design exactly as the model
wrote it, so the operating point cannot travel in the design dict. But a
heat-exchanger task is not just a set of targets — it is a duty specification:
which streams, how much of them, how hot, how dirty, how strong the vessel.
None of that is a design decision, so none of it belongs in the schema; all of
it changes the physics, so a task that cannot set it can only ever pose one
problem. Before this hook the operating point was hardcoded at 2.5 kg/s of
water each side at 80/20 °C, and every task ever written was that same problem
with different targets.

`HeatExchangerEnv` overrides it and reads `task_params["operating_conditions"]`,
a whitelist of nine keys — `m_dot_hot/cold`, `T_hot_in/cold_in`, `k_wall`,
`R_fi`, `R_fo`, `P_design`, `allowable_stress`. Three properties are pinned by
`tests/test_operating_conditions.py`:

- **A task without the block behaves exactly as before**, so every existing
  task and every recorded run stays valid.
- **The task wins over the design.** The schema forbids extra fields so a
  benchmarked design cannot carry these keys, but a design handed straight to
  the environment could — and a design that could restate its own flow rate
  would be answering an easier question than the one it was set.
- **A malformed block raises rather than scoring zero.** `prepare_simulation_inputs`
  is called *outside* `evaluate()`'s crash handler on purpose: everything
  inside it is the design's failure, while a typo like `m_dot_hto` is the
  experimenter's, and silently reverting to 2.5 kg/s would record it as every
  model failing to design.

`analyse_physics` reads the same resolved point, so the ε ceiling, the duty at
which the F warning becomes unavoidable, and the nozzle share of the pressure
budget are all computed for the task actually being audited — and are echoed
back in `AuditReport.physics["operating_conditions"]`.

**Two things this makes possible.** A *family* of tasks rather than one, which
is what separates measuring design skill from measuring memorisation of a
single instance. And simulating one design at more than one operating point,
which is how a turndown requirement would be expressed.

## Multi-point evaluation and witnessed feasibility

Two further hooks, both environment-agnostic and both defaulting to the previous
behaviour, so every existing task and every recorded run is unaffected.

**`secondary_simulations(design_params, task_params)`** returns
`(label, simulator_inputs)` pairs — further conditions the *same* design must
survive. `evaluate()` runs each after a successful primary simulation, adds the
warnings found to `num_warnings`, records each point's count as
`<label>_num_warnings`, prefixes the merged warning list with `[<label>]`, and
stores the full per-point metrics in `raw_data["secondary_points"]`. The
requirements stay a single-point gate; only quality spans the range.

`HeatExchangerEnv` reads `task_params["secondary_operating_points"]`, a list of
`{"name": ..., "operating_conditions": {...}}`. Each point's conditions are
applied over the task's primary point, so a turndown case names only the flows
it changes. Like `prepare_simulation_inputs`, this is called *outside*
`evaluate()`'s crash handler: a malformed point is the experimenter's error and
raises.

**`reference_designs(task_params)`** returns designs the task offers as
*witnesses* to its own feasibility; the default reads
`task_params["reference_designs"]`. The audit evaluates them alongside the
sample and raises a CRITICAL finding for any that fails to meet the task's own
requirements. This exists because sampling can show a score is reachable and can
never show that it is not, so a ceiling measured by sampling is a lower bound —
`heat_exchanger_hard_v4`'s was reported as 0.593 against a true 1.000 until a
witness was added. A task claiming a perfect score is attainable should exhibit
a design that attains it.

**`sample_designs` now takes `task_params`** (optional, positional-compatible)
and draws three designs in ten in *velocity coordinates* — picking a target tube
and nozzle velocity and deriving the tube count and bore from the task's flows,
instead of choosing counts and bores independently of it. Sampling in the wrong
coordinates does not bias the audit, it blinds it: every limit that is a
velocity window was invisible to the old sampler, which is why it reported no
warning-free design for `hard_v4` where a structured grid finds 566. This is an
audit-only path — evaluation is untouched, and all 110 recorded `hard_v3` runs
re-score bit for bit.

## Heat exchanger specifics
- **Schema has seven required fields** (`geometry_type`, `length`, `inner_tube_di/do`, `outer_shell_di`, `number_of_tubes`, `baffle_spacing`) plus the seven optional levers described below. The simulator reads further params via `dict.get(...)` defaults — fouling resistances and fluid operating conditions (`m_dot_hot/cold`, `T_hot_in/cold_in`, …) — but since the schema forbids extra fields, **those are not reachable from a benchmarked design**; they are set by the task (`operating_conditions`) or apply only when calling the simulator directly. Fluid thermophysical properties are otherwise **hardcoded** (water), which keeps evaluation deterministic.
- **Simulator (`simulator.py`) library boundary:** tube/annulus side uses `ht` (Nusselt, ε-NTU) and `fluids` (friction factor); **shell side is hand-coded Kern/Bell-Delaware** because no library covers cross-flow over tube bundles. It also computes a cost model and mechanical/TEMA limit checks that produce `num_warnings`. Any metric coming out `NaN`/`Inf` is treated as a simulation failure.
- **Simulator is at `VERSION = "v4"`.** V4 corrected three defects the physics audit found, and **its numbers differ from V3 — results from the two must never be pooled** (~15% of designs get a different warning count). The corrections: unsupported span now follows the TEMA table keyed by tube OD instead of one flat 1.5 m; the ASME wall-thickness check uses UG-27's `t = P·R/(S·E − 0.6·P)` (the previous form *added* where the code subtracts, understating thickness by ~11% at 200 bar) and honours a joint efficiency; and `drc.py` now reads the design's own `tube_passes` / `pitch_ratio` / `pitch_type` rather than assuming the defaults, so DRC and the simulator can no longer disagree about the same design.
- **Correlation limits are reported, never charged to the design.** Kern's shell-side correlations are only valid for 2e3 < Re < 1e6, and its crossflow area assumes a bundle spanning the shell. When a design falls outside either, the simulator sets `shell_correlation_in_range` / `bundle_fill_fraction` and appends to `raw_data["fidelity_notes"]` — deliberately **not** to `warnings`, because the score penalises warnings and charging a design for the referee's blind spots would be scoring our own ignorance.
- **Score V4 is a gated optimisation score, and is what new tasks should use.** V1-V3 spread most of their weight across the requirements themselves, so a design earned ~85% of the raw score the instant it met the duty target and both pressure limits; measured across sixteen parameter settings the reward for reaching any feasible design never moved off 0.439, whatever the targets were. V4 makes the three requirements a **gate** worth `gate_share` (0.30) — missing one scales that share by how close you came, so the boundary is continuous — and puts the remaining 0.70 on annualised cost and warning-freedom, which can always be improved. **V4 deliberately does not score effectiveness:** with flows and inlet temperatures fixed, `Q_max` is constant, so effectiveness is exactly `heat_duty / 627300` (correlation with duty measured at 1.0000000000 over 4,353 designs). Every earlier version rewards both, which pays twice for one quantity.
- **The schema has seven required fields and seven optional ones.** Optional on purpose: `tube_passes`, `pitch_ratio`, `pitch_type`, `baffle_cut`, `D_nozzle_hot/cold`, `material`, each defaulting to the previous behaviour so older designs re-score identically. Making them required would raise the cost of producing *any* valid design, which is the opposite of what the benchmark measures. An absent key and an explicit `null` both mean "not chosen" (`HeatExchangerSimulator._opt`).
- **Nozzle bore is a real lever, and the exploit is closed.** Before, nozzle loss was a fixed tax eating 66.7% of hard_v2's pressure budget; exposing the bore naively would have been a free win, since a 2 m nozzle on a 0.48 m shell was accepted, cut ΔP by 87%, and cost nothing. Now the bore is bounded by DRC (35% of shell diameter for shell-and-tube, the pipe itself for concentric), it adds mass and cost, and a bore below `MIN_NOZZLE_VELOCITY` raises an oversized-nozzle warning. The designable window is roughly 26-57 mm at these flows.
- **Benchmark Score (`score.py`) is multi-objective** with weights pulled from the task config: `w_heat`, `w_cost`, `w_eff`, `w_drop_tube`, `w_drop_shell` (defaults 0.4/0.3/0.2/0.05/0.05). Score is the weighted sum of component sub-scores, normalized by total weight, then multiplied by a **warnings penalty (−10% per warning)**. It reads metrics with **V1↔V2 name fallbacks** (e.g. `heat_duty_W` else `heat_duty`), so both simulator generations work.
- **Two different pressure-drop thresholds exist on purpose:** the simulator's `MAX_DP_TUBE/SHELL` (10 kPa) only drive *warnings*; the score's `max_dp_tube/shell` from the task config (50 kPa in `task_001.json`) drive the *score*. Don't conflate them.

## Determinism is a hard requirement
Tests assert identical output for identical input (`test_heat_exchanger_smoke.py`) because the evaluation score must be stable and reproducible. Preserve determinism when touching the simulator (hence hardcoded fluid props, no randomness in the eval path).

