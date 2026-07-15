import pandas as pd
import re

class UsedColumnReport:
    def __init__(self, table_name: str, column_name: str, fill_rate: float, nunique: int):
        self.table_name = table_name
        self.column_name = column_name
        self.fill_rate = float(fill_rate)
        self.nunique = int(nunique)

    
    def to_dict(self):
        return {
            "table_name": self.table_name,
            "column_name": self.column_name,
            "fill_rate": self.fill_rate,
            "nunique": self.nunique
        }
class ValidationReport:

    def __init__(self):
        self.IS_VALID: bool = True
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.used_columns: list[UsedColumnReport] = []
        self.excess_columns: list[str] = []

    def error(self, msg: str):
        self.errors.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)

    def info_add_used_column(self, used_column: UsedColumnReport):
        self.used_columns.append(used_column)

    def info_add_excess_column(self, msg: str):
        self.excess_columns.append(msg)

    def ok(self) -> bool:
        self.IS_VALID = len(self.errors) == 0
        return self.IS_VALID
    
    def to_dict(self):
        return {
            "IS_VALID": self.IS_VALID,
            "errors": self.errors,
            "warnings": self.warnings,
            "used_columns": [
                x.to_dict()
                for x in self.used_columns
            ],
            "excess_columns": self.excess_columns
        }

# ------------------------------------------------------------------
# Mapiranje logičkog schema['type'] -> pandas provjera
# ------------------------------------------------------------------
def _is_integer_like(series: pd.Series) -> bool:
    s = series.dropna()
    if s.empty:
        return True
    if pd.api.types.is_integer_dtype(s):
        return True
    if pd.api.types.is_float_dtype(s):
        # Dozvoljavamo float kolonu SAMO ako su sve vrijednosti cjelobrojne
        # (npr. 5.0) — čest slučaj kad pandas učita int kolonu sa NaN-ovima.
        return (s % 1 == 0).all()
    return False


def _is_float_like(series: pd.Series) -> bool:
    s = series.dropna()
    if s.empty:
        return True
    return pd.api.types.is_numeric_dtype(s)



def _is_datetime_like(series: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True

    s = series.astype(str).str.strip()
    s = s.replace({'': pd.NA, 'nan': pd.NA, 'NaN': pd.NA, 'NULL': pd.NA, 'None': pd.NA})

    non_null = s.dropna()
    
    if non_null.empty:
        return True

    # Datumi cija je godina van pandas[ns] opsega (< 1678 ili > 2261) su
    # po definiciji sentinel/placeholder vrijednosti, ne mogu se validirati
    # preko pd.to_datetime u ovom environmentu - izuzimamo ih iz stroge provjere
    year_pattern = re.compile(r'^(\d{4})-\d{2}-\d{2}')

    out_of_range_mask = non_null.apply(
        lambda v: (m := year_pattern.match(v)) is not None and not (1678 <= int(m.group(1)) <= 2261)
    )
    
    checkable = non_null[~out_of_range_mask]

    if checkable.empty:
        return True

    parsed = pd.to_datetime(checkable, errors="coerce", format="mixed")
    return parsed.isna().mean() == 0


def _is_string_like(series: pd.Series) -> bool:
    # gotovo sve prolazi kao string (pandas object/num), ovo je slaba provjera
    return True




TYPE_CHECKERS = {
    "integer": _is_integer_like,
    "float": _is_float_like,
    "datetime": _is_datetime_like,
    "string": _is_string_like,
    "object": _is_string_like,
}