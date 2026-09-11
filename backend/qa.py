import re
import pandas as pd
from pathlib import Path

_shipments_path = Path(__file__).resolve().parent.parent / "data" / "shipment_records.csv"
_shipments_df = pd.read_csv(_shipments_path, keep_default_na=False)
ROUTES = list(
    (_shipments_df["origin"] + "-" + _shipments_df["destination"])
    .unique()
)

MONTH_NAMES = {
    "january": "01",
    "february": "02",
    "march": "03",
    "april": "04",
    "may": "05",
    "june": "06",
    "july": "07",
    "august": "08",
    "september": "09",
    "october": "10",
    "november": "11",
    "december": "12",
}


def extract_route(question: str) -> str:
    q = question.lower()
    for route in ROUTES:
        parts = route.split("-")
        city_a = parts[0].lower()
        city_b = parts[1].lower()
        if city_a in q and city_b in q:
            return route
    return None


def extract_month_year(question: str) -> tuple:
    q = question.lower()
    month = None
    for name, num in MONTH_NAMES.items():
        if name in q:
            month = num
            break
    year_match = re.search(r"\b(\d{4})\b", q)
    year = year_match.group(1) if year_match else None
    return (month, year)


def filter_matching_rows(df: pd.DataFrame, route: str, month: str, year: str) -> pd.DataFrame:
    result = df
    if route is not None:
        result = result[result["route"] == route]
    if month is not None:
        result = result[pd.to_datetime(result["week_of"]).dt.month == int(month)]
    if year is not None:
        result = result[pd.to_datetime(result["week_of"]).dt.year == int(year)]
    return result


def build_answer_prompt(question: str, matched_rows: list) -> str:
    records_text = "\n".join(
        f"{r['route']}, {r['week_of']}, {r['flagged']}, {r['reason']}"
        for r in matched_rows
    )
    return (
        f"Answer this question using only the information below. "
        f"Question: {question}. "
        f"Relevant records: {records_text}. "
        f"Write a 1 to 3 sentence answer grounded only in these records. "
        f"Do not invent any route, date, or fact not listed above. "
        f"Do not use markdown."
    )


def answer_question(question: str, df: pd.DataFrame, provider) -> dict:
    route = extract_route(question)
    month, year = extract_month_year(question)
    if route is None:
        return {
            "answer": "No flagged weeks found matching that question. Try mentioning a specific route or month.",
            "matched_row_count": 0,
        }
    filtered = filter_matching_rows(df, route, month, year)
    if filtered.empty:
        return {
            "answer": "No flagged weeks found matching that question. Try mentioning a specific route or month.",
            "matched_row_count": 0,
        }
    matched_rows = filtered.to_dict(orient="records")
    prompt = build_answer_prompt(question, matched_rows)
    result = provider.generate(prompt)
    return {
        "answer": result["text"],
        "matched_row_count": len(matched_rows),
    }
