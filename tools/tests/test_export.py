#!/usr/bin/env python3
"""Wrapper: runs the node test of app/dashboard-mockup/js/export.js (official brief + zip). Prints SKIP and passes when node is missing."""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def main():
    node = shutil.which("node")
    if not node:
        print("SKIP  node not found, export test not run")
        return 0
    r = subprocess.run([node, os.path.join(HERE, "export_node_test.js")], cwd=ROOT, capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
