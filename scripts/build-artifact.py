#!/usr/bin/env python3
"""Inject seed data into the artifact template. Pure templating — does not
read from or publish to the live artifact itself (that's the Artifact tool,
run by Claude, not this script).

Usage: python3 build-artifact.py --template src/artifact/command-center.html \
    --seed data/current-seed.json --output data/command-center.built.html
"""
import argparse

ap = argparse.ArgumentParser()
ap.add_argument("--template", required=True)
ap.add_argument("--seed", required=True)
ap.add_argument("--output", required=True)
args = ap.parse_args()

tpl = open(args.template).read()
seed = open(args.seed).read()
assert "__SEED_DATA__" in tpl, "template is missing the __SEED_DATA__ placeholder"
open(args.output, "w").write(tpl.replace("__SEED_DATA__", seed))
print(f"wrote {args.output}")
