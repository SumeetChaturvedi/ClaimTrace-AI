# Fictional Dataset — Ground Truth Reference (NOT for the agent to read)

Scenario: Additional reinforcement work at Pier P-42, Delhi Metro Viaduct Package DMV-7 (entirely fictional), following a design revision triggered by a supplementary geotechnical finding.

Sample investigation question to test the agent:
> "Investigate all available project records related to additional reinforcement work at Pier P-42 following a design revision."

## Core evidence chain (should be found as FACTS, correctly chained)
1. Original drawing Rev 0 (doc 01) — baseline design, no special provision.
2. Geotech report (doc 02, 02-May-2019) — soft clay pocket found, triggers redesign.
3. Revised drawing Rev 1 (doc 03, 01-Jun-2019) — references doc 02, adds ~2.8t reinforcement.
4. Site Instruction SI-088 (doc 04, 10-Jun-2019) — references doc 03, instructs the work.
5. Contractor acknowledgment (doc 05, 15-Jun-2019) — references SI-088.
6. Contractor cost/time notice (doc 06, 18-Jun-2019) — references SI-088, reserves claim rights.
7. Meeting minutes (doc 07, 25-Jun-2019) — confirms mobilization and claim intent.
8. Procurement/delivery (doc 12, 28-Jun-2019) — material delivered for the work.
9. DPR day 1 & 2 (docs 08, 09, 02–03 Jul 2019) — execution evidence.
10. Photo log (doc 11) — execution evidence, corroborates DPRs.
11. Measurement record (doc 10, 10-Jul-2019) — quantifies the work (2.75t), consistent with Rev 1 estimate.
12. Approval/certification letter (doc 17, 20-Jul-2019) — certifies physical completion, explicitly notes cost buildup is still outstanding.

## Deliberate contradiction
Doc 13 (internal email, 15-Apr-2019) — Contractor's own team privately observed the soil anomaly *before* the official geotech report (doc 02, 02-May-2019). This complicates the narrative that the design change was purely reactive to a client-side discovery — a good agent should surface this as CONTRADICTORY / worth flagging, not silently ignore it or silently treat it as another supporting fact.

## Deliberate gap
No detailed cost buildup / valuation document exists in this dataset (referenced as "outstanding" in doc 17, and implied as forthcoming in doc 06, but never produced). A correct agent response should explicitly state that **cost impact/quantum could not be established from the available records** — not estimate or infer a number.

## Deliberate irrelevant noise (agent should NOT cite these as relevant)
- Doc 14 — Pier P-15 shuttering delay (different pier entirely)
- Doc 15 — DPR for unrelated casting-yard work
- Doc 16 — Catering invoice

## Secondary test: notice timing
Doc 06 (contractor's cost/time notice) is dated 18-Jun-2019, 8 days after SI-088 (10-Jun-2019). The doc itself flags a fictional "28-day notice" contractual clause for calibration — a strong agent, if asked about notice compliance, should note the notice appears timely against that clause, without asserting this as a general legal conclusion (this is a fictional clause reference, not real contract law).

## How to use this file
Do NOT upload this file to the agent's document set — it is the answer key for evaluating whether the agent's dossier correctly identifies the chain, the contradiction, the gap, and ignores the noise.
