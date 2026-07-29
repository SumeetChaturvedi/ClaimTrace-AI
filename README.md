# Construction Claims Evidence Investigator — Pre-Claude-Code Scaffold

This folder is prep work done ahead of opening Claude Code, per the V0 plan
(`claims-evidence-investigator-v0-plan.md`).

## What's already here
- `data/fictional_dataset/` — 17 fictional test documents (Pier P-42 reinforcement
  scenario) + `00_GROUND_TRUTH_README.md` (the answer key — do NOT feed this file
  to the agent, it's for evaluating the agent's output).
- `backend/app/db/schema.sql` — initial Postgres/pgvector schema matching Part F
  of the plan.
- `backend/requirements.txt` — starter Python dependency list.
- `backend/app/{agent,ingestion,api,db}` and `frontend/` — empty folders matching
  the intended repo structure.

## What's NOT done yet (deliberately left for Claude Code)
- No actual application code.
- No Postgres instance running yet.
- No Agent SDK integration.
- No frontend scaffolding (Next.js not yet initialized).

## When you're ready to start Claude Code
1. Install Postgres locally (with pgvector) if you haven't — you can do this now,
   it's free and doesn't depend on any subscription.
2. Run `psql -f backend/app/db/schema.sql` against a local database once Postgres
   is set up.
3. Open this folder in Claude Code and point it at both this README and the full
   plan document. Start with Milestone 0 (ingestion pipeline) only.
