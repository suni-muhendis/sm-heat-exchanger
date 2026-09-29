"""Install the built wheel into a clean venv and evaluate the example design there.

The wheel's sm-core dependency resolves from its pinned git tag, so this also
checks that the published core and this environment work together.

Usage: python scripts/check_wheel.py dist
"""
import json
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SMOKE = """
import json, sys
from pathlib import Path
import sm_heat_exchanger
from sm_core import make_env, list_environments
assert Path(sm_heat_exchanger.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
assert "heat_exchanger" in list_environments(), list_environments()
payload = json.loads(sys.stdin.read())
result = make_env("heat_exchanger").evaluate("wheel-smoke", payload["task"], "sample", payload["design"])
assert result.status == "success", result
assert (result.environment, result.simulator_version) == ("heat_exchanger", "v4"), result
assert "scipy" not in sys.modules
print("sm_heat_exchanger", sm_heat_exchanger.__version__, "score", result.score.normalized_total)
"""


def main() -> None:
    wheels = sorted(Path(sys.argv[1]).glob("sm_heat_exchanger-*.whl"))
    if len(wheels) != 1:
        raise SystemExit("expected exactly one sm_heat_exchanger wheel, found {}".format(wheels))
    payload = json.dumps({
        "task": json.loads((ROOT / "examples/task_001.json").read_text(encoding="utf-8")),
        "design": json.loads((ROOT / "examples/design_001.json").read_text(encoding="utf-8")),
    })
    with tempfile.TemporaryDirectory(prefix="sm-he-wheel-") as temp:
        env_dir = Path(temp) / "venv"
        venv.EnvBuilder(with_pip=True).create(env_dir)
        python = env_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        subprocess.run([str(python), "-m", "pip", "install", "-q", str(wheels[0].resolve())], check=True)
        subprocess.run([str(python), "-c", SMOKE], input=payload, text=True, check=True, cwd=temp)


if __name__ == "__main__":
    main()
