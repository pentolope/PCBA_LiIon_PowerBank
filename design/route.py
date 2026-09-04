"""Routing: the toolkit owns the search; this board declares it.

The candidate loop that lived here - staging, invoking the router,
tidying, adopting, measuring, recording - is the toolkit's `run.py
route`, driven by the `routing.search` and `routing.transforms` blocks
of `board/manifest.json`, which mirror the constants this module
carried: the reserved nets, the offered pours, the attempt matrix, the
router options and the acceptance that also refuses a via on a
solder-mask opening. What stays board-side is the placed board itself:
`layout.write()` regenerates it, and the toolkit routes it and adopts
only a candidate its declared acceptance passes.
"""
from __future__ import annotations

import os
import subprocess
import sys

from . import layout


def run():
    layout.write()
    proc = subprocess.run(
        [sys.executable,
         os.path.join(layout.REPO_ROOT, "tooling",
                      "PCBA_AutoDesignAndTest", "run.py"),
         "route", os.path.join("board", "manifest.json"), "--adopt"],
        cwd=layout.REPO_ROOT, check=False)
    sys.exit(proc.returncode)


if __name__ == "__main__":
    run()
