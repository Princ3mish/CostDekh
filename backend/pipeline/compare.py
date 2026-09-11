import pandas as pd
import numpy as np

ANOMALY_THRESHOLD_PCT = 15.0


def add_own_history(df: pd.DataFrame) -> pd.DataFrame:
    df_res = df.sort_values(by=['route', 'week_of'], ascending=[True, True]).reset_index(drop=True)
    df_res['own_history_avg'] = df_res.groupby('route')['cost_per_tonne_km'].transform(
        lambda s: s.shift(1).rolling(window=8, min_periods=1).mean()
    )
    df_res['vs_own_history_pct'] = np.where(
        df_res['own_history_avg'].notna(),
        (((df_res['cost_per_tonne_km'] / df_res['own_history_avg']) - 1) * 100).round(1),
        np.nan
    )
    return df_res


def add_peer_comparison(df: pd.DataFrame) -> pd.DataFrame:
    df_res = df.copy()
    grp_sum = df_res.groupby(['week_of', 'route_type'])['cost_per_tonne_km'].transform('sum')
    grp_count = df_res.groupby(['week_of', 'route_type'])['cost_per_tonne_km'].transform('count')
    peer_sum = grp_sum - df_res['cost_per_tonne_km']
    peer_cnt = grp_count - 1
    df_res['peer_avg'] = np.where(peer_cnt > 0, peer_sum / peer_cnt, np.nan)
    df_res['vs_similar_routes_pct'] = np.where(
        df_res['peer_avg'].notna(),
        (((df_res['cost_per_tonne_km'] / df_res['peer_avg']) - 1) * 100).round(1),
        np.nan
    )
    return df_res


def flag_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    df_res = df.copy()
    cond1 = df_res['vs_own_history_pct'].notna() & (df_res['vs_own_history_pct'] >= ANOMALY_THRESHOLD_PCT)
    cond2 = df_res['vs_similar_routes_pct'].notna() & (df_res['vs_similar_routes_pct'] >= ANOMALY_THRESHOLD_PCT)
    df_res['is_flagged'] = cond1 | cond2
    return df_res


if __name__ == '__main__':
    df = pd.read_csv('output/weekly_aggregates.csv')
    df = add_own_history(df)
    df = add_peer_comparison(df)
    df = flag_anomalies(df)
    df.to_csv('output/flagged_weeks.csv', index=False)
    print(f"{df['is_flagged'].sum()} of {len(df)}")
