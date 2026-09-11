# Decisions Log

## Section 1: Ingestion + Weekly Aggregation
- What: Loaded shipment records, derived week_of as the Monday of each shipment's week, derived route as origin-destination, aggregated cost per tonne-km per route per week by summing total cost and total tonne-km before dividing (not averaging per-shipment ratios).
- Why: Aggregating at the group level before dividing gives a volume-weighted cost per tonne-km, which is statistically correct for a group metric. Averaging per-shipment ratios would let small shipments distort the week's number.

## Section 2: Comparison Engine + Flagging
- What: Computed trailing 8-week own-history average (strictly prior weeks, degrades gracefully with fewer weeks), same-week peer average across other routes of the same route_type, and flagged any week where either comparison rises 15% or more.
- Why: The brief's own examples show a flag triggered by peer comparison alone even when the history-comparison is modest, confirming the two checks are combined with OR, not AND. 15% is the threshold that separates routine week-to-week noise from the three worked examples in the brief while giving clear margin on the two larger ones.

## Section 3: Notes Filtering + Retrieval
- What: Built a two-stage deterministic filter (route match or "All Routes", then a -21/+10 day window around the flagged week) before any similarity ranking, and split results into a justifying candidate (negation-checked) versus a closest-context candidate (not negation-checked, used only so the explanation can name a nearby note even when it doesn't count). Used TF-IDF + cosine similarity for ranking rather than a neural embedding model or full vector database, since 10 notes doesn't warrant that infrastructure and TF-IDF keeps the whole retrieval step deterministic with zero external downloads.
- Why: The brief's own worked example names a rejected note in the explanation text, which a single-bucket "candidate or nothing" design can't reproduce. The window bounds were derived by checking them against all three worked examples in the brief before implementation, not tuned after the fact.

## Section 4: LLM Explanation Layer
- What: Built a provider-agnostic LLMProvider interface with a GroqProvider implementation (llama-3.1-8b-instant, temperature 0), and restricted every LLM call to a strict single-note prompt so the model only phrases an explanation, never decides the verdict. Skipped the LLM entirely for the "no candidate note at all" case since there is nothing to ground an explanation in.
- Why: Keeping verdict logic in code and giving the LLM only phrasing duties makes the pipeline reproducible across runs (grading requires identical flags/numbers, only wording may vary) and removes the LLM's ability to hallucinate a verdict. Skipping the call when there's no note to reference is both cheaper and safer than letting a model guess.

## Section 4 Correction
- What: GROQ_MODEL was initially set to groq/compound during setup, which is an agentic model that leaked chain-of-thought reasoning into one output row. Switched to allam-2-7b, a plain instruction-tuned model with no metered cost on this tier, and corrected the cost estimate constants in explanation.py from Llama 3.1 8B pricing to $0.00 to match the model actually used.
- Why: compound is designed for multi-step tool orchestration, not single-sentence extraction, and produced unpredictable reasoning preambles. allam-2-7b behaved deterministically across all 14 rows with zero cost, which is a better fit for a task that only needs one grounded sentence.

## Section 5 Addendum: Rate Limit Retry
- What: Added retry-with-backoff (up to 5 attempts, 2.5s wait) in GroqProvider.generate for HTTP 429 responses, discovered when running the pipeline three consecutive times for the reproducibility check. Also corrected the fallback default model string to match the model actually in use (allam-2-7b instead of the deprecated llama-3.1-8b-instant).
- Why: Three full pipeline runs in quick succession is exactly the pattern that triggers Groq's free-tier rate limit, and failing outright there would make the reproducibility check itself unreliable rather than the pipeline. The retry only delays and re-sends the identical request — it does not change what gets sent or how the response is parsed, so it does not affect determinism.

## Section 4.5: Fallback LLM Provider
- What: Added a FallbackProvider that tries Groq first and falls back to NVIDIA NIM only if Groq's call raises an error, with both providers self-reporting their name so the usage log records which one actually served each call.
- Why: A single-provider pipeline has one point of failure if that provider has an outage or rate-limits mid-run; a same-shape OpenAI-compatible fallback costs one small class and keeps verdict logic completely unchanged, since the LLM is only ever used for phrasing, never for the decision itself. Verified by temporarily disabling the Groq key and confirming NVIDIA NIM served the calls without any other behavior change.

## Section 5: Output Formatting + Reproducibility Check
- What: Reshaped internal pipeline columns into the exact sample_output_format_v2.csv contract, then ran the entire pipeline three full times end-to-end and diffed every graded column except free-text reason across all three runs.
- Why: The brief grades reproducibility on flags and numbers, explicitly allowing explanation wording to vary, so the diff excludes reason by design rather than by oversight. Running the actual pipeline as subprocesses three times is a stronger proof than reasoning about determinism from the code alone.

## Section 6: Eval Harness
- What: Built two independent checks — four hand-verified labeled cases covering all four verdict scenarios (peer-window justified, multi-week flood justified, closest-note rejected, no note at all), and a full-dataset negation safety scan that re-reads raw note text for every matched_note_id in the final output and confirms none of them are negated notes.
- Why: The labeled cases prove correctness on scenarios already validated by hand during earlier sections, now automated instead of relying on memory. The negation scan checks the entire output, not a sample, and is independent of the pipeline's own filtering logic since it re-derives negation from raw text rather than trusting the is_negated flag computed earlier — this is what lets us honestly say the system was checked, not just built.

## Section 7: FastAPI Backend + React Dashboard
- What: Built a read-only FastAPI layer over the pipeline's own output files (no recomputation on request) with two endpoints, and a single-page React dashboard with a sortable table, an expandable evidence panel per row, and a per-route cost trend chart.
- Why: Keeping the API strictly read-only over precomputed output means the API can never disagree with the graded CSV — there's one source of truth, not two systems that could drift apart. The expandable evidence panel exists specifically so a reviewer can check the "no hallucination" claim visually against the actual matched note, rather than trusting the reason text on faith.

## Section 8: README and Final Documentation
- What: Wrote the top-level README covering architecture, run instructions, key design decisions, reproducibility, cost, and known limitations, sourced entirely from decisions.md and real output files rather than restated estimates.
- Why: The brief evaluates "can you explain your work" partly from the README alone before any live walkthrough, so it needed to stand on its own as a complete account rather than a summary that assumes the reader has decisions.md open too.

## Section 8 Addendum: NVIDIA NIM Model Selection

- What: Tested every apparent text-instruct model available on the NVIDIA NIM key (meta/llama-3.1-8b-instruct, nvidia/llama-3.1-nemotron-nano-8b-v1, mistral-7b, granite-3.0-8b, nemotron-51b/70b, gemma-3-4b-it, poolside/laguna-xs-2.1) and found each was either 410 end-of-life, 404 inaccessible on this key, or 503 unavailable. meta/llama-3.2-11b-vision-instruct was the only model that returned 200 and handled the plain-text explanation prompt correctly.
- Why: A vision-labeled model is not the ideal fit on paper, but empirical verification matters more than a clean-sounding name — this was tested directly against the actual explanation prompt, not just a "say hello" check, before being accepted as the fallback model.

## Section 9: Stretch Goal Q&A
- What: Added a POST /api/ask endpoint that extracts a route and/or month/year from a plain-English question via string matching, filters the already-computed final_flagged_routes.csv to matching rows, and makes one LLM call to phrase an answer strictly from those rows' existing reason field. Questions with no recognized route return a fixed "no match" message with zero LLM calls. ROUTES is loaded from the full shipment_records.csv (all 7 routes), not from the flagged-only output, so a real route with zero anomalies is correctly distinguished from an unrecognized route at the code level. Added a matching input/answer block to the dashboard, visually distinguishing grounded answers from no-match answers.
- Why: This is deliberately not a general-purpose chatbot — it answers only from data the pipeline already verified and grounded, reusing the same "verdict in code, LLM only phrases" guardrail from Section 4 rather than introducing a second, less-trustworthy answering path. Requiring a recognized route before answering keeps the assistant scoped to what it can actually verify, at the cost of not answering broader cross-route questions like "what got flagged in December" — a deliberate scope trade-off, not an oversight.

