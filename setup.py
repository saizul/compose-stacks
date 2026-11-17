"""Build hook that bundles the stack library into the wheel.

Contributors edit ``stacks/`` and ``templates/`` at the repository root. When a
wheel is built, both folders are copied into the ``compose_stacks`` package so
that ``pip install compose-stacks`` ships the full catalogue. Editable installs
read the folders straight from the repository instead.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py

ROOT = Path(__file__).parent.resolve()
BUNDLED = ("stacks", "templates")
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".env", ".DS_Store")


class BuildPyWithStacks(build_py):
    def run(self) -> None:
        super().run()
        for folder in BUNDLED:
            src = ROOT / folder
            if src.is_dir():
                dst = Path(self.build_lib) / "compose_stacks" / folder
                shutil.copytree(src, dst, dirs_exist_ok=True, ignore=IGNORE)


setup(cmdclass={"build_py": BuildPyWithStacks})
