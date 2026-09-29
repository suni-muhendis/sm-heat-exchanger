# Changelog

All notable changes are recorded here. The simulator and each score function
carry their own versions; a package release does not make results from
different simulator or score versions comparable.

## [Unreleased]

## [0.8.0] - 2026-09-29

First release as a package of its own, extracted with its history from
SM-Bench (`sunimuhendis.environments.heat_exchanger` up to `envs-v0.7.0`).
Simulator `v4` and scores `heat_exchanger_score_v1`–`v4` are unchanged: every
design SM-Bench has on record re-scores identically.

### Changed

- The package is `sm-heat-exchanger`, imported as `sm_heat_exchanger`, and
  builds on `sm-core`. It registers `heat_exchanger` in the
  `sm_core.environments` entry-point group.
- The benchmark prompt moved here as `sm_heat_exchanger.prompts`, and the
  design samplers as `sm_heat_exchanger.samplers` (the Latin-hypercube
  sampler needs the `samplers` extra).

[Unreleased]: https://github.com/suni-muhendis/sm-heat-exchanger/compare/v0.8.0...main
[0.8.0]: https://github.com/suni-muhendis/sm-heat-exchanger/releases/tag/v0.8.0
