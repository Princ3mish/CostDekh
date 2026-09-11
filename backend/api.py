from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

flagged_df = pd.read_csv("output/final_flagged_routes.csv", keep_default_na=False)
notes_df = pd.read_csv("data/context_notes.csv", keep_default_na=False)
history_df = pd.read_csv("output/weekly_aggregates.csv")

notes_lookup = {
    str(r["note_id"]).strip(): {"text": str(r["note"]), "date": str(r["date"])}
    for _, r in notes_df.iterrows()
}


@app.get("/api/flagged-routes")
def get_flagged_routes():
    records = flagged_df.to_dict(orient="records")
    for rec in records:
        nid = str(rec.get("matched_note_id", "")).strip()
        if nid and nid not in ("nan", "None") and nid in notes_lookup:
            rec["matched_note_text"] = notes_lookup[nid]["text"]
            rec["matched_note_date"] = notes_lookup[nid]["date"]
        else:
            rec["matched_note_text"] = None
            rec["matched_note_date"] = None
    return records


@app.get("/api/route-history/{route}")
def get_route_history(route: str):
    filtered = history_df[history_df["route"] == route].sort_values("week_of", ascending=True)
    return filtered[["week_of", "cost_per_tonne_km"]].to_dict(orient="records")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
