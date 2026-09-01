# Iterating on the design after go-live

The artifact template (`src/artifact/command-center.html`) is plain CSS/HTML/JS
— no build tooling. But once the artifact is live, it holds real state that
exists nowhere else: todos the 3:30pm cron added, meeting notes typed into
cards, accounts bob-sfdc-sync has refreshed. **Never rebuild from
`migrate-csm-tracker.py`'s output again after go-live** — that's today's
one-time snapshot and republishing it reverts everything since.

The correct loop, every time:

1. **Read the live artifact's current state.** Use the Artifact tool,
   `action: "read"`, on the Command Center URL. Extract the
   `<script type="application/json" id="seed-data">` block's contents into a
   local file (`data/current-seed.json` — already gitignored).
2. **Edit the template** — CSS custom properties at the top of
   `src/artifact/command-center.html` for anything visual, markup/JS below
   that for structure.
3. **Rebuild**: `python3 scripts/build-artifact.py --template
   src/artifact/command-center.html --seed data/current-seed.json --output
   data/command-center.built.html`
4. **Republish** with the Artifact tool, passing `url` set to the existing
   Command Center URL so it updates in place instead of creating a new
   artifact.
5. **Commit the template diff** (never `data/` — real customer data stays
   local, per `.gitignore`).

Read → edit → rebuild → republish, in that order. Never edit → rerun the
migration script → republish.
