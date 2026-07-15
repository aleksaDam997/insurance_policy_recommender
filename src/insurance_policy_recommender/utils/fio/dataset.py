import pandas as pd
from pathlib import Path
import sys
from src.insurance_policy_recommender.exception.exception import InsurancePolicyRecommenderException

def load_csv_with_valid_columns(table_schema: dict, table_path: Path):

    try:
        dtype = {}
        parse_dates = []
        needed_cols = []

        for col_name, col_spec in table_schema.items():

            if col_spec["dtype"] == "datetime":
                parse_dates.append(col_name)
            else:
                dtype[col_name] = col_spec["dtype"]

            if col_spec["required"]:
                needed_cols.append(col_name)

        df = pd.read_csv(
            table_path,
            dtype=dtype,
            parse_dates=parse_dates
        )

        # df = df[needed_cols]

        return df
    except Exception as e:
        raise InsurancePolicyRecommenderException("Greška nastala kod učitavanja csv fajla sa podacima po validacionoj šemi.", sys)