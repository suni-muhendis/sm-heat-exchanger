"""sm_heat_exchanger — heat-exchanger evaluation environment on sm-core.

Registered as ``heat_exchanger`` in the ``sm_core.environments`` entry-point
group, so once this package is installed:

    from sm_core import make_env

    env = make_env("heat_exchanger")
    result = env.evaluate(task_id, task_params, design_id, design)
"""

__version__ = "0.8.0"


def make_env(**kwargs):
    """Build the heat-exchanger environment; registered as ``heat_exchanger``.

    ``score_version`` sets the default score; a task that names its own
    ``score_version`` is scored with that one instead. The imports are lazy so
    that discovering the environment does not import its physics libraries.
    """
    from .env import HeatExchangerEnv
    from .score import get_score_function
    from .simulator import HeatExchangerSimulator

    score_version = kwargs.get("score_version", "heat_exchanger_score_v1")
    return HeatExchangerEnv(HeatExchangerSimulator(), get_score_function(score_version))
