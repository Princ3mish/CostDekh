import pandas as pd

LABELED_CASES = [
    {"route": "Ahmedabad-Mumbai", "week_of": "2025-01-20", "expected_flagged": "No (justified)", "expected_matched_note_id": "N002"},
    {"route": "Chennai-Bangalore", "week_of": "2025-02-24", "expected_flagged": "No (justified)", "expected_matched_note_id": "N001"},
    {"route": "Mumbai-Pune", "week_of": "2025-09-15", "expected_flagged": "Yes", "expected_matched_note_id": ""},
    {"route": "Delhi-Jaipur", "week_of": "2024-11-11", "expected_flagged": "Yes", "expected_matched_note_id": ""}
]

NEGATION_PHRASES = [
    "not significantly affected",
    "no significant disruptions",
    "not part of this dataset",
    "remained normal",
    "returned to normal",
    "no major disruptions",
    "remained stable",
    "without a rate change",
    "improved road conditions"
]


def check_labeled_cases(output_df: pd.DataFrame) -> list:
    results = []
    for case in LABELED_CASES:
        sub = output_df[(output_df["route"] == case["route"]) & (output_df["week_of"] == case["week_of"])]
        if sub.empty:
            actual_flagged = ""
            actual_matched_note_id = ""
        else:
            r = sub.iloc[0]
            actual_flagged = str(r["flagged"]) if pd.notna(r["flagged"]) else ""
            actual_matched_note_id = str(r["matched_note_id"]) if pd.notna(r["matched_note_id"]) and str(r["matched_note_id"]).strip() not in ("nan", "None") else ""
        passed = (actual_flagged == case["expected_flagged"]) and (actual_matched_note_id == case["expected_matched_note_id"])
        results.append({
            "route": case["route"],
            "week_of": case["week_of"],
            "expected_flagged": case["expected_flagged"],
            "actual_flagged": actual_flagged,
            "expected_matched_note_id": case["expected_matched_note_id"],
            "actual_matched_note_id": actual_matched_note_id,
            "passed": passed
        })
    return results


def check_negation_safety(output_df: pd.DataFrame, notes_df: pd.DataFrame) -> list:
    notes_lookup = {str(r["note_id"]).strip(): str(r["note"]) for _, r in notes_df.iterrows()}
    matched_df = output_df[output_df["matched_note_id"].notna() & (output_df["matched_note_id"].astype(str).str.strip() != "") & (output_df["matched_note_id"].astype(str) != "nan")]
    results = []
    for _, r in matched_df.iterrows():
        nid = str(r["matched_note_id"]).strip()
        note_text = notes_lookup.get(nid, "")
        negated = any(phrase in note_text.lower() for phrase in NEGATION_PHRASES)
        results.append({
            "route": r["route"],
            "week_of": r["week_of"],
            "matched_note_id": nid,
            "negated": negated,
            "passed": not negated
        })
    return results


if __name__ == '__main__':
    output_df = pd.read_csv('output/final_flagged_routes.csv', keep_default_na=False)
    notes_df = pd.read_csv('data/context_notes.csv')

    labeled_results = check_labeled_cases(output_df)
    negation_results = check_negation_safety(output_df, notes_df)

    all_cases_passed = True
    for res in labeled_results:
        if res["passed"]:
            print(f"PASS: {res['route']} ({res['week_of']})")
        else:
            all_cases_passed = False
            print(f"FAIL: {res['route']} ({res['week_of']}) - expected flagged='{res['expected_flagged']}', matched_note_id='{res['expected_matched_note_id']}'; got flagged='{res['actual_flagged']}', matched_note_id='{res['actual_matched_note_id']}'")

    passed_neg_count = sum(1 for r in negation_results if r["passed"])
    total_neg_count = len(negation_results)
    print(f"{passed_neg_count}/{total_neg_count} matched notes passed negation safety check")
    for r in negation_results:
        if not r["passed"]:
            print(f"FAIL: {r['route']} ({r['week_of']}) matched note {r['matched_note_id']} contains negation")

    all_neg_passed = (passed_neg_count == total_neg_count)
    if all_cases_passed and all_neg_passed:
        print("EVAL PASSED")
    else:
        print("EVAL FAILED")
