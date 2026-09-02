#!/usr/bin/env python3
"""Inject seed data into the artifact template. Pure templating — does not
read from or publish to the live artifact itself (that's the Artifact tool,
run by Claude, not this script).

Also embeds the self-publish template: the page keeps a frozen JSON-escaped
copy of its own static source (everything except the seed JSON) in the
DOC_TEMPLATE_SRC constant, so a viewer's inline edit can regenerate a fresh
full document and call the `artifact` capability's publish() itself, without
a Claude session in the loop. This is a fixed-point substitution — see the
comment on DOC_TEMPLATE_SRC in command-center.html for why it has to be one.
Re-run this any time the template's HTML/CSS/JS changes; nothing else to
keep in sync by hand.

Usage: python3 build-artifact.py --template src/artifact/command-center.html \
    --seed data/current-seed.json --output data/command-center.built.html
"""
import argparse
import json

ap = argparse.ArgumentParser()
ap.add_argument("--template", required=True)
ap.add_argument("--seed", required=True)
ap.add_argument("--output", required=True)
args = ap.parse_args()

tpl = open(args.template).read()
seed = open(args.seed).read()
assert "__SEED_DATA__" in tpl, "template is missing the __SEED_DATA__ placeholder"

ASSIGN = 'var DOC_TEMPLATE_SRC = "__DOC_TEMPLATE_SRC__";'
assert tpl.count(ASSIGN) == 1, f"expected exactly one {ASSIGN!r}, found {tpl.count(ASSIGN)}"

assert tpl.count("__SEED_DATA__") == 1

# Order matters, and must match buildFullDocument()'s runtime logic exactly: substitute the
# seed FIRST, while its marker is still the only occurrence of that text — embedding the
# self-value (a copy of `tpl`, which still contains an unresolved seed marker) before this
# would give this same substitution a second, buried match to corrupt, baking today's seed
# permanently into every future generation's template.
seed_filled = tpl.replace("__SEED_DATA__", seed)
self_value = json.dumps(tpl).replace("</script", "<\\/script")
final = seed_filled.replace(ASSIGN, "var DOC_TEMPLATE_SRC = " + self_value + ";")

open(args.output, "w").write(final)
print(f"wrote {args.output}")
