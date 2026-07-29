# Construction Claims Evidence Investigator — V0 Planning Document

---

## PART A — Problem Definition

**1–2. Restated problem, verified vs. assumed**

Verified (from your father's firsthand account, treated as anecdote not data): on a long-running infrastructure project, historical records became hard to retrieve, and this reportedly weakened the company's ability to substantiate a claim. That's it. Everything else — the ₹170 crore figure, the ₹60–70 crore recoverable amount, which document types were missing, why they were missing (storage? metadata? staff turnover? no one indexed anything?) — is unverified. You've correctly flagged this, which is a good sign; most first-time founders skip this step entirely.

**3. Critique of the hypothesis**

The hypothesis ("records get fragmented across systems and people over years, and reconstructing evidence becomes hard") is *plausible* but generic — it's true of almost any long-duration paper-heavy industry (litigation discovery, insurance claims, medical malpractice, M&A due diligence). That's not a flaw, but it means you have zero evidence yet that this specific pain is (a) acute enough that people would pay to fix it, (b) not already adequately solved by existing document management systems or the claims consultants who already do this manually, or (c) something your father's company would actually let an AI tool near, given claims data is commercially and legally sensitive.

The single biggest untested assumption: **that the bottleneck was retrieval/reconstruction, not something upstream** (e.g., no one ever wrote the site instruction down in the first place, or notices were filed late per contract, which no amount of search technology fixes). If the root cause was "the paperwork was never created" rather than "the paperwork existed but was hard to find," your product doesn't help. You don't know which it was yet.

**4. Is this a reasonable V0 to build before talking to domain experts?**

Yes — with a caveat. Building a fictional-dataset prototype *before* talking to your father's colleagues is reasonable and actually smart, because it lets you show something concrete instead of asking abstract questions. But you should treat V0 as a **conversation-starter artifact**, not a product decision. Don't sink more than ~3-4 weeks into it before getting real feedback from someone who has actually run a claim (Part I below).

**5. What V0 is and is not**

V0 **is**: a working demo, using synthetic documents, that shows an AI agent can take a natural-language investigation question, search a small messy document set, follow cross-references, build a chronology, and produce a cited, fact/inference/gap-labeled dossier.

V0 **is not**: a claims-workflow product, a legal tool, multi-user, multi-project at scale, integrated with real document management systems, or validated against real users. It proves *retrieval-and-reasoning-with-citation-discipline* works technically. It does not prove market fit.

---

## PART B — Domain Assumptions

**6–7. Assumptions, classified**

| Assumption | Classification |
|---|---|
| Claims rely on documentary evidence spread across many document types | Safe for fictional prototype |
| A "design revision → site instruction → execution → measurement → cost" chain is a plausible evidence pattern | Safe for fictional prototype, but not universal — mark as *one example pattern*, not *the* pattern |
| Every claim needs a fixed checklist of ~10 document types | **Dangerous to hard-code** |
| Contractual notice periods/deadlines determine claim validity | Requires validation — this is jurisdiction- and contract-specific (FIDIC vs. Indian EPC vs. NHAI/DMRC standard contracts differ) and is a legal question, not a document-retrieval question |
| "Missing records = weaker claim" is universally true | Requires validation — sometimes a claim is denied for contractual/legal reasons even with perfect records |
| Document relationships (drawing → instruction → correspondence) can be inferred from references/IDs/dates in text | Safe for fictional prototype (it's just entity linking) |
| The agent can determine what evidence *should* exist for a given claim type | **Dangerous to hard-code** — this requires domain expert-authored checklists, not LLM guessing |

**8. Building without knowing the complete workflow**

Design the agent as a **general-purpose evidence investigator with construction vocabulary**, not a construction-claims-rules-engine. It should never assert "this claim requires X, Y, Z documents" as ground truth — only "based on the investigation question, plausible related evidence would include X, Y, Z; here's what was found and what wasn't." Domain-specific checklists (notice periods, required document types per claim category, jurisdiction rules) become a *separate, later, expert-authored config layer* — not something the LLM infers. This is the right instinct you already had in Section 6; keep it.

---

## PART C — Final V0 User Flow

**9. Critique of the 22-step flow**

It's fundamentally sound but over-specified for V0 — several steps you've listed as separate steps are really sub-behaviors of a single agentic reasoning loop (steps 11–19 are essentially "the agent iterates using tools until it decides it's done," not 9 discrete pipeline stages). Also, step-level determinism isn't marked, which matters a lot for cost, reliability, and debuggability.

**10–12. Recommended simplified V0 flow**

1. **Create project** (deterministic — DB row)
2. **Upload documents** (deterministic — file storage)
3. **Extract text + page boundaries** (deterministic — PyMuPDF/pdfplumber)
4. **Classify document type + extract metadata** (AI-powered, single-shot per doc, not agentic — one LLM call per document, structured JSON output: doc type, date, referenced IDs, parties)
5. **Chunk + embed + index** (deterministic pipeline, AI-powered embeddings)
6. **User asks investigation question** (human input)
7. **Agent loop** (agent-controlled): plan → search → read → follow references → search again → track facts/contradictions/gaps → decide when to stop. This single loop *is* your old steps 9–20.
8. **Generate dossier** (AI-powered, but templated/structured output, not free-form)
9. **Human reviews dossier** (human-reviewed — this step must exist; V0 output is a draft for a person, never a final artifact)

Steps to drop/defer from your original list: separate "verify citation" as its own agent step (fold into deterministic post-processing — see Part D §19), and treat "identify facts vs inferences" not as a distinct step but as a labeling requirement enforced on every claim the agent makes throughout.

---

## PART D — Agent Architecture

**13–14. Architecture choice**

Use the **Claude Agent SDK (Python package)** as the runtime, called from your own control logic — not LangGraph, not a hand-rolled state machine with many node types, and not a raw HTTP client hitting the API directly. Justification: your investigation task is a single reasoning agent making tool calls in a loop with a clear stopping condition; the Agent SDK gives you that loop, tool-calling, and context management out of the box (it's the same engine behind Claude Code), so you write your custom tools (search, read, etc.) and a thin wrapper around stopping conditions rather than reinventing the loop itself. LangGraph adds a graph-orchestration layer that earns its complexity with multiple specialized agents or branching multi-actor workflows — you explicitly don't want fake multi-agent theater, so skip it.

Billing-wise, this choice also matters: Agent SDK usage (including `claude -p` and SDK calls) draws from a monthly credit included with Pro/Max/Team subscriptions, separate from your interactive Claude Code/chat usage, at no extra cost beyond your $20/month plan — rather than requiring a separate Console API key billed per token. That's sized for individual experimentation, which is exactly V0's scale. (This is a recent billing mechanic as of mid-2026 — worth a quick check of Anthropic's Help Center for the current terms right before you start building, in case anything's shifted.)

**15. Agent state**

- Investigation question (fixed)
- Investigation plan (mutable — the agent's evolving list of sub-questions)
- Tool call history + results (append-only log — this *is* your investigation trail)
- Working evidence set: facts (with citations), inferences, contradictions, gaps
- Step counter / token counter

**16. Stopping conditions**

- Agent explicitly signals "investigation complete" via a `finalize_investigation` tool call
- Hard cap on tool calls (e.g., 25) to prevent runaway loops/cost — trip this and force a "partial investigation, here's what I found" summary
- No new relevant documents found in last 2 search iterations

**17. Failure/retry behavior**

- Tool call errors (bad doc ID, empty search): return a structured error to the model, let it adapt — don't crash the loop
- If the model produces a citation to a document/page that doesn't exist, reject it at the deterministic verification layer and force a correction turn
- Cap retries per tool at 2 before the agent is told to move on

**18. Tools — evaluated**

| Tool | Needed in V0? | Input | Output | Logic |
|---|---|---|---|---|
| `search_documents(query)` | Yes | text query | ranked chunks w/ doc ID, page | Deterministic (pgvector similarity) + optional keyword fallback |
| `read_document(doc_id)` | Yes | doc ID | full extracted text | Deterministic |
| `get_document_metadata(doc_id)` | Yes | doc ID | type, date, referenced IDs | Deterministic (pre-extracted in step 4) |
| `find_related_documents(doc_id)` | Yes | doc ID | docs sharing referenced IDs/entities | Deterministic (metadata join, not LLM) |
| `compare_documents(id_a, id_b)` | Merge into agent reasoning, not a separate tool | — | — | The agent can just read both via `read_document` and reason itself — a dedicated tool adds little |
| `extract_timeline_events()` | Fold into dossier generation, not a live tool | — | — | Do this once at the end from the accumulated fact set, deterministically sorted by date |
| `search_for_contradictions()` | Drop as separate tool | — | — | This is a reasoning behavior the agent should do while reading, not a callable function |
| `identify_evidence_gaps()` | Drop as separate tool | — | — | Also a reasoning behavior, not a tool |
| `verify_citation(doc_id, page, quote)` | Yes, but deterministic and run automatically, not agent-invoked | claim + citation | boolean match | Deterministic string/page match against source text — this is your hallucination guard, see §19–20 |
| `generate_evidence_dossier()` | Yes | accumulated state | structured dossier | AI-powered, single final call, structured output |

So: 6 real tools, not 10. Fewer tools = more reliable agent behavior at this scale.

**19. Citation verification**

After the agent claims a fact with a citation (doc ID + page + quoted excerpt), run a deterministic check: does that excerpt actually appear (or closely match) in the extracted text of that doc/page? If not, flag it and either force the agent to correct it or mark it "unverified — citation could not be confirmed" in the final dossier. Never trust the model's citation at face value — this is the single highest-leverage integrity control in the whole system.

**20. Minimizing hallucination**

- Every fact-bearing tool result includes doc ID + page, forced into the model's context so it always has exact provenance available
- System prompt requires labeling every claim as FACT/INFERENCE/CONTRADICTORY/UNVERIFIED per your Part 8 model
- Deterministic citation verification (above) as a backstop, not a suggestion
- Dossier generation step explicitly instructed to omit any claim without a verifiable citation, converting it to "not found in available records" instead

---

## PART E — Fictional Dataset

**21–27. Scenario design**

**Scenario**: Contractor performs additional reinforcement work at Pier P-42 on a fictional metro viaduct project after a design revision, following soil condition findings.

**~18 documents:**
1. Original structural drawing (P-42, Rev 0)
2. Geotechnical report noting soil anomaly near P-42 (the trigger)
3. Revised structural drawing (P-42, Rev 1) — references the geotech report and Rev 0
4. Site instruction (SI-088) — issued by Engineer, references Rev 1 drawing, instructs additional reinforcement
5. Contractor's acknowledgment letter (references SI-088)
6. Contractor's cost/time impact notice (references SI-088 — **this is your "notice" document, deliberately time-stamped close to a contractual deadline** to test whether the agent notices timing)
7. Meeting minutes discussing the change (references SI-088, mentions P-42)
8. Daily Progress Report, day 1 of extra rebar work (mentions P-42, no explicit SI-088 reference — tests entity linking without explicit IDs)
9. Daily Progress Report, day 2 (same)
10. Measurement record / MB extract for the additional rebar (quantities, references DPR dates)
11. Site photographs log (references DPR dates, P-42) — text log describing photos, not actual images, to keep V0 simple
12. Procurement/delivery record for the extra rebar tonnage
13. **Contradictory document**: an internal email suggesting the soil anomaly was already known before the "trigger" geotech report — undermines the contractor's timeline narrative
14–16. **Irrelevant noise**: correspondence about Pier P-15 (unrelated), a DPR about a different work item, an unrelated invoice
17. **Deliberately missing category**: no cost buildup/valuation document exists in the dataset — this tests whether the agent correctly reports "cost impact could not be established from available records" rather than inventing a number
18. Approval/certification letter closing out the variation, referencing SI-088 and the measurement record

Ground truth to evaluate against: which facts are directly supported (should be ~8-10 clear ones), the one deliberate contradiction (item 13), the one deliberate gap (cost documentation), and the 3 irrelevant documents the agent should *not* cite as relevant.

Generate these yourself with Claude's help as plain fictional text (not modeled on any real DMRC document), explicitly avoiding real project names, real contract numbers, or anything traceable to your father's employer.

---

## PART F — Technical Architecture

**28–31. Stack assessment**

| Component | Need in V0? | Free option | Later option | V0 cost | Outgrow when |
|---|---|---|---|---|---|
| Next.js + TS + Tailwind | Yes | Free, self-hosted local | Vercel hosting | $0 | Public deployment |
| FastAPI | Yes | Free | — | $0 | — |
| PostgreSQL (local) | Yes | Free (local install/Docker) | Managed Postgres (Supabase/RDS) | $0 | Multi-user/cloud deployment |
| pgvector | Yes | Free extension | Managed vector DB (Pinecone) | $0 | Never, honestly — pgvector scales fine to hundreds of thousands of chunks |
| Local filesystem storage | Yes | Free | S3/blob storage | $0 | Cloud deployment |
| PyMuPDF/pdfplumber | Yes | Free | — | $0 | — |
| Tesseract OCR | Only if you have scanned docs | Free | Azure Document Intelligence | $0 | If dataset needs OCR — for fictional typed docs, skip entirely |
| Embeddings | Yes | Local model (e.g., `sentence-transformers/all-MiniLM-L6-v2`) — free, runs on CPU | OpenAI/Voyage/Anthropic embeddings API | $0 | If retrieval quality on real messy docs proves inadequate |
| Agent orchestration | Yes | Custom Python loop, free | — | $0 | — |
| Claude model calls (agent loop, classification, dossier) | Yes | Claude Agent SDK, billed against Pro subscription's included monthly credit | Console API key, pay-as-you-go | $0 marginal (covered by your $20/month Pro plan) | If sustained usage ever exceeds the included Agent SDK credit |
| Deployment | No (local only) | Free | Any cloud | $0 | When you want to demo remotely |

**32. Database schema (core tables)**

```
projects(id, name, created_at)
documents(id, project_id, filename, doc_type, doc_date, referenced_ids[], uploaded_at, raw_text_path)
document_chunks(id, document_id, page_number, chunk_text, embedding vector)
investigations(id, project_id, question, status, created_at)
investigation_steps(id, investigation_id, step_number, tool_called, tool_input, tool_output, agent_reasoning)
dossier_findings(id, investigation_id, finding_type[FACT/INFERENCE/CONTRADICTION/GAP/UNVERIFIED], text, source_document_id, source_page, source_excerpt, verified boolean)
```

**33. Folder structure**

```
/backend
  /app
    /agent        (Agent SDK wrapper, tools, prompts, stopping-condition logic)
    /ingestion     (extraction, chunking, embedding)
    /api           (FastAPI routes)
    /db            (models, migrations)
/frontend
  /app             (Next.js routes: project, upload, investigate, dossier)
  /components
/data
  /fictional_dataset   (your 18 test documents)
```

**34. End-to-end data flow**

Upload → extract text/pages → classify + extract metadata (LLM, structured) → chunk + embed → store in Postgres/pgvector → user submits question → agent loop (search/read/follow-refs, tool calls logged) → deterministic citation verification → dossier generation → human review in UI.

---

## PART G — Cost Analysis

**35–37. Expenses**

Mandatory model usage: document classification (~18 small calls) + agent investigation loop (~15-25 tool-use turns per investigation) + dossier generation (1 call). By routing these through the **Claude Agent SDK** rather than a Console API key, this usage is billed against the monthly Agent SDK credit included with your Pro subscription — not a separate per-token charge. Everything else in your stack (Postgres, pgvector, local filesystem, PyMuPDF, local embeddings) is free at V0 scale regardless.

- **Minimum possible V0 cost**: $0 marginal — covered entirely by your existing $20/month Pro subscription, assuming your test-investigation volume stays within the included Agent SDK credit (very likely at V0 scale — a few dozen runs against 18 documents).
- **Recommended V0 cost**: still just the $20/month Pro plan you're already paying for. No separate budget needed unless you start running the agent constantly for extended stretches.
- **Future cost drivers**: if you scale usage well beyond individual experimentation (e.g., many users, continuous automation, production deployment), you'd move to a Console API key with standard pay-as-you-go billing — plus the usual production costs: cloud hosting, managed DB, OCR on real scanned documents, multi-user concurrency.

**38. Subscription vs. Claude Code vs. Agent SDK vs. API billing — clarified**

- **Claude.ai chat + Claude Code (interactive)**: covered by your $20/month Pro plan, shared usage pool with session/weekly limits. This is what you use to *write* the application.
- **Claude Agent SDK (your app's runtime)**: also covered by your Pro plan, via a *separate* monthly credit specifically carved out for SDK/`claude -p`/programmatic use, at no additional charge. This is what your app uses to *run* the agent.
- **Console API key**: a separate account with its own pay-as-you-go billing, only needed if you outgrow the Agent SDK credit or move to production-scale automation. Not required for V0.

Net effect: for this prototype, you genuinely don't need anything beyond the $20/month Pro subscription you already want. Worth reconfirming current terms at Anthropic's Help Center before you start, since this billing model is only a few weeks old as of writing and could still evolve.

---

## PART H — Build Roadmap

**39–43. Milestones**

**Milestone 0 — Ingestion pipeline only** (no agent yet)
- Build: upload → extract → classify → chunk → embed → store
- Test: can you manually query pgvector and get sensible chunk matches for your 18 fictional docs?
- Failure modes: bad PDF extraction (check text quality first), garbage embeddings
- Done when: all 18 docs ingested, metadata correctly extracted for ≥90%

**Milestone 1 — Single-tool agent (search + read only)**
- Build: minimal agent loop with just `search_documents` + `read_document`, no dossier yet, just print its reasoning
- Test: give it the P-42 question, see if it finds SI-088 and the revised drawing
- Done when: agent reliably retrieves the core evidence chain without missing obvious documents

**Milestone 2 — Full tool set + citation verification**
- Build: remaining tools, deterministic citation checker
- Test: intentionally ask it something the dataset can't answer (cost impact) — does it correctly say "not found"?
- Done when: it correctly flags the deliberate gap and the deliberate contradiction

**Milestone 3 — Dossier generation + UI**
- Build: structured dossier output, investigation trail view, 5-screen UI
- Test: full end-to-end run, human-readable dossier with correct FACT/INFERENCE/GAP labeling
- Done when: you'd be comfortable showing this to your father

**When to switch to Claude Code**: once this document is finalized and you have the schema, tool list, and milestone plan settled — i.e., now, after this conversation. Use normal Claude for any further product/architecture rethinking; use Claude Code for the actual implementation loop.

---

## PART I — Validation Plan

**44–47.**

Show your father: the live investigation trail (agent reasoning step by step) and the final dossier — not the code. Ask him:
- "Does this look like how you'd actually reconstruct evidence for a claim?"
- "What document types are missing from my fictional set that would be essential in your real claims?"
- "Was the real problem retrieval, or was it that records were never created/filed correctly in the first place?"
- "Who in your organization actually does this reconstruction work today, and how do they do it now (Excel? memory? a DMS)?"

Then talk to a claims/contracts manager or document controller directly, not just your father — he's a Project Director, one level removed from the day-to-day evidence-wrangling. Ask what tool they currently use, if any, and what would make them trust an AI-generated dossier at all.

Validating signal: someone who does this work says "yes, this is genuinely the bottleneck" and wants to try it on a real (redacted) project. Needs-modification signal: the document types/relationships are wrong, or the real bottleneck is upstream (notices never filed) rather than retrieval. Pivot signal: claims professionals say records are the least of their problems compared to contractual/legal interpretation — in which case the real product might be closer to contract analysis than evidence retrieval.

---

## PART J — Final Recommendation

**48–51.**

I recommend building this V0 — it's scoped sensibly, technically tractable for one developer with AI assistance, cheap, and it forces you to learn agentic system design properly rather than superficially. The citation-integrity discipline you've built into the spec (FACT/INFERENCE/GAP/UNVERIFIED, deterministic verification) is genuinely the right instinct and is more rigorous than most first AI-agent projects.

**Biggest reason it could succeed**: it's a real, narrow, well-understood technical problem (retrieval + agentic tool use + grounded citation) wrapped around a domain your father can validate quickly and cheaply, with a clear "show, don't pitch" demo path.

**Biggest reason it could fail**: you don't yet know if the underlying problem is retrieval (fixable by software) or upstream process/legal issues (not fixable by search). If it's the latter, a beautifully built evidence investigator solves a problem nobody has.

**Next three actions**:
1. Generate the fictional 18-document dataset now, before writing any pipeline code — it will surface flaws in your document-relationship assumptions early.
2. Build Milestone 0 + 1 only (ingestion + minimal search/read agent), and manually inspect whether it finds the SI-088 → drawing → DPR chain correctly.
3. Before building Milestone 2/3, get 20 minutes with your father specifically to challenge the document-type assumptions in Part E against his real experience.
