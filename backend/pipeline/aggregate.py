import os
import sys
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from backend.pipeline.ingest import load_shipments
except ImportError:
    from ingest import load_shipments


def weekly_aggregate(df: pd.DataFrame) -> pd.DataFrame:
    df_copy = df.copy()
    df_copy['tonne_km'] = df_copy['quantity_tonnes'] * df_copy['distance_km']
    agg = df_copy.groupby(['route', 'route_type', 'week_of'], as_index=False).agg(
        total_cost=('freight_cost_inr', 'sum'),
        total_tonne_km=('tonne_km', 'sum')
    )
    agg['cost_per_tonne_km'] = agg['total_cost'] / agg['total_tonne_km']
    agg = agg[['route', 'route_type', 'week_of', 'total_cost', 'total_tonne_km', 'cost_per_tonne_km']]
    agg = agg.sort_values(by=['route', 'week_of'], ascending=[True, True]).reset_index(drop=True)
    return agg


if __name__ == '__main__':
    df = load_shipments('data/shipment_records.csv')
    result = weekly_aggregate(df)
    result.to_csv('output/weekly_aggregates.csv', index=False)
    print(len(result))
    print(result.head(5))
