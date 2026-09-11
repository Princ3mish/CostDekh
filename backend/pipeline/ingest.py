import pandas as pd


def load_shipments(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df['shipment_date'] = pd.to_datetime(df['shipment_date'])
    df['week_of'] = (df['shipment_date'] - pd.to_timedelta(df['shipment_date'].dt.weekday, unit='D')).dt.date
    df['route'] = df['origin'] + '-' + df['destination']
    return df
