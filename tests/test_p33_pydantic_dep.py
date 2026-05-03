"""P33-TS00: Dependency metadata test.

Pydantic must be a *direct* dependency, not only transitively pulled in by
openai. Schema-driven config relies on it; declaring it directly makes the
contract explicit and survives a future openai dep change.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"


def test_pydantic_declared_in_pyproject() -> None:
    data = tomllib.loads(PYPROJECT.read_text())
    deps = data["project"]["dependencies"]
    matches = [d for d in deps if d.lower().startswith("pydantic")]
    assert matches, (
        f"Expected a direct 'pydantic' entry in [project.dependencies]; found only: {deps}"
    )
    spec = matches[0].lower().replace(" ", "")
    assert ">=2.12.5" in spec and "<3" in spec, (
        f"Expected pydantic>=2.12.5,<3 (got {matches[0]!r}); P33 locks Pydantic v2.x, not v3."
    )


def test_pydantic_resolves_to_v2() -> None:
    import pydantic

    major = int(pydantic.VERSION.split(".")[0])
    assert major == 2, f"Resolved Pydantic major version is {pydantic.VERSION}; P33 requires v2.x."
    assert sys.version_info >= (3, 11)
