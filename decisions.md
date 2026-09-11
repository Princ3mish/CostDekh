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
