import os
import sys
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from backend.pipeline.llm_provider import LLMProvider, GroqProvider, NvidiaNimProvider, FallbackProvider
except ImportError:
    from llm_provider import LLMProvider, GroqProvider, NvidiaNimProvider, FallbackProvider


def build_prompt(note_row: dict, route: str, week_of: str, is_rejection: bool) -> str:
    note_id = note_row.get("note_id", "")
    date_val = str(note_row.get("date", "")).split(" ")[0]
    note_text = note_row.get("note", note_row.get("note_text", ""))
    if not is_rejection:
        return f'You are writing one factual sentence for a logistics cost report. Route: {route}. Week: {week_of}. A cost rise on this route is explained by this note: Note {note_id}, dated {date_val}: "{note_text}". Write exactly one sentence stating that this note explains the cost rise, naming the note id and reflecting its actual content and date. Do not invent any information not in the note. Do not use markdown.'
    else:
        return f'You are writing one factual sentence for a logistics cost report. Route: {route}. Week: {week_of}. The closest available note is: Note {note_id}, dated {date_val}: "{note_text}". This note does not describe a reason for a cost rise on this route. Write exactly one sentence naming this note and its date, stating it does not justify the cost rise, and stating the rise remains unexplained. Do not invent any information not in the note. Do not use markdown.'


def get_verdict_and_reason(row: dict, notes_lookup: dict, provider: LLMProvider, usage_log: list) -> dict:
    best_id = row.get("best_justifying_note_id")
    closest_id = row.get("closest_context_note_id")
    if pd.notna(best_id) and str(best_id).strip() != "":
        note = notes_lookup[str(best_id)]
        prompt = build_prompt(note, str(row["route"]), str(row["week_of"]), False)
        resp = provider.generate(prompt)
        usage_log.append({
            "route": row["route"],
            "week_of": row["week_of"],
            "provider": resp.get("provider", "groq"),
            "input_tokens": resp["input_tokens"],
            "output_tokens": resp["output_tokens"]
        })
        return {
            "flagged": "No (justified)",
            "matched_note_id": str(best_id),
            "reason": resp["text"]
        }
    elif pd.notna(closest_id) and str(closest_id).strip() != "":
        note = notes_lookup[str(closest_id)]
        prompt = build_prompt(note, str(row["route"]), str(row["week_of"]), True)
        resp = provider.generate(prompt)
        usage_log.append({
            "route": row["route"],
            "week_of": row["week_of"],
            "provider": resp.get("provider", "groq"),
            "input_tokens": resp["input_tokens"],
            "output_tokens": resp["output_tokens"]
        })
        return {
            "flagged": "Yes",
            "matched_note_id": "",
            "reason": resp["text"]
        }
    else:
        return {
            "flagged": "Yes",
            "matched_note_id": "",
            "reason": "No matching note found for this route or date range. Cost rise looks unexplained and worth a human review."
        }


if __name__ == '__main__':
    candidates_df = pd.read_csv('output/candidate_matches.csv')
    notes_df = pd.read_csv('data/context_notes.csv')
    notes_lookup = {
        str(row['note_id']): {
            'note_id': str(row['note_id']),
            'date': str(row['date']).split(' ')[0],
            'note': row['note']
        }
        for _, row in notes_df.iterrows()
    }
    provider = FallbackProvider([GroqProvider(), NvidiaNimProvider()])
    usage_log = []
    results = []
    for _, row in candidates_df.iterrows():
        res = get_verdict_and_reason(row.to_dict(), notes_lookup, provider, usage_log)
        res['route'] = row['route']
        res['week_of'] = row['week_of']
        results.append(res)
    results_df = pd.DataFrame(results)

    flagged_df = pd.read_csv('output/flagged_weeks.csv')
    flagged_df = flagged_df[flagged_df['is_flagged'] == True]
    merged_df = flagged_df.merge(results_df[['route', 'week_of', 'flagged', 'matched_note_id', 'reason']], on=['route', 'week_of'], how='left')
    merged_df['matched_note_id'] = merged_df['matched_note_id'].fillna('')
    merged_df.to_csv('output/explained_weeks.csv', index=False)

    usage_df = pd.DataFrame(usage_log, columns=['route', 'week_of', 'provider', 'input_tokens', 'output_tokens'])
    usage_df.to_csv('output/llm_usage_log.csv', index=False)

    total_input = int(usage_df['input_tokens'].sum()) if not usage_df.empty else 0
    total_output = int(usage_df['output_tokens'].sum()) if not usage_df.empty else 0
    llm_calls = len(usage_df)
    est_cost = (total_input / 1_000_000 * 0.00) + (total_output / 1_000_000 * 0.00)
    print(f"Total input tokens: {total_input}")
    print(f"Total output tokens: {total_output}")
    print(f"Number of LLM calls: {llm_calls}")
    print(f"Estimated cost (ALLaM-2-7B free tier, $0/1M tokens): ${est_cost:.6f}")
