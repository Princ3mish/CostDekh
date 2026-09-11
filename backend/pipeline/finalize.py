import pandas as pd


def format_pct(value: float) -> str:
    if value is None or pd.isna(value) or str(value).strip() in ("", "None", "nan", "NaN"):
        return "N/A"
    val = float(value)
    if val > 0:
        return f"+{val:.1f}%"
    return f"{val:.1f}%"


def build_output_row(row: dict) -> dict:
    return {
        "route": row["route"],
        "week_of": row["week_of"],
        "cost_per_tonne_km": round(float(row["cost_per_tonne_km"]), 2),
        "vs_own_history": f"{format_pct(row.get('vs_own_history_pct'))} vs this route's past average",
        "vs_similar_routes": f"{format_pct(row.get('vs_similar_routes_pct'))} vs similar-length routes this week",
        "flagged": row["flagged"],
        "matched_note_id": row["matched_note_id"] if pd.notna(row.get("matched_note_id")) and str(row.get("matched_note_id")).strip() not in ("nan", "None") else "",
        "reason": row["reason"]
    }


if __name__ == '__main__':
    df = pd.read_csv('output/explained_weeks.csv', keep_default_na=False)
    df = df.sort_values(by=['route', 'week_of'], ascending=[True, True]).reset_index(drop=True)
    rows = [build_output_row(row.to_dict()) for _, row in df.iterrows()]
    out_df = pd.DataFrame(rows, columns=[
        'route', 'week_of', 'cost_per_tonne_km', 'vs_own_history',
        'vs_similar_routes', 'flagged', 'matched_note_id', 'reason'
    ])
    out_df.to_csv('output/final_flagged_routes.csv', index=False)
    print(len(out_df))
