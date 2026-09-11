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

## Section 4.5: Fallback LLM Provider
- What: Added a FallbackProvider that tries Groq first and falls back to NVIDIA NIM only if Groq's call raises an error, with both providers self-reporting their name so the usage log records which one actually served each call.
- Why: A single-provider pipeline has one point of failure if that provider has an outage or rate-limits mid-run; a same-shape OpenAI-compatible fallback costs one small class and keeps verdict logic completely unchanged, since the LLM is only ever used for phrasing, never for the decision itself. Verified by temporarily disabling the Groq key and confirming NVIDIA NIM served the calls without any other behavior change.

## Section 5: Output Formatting + Reproducibility Check
- What: Reshaped internal pipeline columns into the exact sample_output_format_v2.csv contract, then ran the entire pipeline three full times end-to-end and diffed every graded column except free-text reason across all three runs.
- Why: The brief grades reproducibility on flags and numbers, explicitly allowing explanation wording to vary, so the diff excludes reason by design rather than by oversight. Running the actual pipeline as subprocesses three times is a stronger proof than reasoning about determinism from the code alone.
