from datetime import date
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

WINDOW_BEFORE_DAYS = 21
WINDOW_AFTER_DAYS = 10
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


def load_notes(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'])
    return df


def is_negated(note_text: str) -> bool:
    text_lower = str(note_text).lower()
    return any(p in text_lower for p in NEGATION_PHRASES)


def get_route_date_candidates(route: str, week_of: date, notes_df: pd.DataFrame) -> pd.DataFrame:
    week_dt = pd.to_datetime(week_of)
    start_dt = week_dt - pd.Timedelta(days=WINDOW_BEFORE_DAYS)
    end_dt = week_dt + pd.Timedelta(days=WINDOW_AFTER_DAYS)
    mask_route = (notes_df['applies_to'] == route) | (notes_df['applies_to'] == 'All Routes')
    mask_date = (notes_df['date'] >= start_dt) & (notes_df['date'] <= end_dt)
    res = notes_df[mask_route & mask_date].copy()
    res['negated'] = res['note'].apply(is_negated)
    return res


def rank_by_similarity(candidates: pd.DataFrame, route: str) -> pd.DataFrame:
    if candidates.empty:
        return candidates
    query = route.replace('-', ' ')
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(candidates['note'])
    query_vec = vectorizer.transform([query])
    sim = cosine_similarity(query_vec, tfidf_matrix).flatten()
    res = candidates.copy()
    res['similarity'] = sim
    return res.sort_values(by='similarity', ascending=False)


def match_notes_for_row(route: str, week_of: date, notes_df: pd.DataFrame) -> dict:
    candidates = get_route_date_candidates(route, week_of, notes_df)
    ranked = rank_by_similarity(candidates, route)
    justifying = ranked[~ranked['negated']] if not ranked.empty else pd.DataFrame()
    if not justifying.empty:
        best_justifying_note_id = justifying.iloc[0]['note_id']
        best_justifying_similarity = justifying.iloc[0]['similarity']
    else:
        best_justifying_note_id = None
        best_justifying_similarity = None
    if not ranked.empty:
        closest_context_note_id = ranked.iloc[0]['note_id']
        closest_context_similarity = ranked.iloc[0]['similarity']
    else:
        closest_context_note_id = None
        closest_context_similarity = None
    return {
        'route': route,
        'week_of': week_of,
        'best_justifying_note_id': best_justifying_note_id,
        'best_justifying_similarity': best_justifying_similarity,
        'closest_context_note_id': closest_context_note_id,
        'closest_context_similarity': closest_context_similarity
    }


if __name__ == '__main__':
    flagged_df = pd.read_csv('output/flagged_weeks.csv')
    flagged_df = flagged_df[flagged_df['is_flagged'] == True]
    notes_df = load_notes('data/context_notes.csv')
    results = [
        match_notes_for_row(row['route'], row['week_of'], notes_df)
        for _, row in flagged_df.iterrows()
    ]
    out_df = pd.DataFrame(results)
    out_df.to_csv('output/candidate_matches.csv', index=False)
    matched_count = out_df['best_justifying_note_id'].notna().sum()
    none_count = out_df['best_justifying_note_id'].isna().sum()
    print(f"Matched: {matched_count}, None: {none_count}")
