# FreightTiger Cost Watch

## What This Does
FreightTiger Cost Watch is an automated anomaly detection and root-cause explanation engine for freight logistics. It detects anomalous weekly shipping cost-per-tonne-km increases per route, checks unstructured operational context notes for real-world justifications before flagging, and generates single-sentence, grounded explanations for human review.

## Architecture
The system operates as a five-stage deterministic and LLM-assisted pipeline:

- `backend/pipeline/ingest.py` & `backend/pipeline/aggregate.py`: Loads raw shipment records and computes volume-weighted weekly cost per tonne-km per route.
- `backend/pipeline/compare.py`: Compares each route-week against its trailing 8-week history and same-week route-type peers, flagging anomalies with >=15% cost increases.
- `backend/pipeline/notes_retrieval.py`: Filters context notes by route and date window (-21 to +10 days), strips negated notes, and ranks relevant candidates using TF-IDF similarity.
- `backend/pipeline/explanation.py`: Prompts the LLM provider to formulate a single grounded explanatory sentence for candidate notes without delegating verdict decisions.
- `backend/pipeline/finalize.py`: Assembles final metric strings, comparative percentages, and formatted columns into `output/final_flagged_routes.csv`.

**Guardrail Design**: The anomaly and justification verdicts are calculated 100% deterministically in Python code; the LLM is strictly constrained to phrasing explanations from matched context and never decides whether a route is flagged. Negation phrases (e.g., "no major disruptions", "remained stable") are hard-filtered before the LLM ever receives a note. Additionally, a dual-provider fallback architecture ensures seamless execution via NVIDIA NIM if Groq encounters rate limits or outages.

## How To Run It
1. Install Python dependencies:
   ```bash
   pip install pandas scikit-learn requests python-dotenv fastapi uvicorn
   ```
2. Configure API keys in `backend/.env`:
   ```env
   GROQ_API_KEY=your_groq_api_key
   GROQ_MODEL=allam-2-7b
   NVIDIA_API_KEY=your_nvidia_api_key
   NVIDIA_NIM_MODEL=meta/llama-3.2-11b-vision-instruct
   ```
3. Execute the pipeline scripts in sequential order:
   ```bash
   python backend/pipeline/aggregate.py
   python backend/pipeline/compare.py
   python backend/pipeline/notes_retrieval.py
   python backend/pipeline/explanation.py
   python backend/pipeline/finalize.py
   ```
4. Start the FastAPI backend server:
   ```bash
   python backend/api.py
   ```
5. In a separate terminal, start the React frontend dashboard:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Key Design Decisions
- **15% Anomaly Threshold**: Separates genuine operational spikes from baseline noise while matching worked example benchmarks (see `decisions.md` Section 2).
- **-21 / +10 Day Note Window**: Captures advance announcements and multi-week operational disruptions while preventing distant historical notes from falsely matching (see `decisions.md` Section 3).
- **Group-Level Aggregation**: Sums total costs and tonne-km before dividing rather than averaging shipment ratios, preventing small loads from biasing route metrics (see `decisions.md` Section 1).
- **Justifying vs. Closest-Context Note Split**: Distinguishes valid explanations from rejected/negated notes, allowing rejected context to be cited in reasons without altering the "Yes" flag (see `decisions.md` Section 3).
- **TF-IDF Keyword Ranking**: Deterministic, lightweight similarity ranking that requires no external neural downloads or vector database infrastructure (see `decisions.md` Section 3).

## Reproducibility
The pipeline's determinism is validated via `reproducibility_check.py`, which executes three consecutive end-to-end pipeline passes and diffs all quantitative and categorical columns (`route`, `week_of`, `cost_per_tonne_km`, `vs_own_history`, `vs_similar_routes`, `flagged`, `matched_note_id`). All runs produced 100% identical outputs. All LLM calls enforce `temperature=0`, and all decisions and numerical calculations occur strictly in code.

## Cost of Running It
During the full pipeline execution on the dataset:
- **Serving Provider**: Groq (`allam-2-7b`)
- **Total LLM Calls**: 14 calls
- **Total Input Tokens**: 2,188
- **Total Output Tokens**: 1,185
- **Estimated Total Cost**: $0.00 (served on free tier)
- **Fallback Verification**: Tested and confirmed with NVIDIA NIM (`meta/llama-3.2-11b-vision-instruct` — the only model returning HTTP 200 on this API key after both `meta/llama-3.1-8b-instruct` and `nvidia/llama-3.1-nemotron-nano-8b-v1` returned 410 end-of-life) by temporarily simulating primary provider failure.

## Known Limitations
- **Small Dataset Baseline**: The anomaly threshold and retrieval window were calibrated against a dataset of 7 routes and 10 notes.
- **Heuristic Date Matching**: Date relevance uses a fixed calendar offset window rather than natural language semantic parsing of temporal expressions.
- **Sample Labeled Evaluation**: The automated evaluation harness checks 4 hand-labeled benchmark cases and a complete negation safety scan rather than exhaustive multi-annotator coverage.

## Project Structure
```
.
├── .gitignore
├── README.md
├── decisions.md
├── reproducibility_check.py
├── backend/
│   ├── .env
│   ├── .gitignore
│   ├── api.py
│   └── pipeline/
│       ├── __init__.py
│       ├── aggregate.py
│       ├── compare.py
│       ├── eval_harness.py
│       ├── explanation.py
│       ├── finalize.py
│       ├── ingest.py
│       ├── llm_provider.py
│       └── notes_retrieval.py
├── data/
│   ├── context_notes.csv
│   ├── sample_output_format_v2.csv
│   └── shipment_records.csv
├── frontend/
│   ├── .gitignore
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   ├── public/
│   │   ├── favicon.svg
│   │   └── icons.svg
│   └── src/
│       ├── App.css
│       ├── App.jsx
│       ├── main.jsx
│       └── assets/
│           ├── hero.png
│           └── vite.svg
└── output/
    ├── candidate_matches.csv
    ├── explained_weeks.csv
    ├── final_flagged_routes.csv
    ├── flagged_weeks.csv
    ├── llm_usage_log.csv
    ├── run_1.csv
    ├── run_2.csv
    ├── run_3.csv
    └── weekly_aggregates.csv
```
