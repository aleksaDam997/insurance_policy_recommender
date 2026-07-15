import pandas as pd

def build_complete_record(df: pd.DataFrame, key: str):
    df = df.sort_values(key)
    df_filled = df.groupby(key).transform('bfill')
    df_filled[key] = df[key].values
    return df_filled.drop_duplicates(key, keep='first')