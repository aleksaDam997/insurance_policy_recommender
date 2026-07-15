#!/usr/bin/env python3

from pathlib import Path
import pandas as pd
import numpy as np
from tqdm import tqdm

from src.insurance_policy_recommender.utils.generator.generator import validation_report_to_html
from src.insurance_policy_recommender.utils.fio.fio import write_into_file, write_yaml
from src.insurance_policy_recommender.entity.artifact_entity import DataIngestionArtifact, DataValidationArtifact
from src.insurance_policy_recommender.entity.config_entity import DataValidationConfig
from src.insurance_policy_recommender.components.helper.data_validation_helper import *
from src.insurance_policy_recommender.logging.logger import logger
from src.insurance_policy_recommender.exception.exception import InsurancePolicyRecommenderException
from src.insurance_policy_recommender.constants.training_pipeline import TABLE_NAME_TO_PATH_MAP

class DataValidation:
    def __init__(self, config: DataValidationConfig, data_ingestion_artifact: DataIngestionArtifact):
        self.config = config
        self.data_ingestion_artifact = data_ingestion_artifact

    def __validate_table(self,table_name: str, report: ValidationReport) -> bool:

        _STATUS = True
        
        """Validira jedan CSV fajl prema schema.yaml i popunjava fill_rates dict."""
        schema = self.config.schema['schema'].get(table_name, {})

        table_path = getattr(
            self.data_ingestion_artifact,
            TABLE_NAME_TO_PATH_MAP[table_name]
        )
        
        if not schema:
            report.error(f"[{table_name}] Nema definisane schema u schema.yaml — preskačem provjere.")
            return False

        try:
            df = pd.read_csv(table_path, low_memory=False)
        except Exception as e:
            report.error(f"[{table_name}] Ne mogu učitati {table_path}: {e}")
            return False

        columns = schema.get("columns", {})

        # 0) Potpuno identični redovi (mogući duplicate ingestion)
        # Dakle poredi sve kolone redova i gleda ako ima bukvalno sve iste vrijednosti odnosno ako je cijeli red dupli oznaci duplikat sa True
        # Prvi red za koga nadje duplikat ce biti False
        full_dups = df.duplicated().sum()
        dup_rate = full_dups / len(df)

        report.warn(
            f"[{table_name}] {full_dups} duplikata ({dup_rate:.2%} redova)."
        )

        if full_dups > 0:
            report.warn(f"[{table_name}] {full_dups} potpuno identičnih redova (mogući duplicate ingestion).")

        # 1) Provjera prisustva kolona
        for col_name, col_spec in columns.items():

            required = col_spec.get("required", False)
            used = col_spec.get("used_by_pipeline", True)

            if col_name not in df.columns:
                if required:
                    report.error(f"[{table_name}] Nedostaje OBAVEZNA kolona: '{col_name}'")
                    _STATUS = False
                elif used:
                    report.error(
                        f"[{table_name}] Nedostaje kolona '{col_name}' koju pipeline koristi "
                        f"(used_by_pipeline=true), ali nije formalno required — provjeri feature engineering."
                    )
                else:
                    report.warn(f"[{table_name}] Nedostaje kolona '{col_name}' nije kritično za pipeline.")
                continue

            series = df[col_name]

            # 2) Tip provjera
            expected_type = col_spec.get("type", "UNKNOWN")

            if expected_type == "UNKNOWN":

                report.warn(
                    f"[{table_name}.{col_name}] schema.yaml ne sadrži 'type' za ovu kolonu — "
                    f"provjeri da li je feature engineering kompatibilan sa tipom u CSV-u."
                )
                continue


            checker = TYPE_CHECKERS[expected_type]

            if not checker(series):
                report.error(
                    f"[{table_name}.{col_name}] Tip ne odgovara schema['type']={expected_type} "
                    f"Primjer vrijednosti={series.dropna().iloc[0]!r} "
                    f"(pandas dtype={series.dtype})"
                )
                _STATUS = False
                continue


            f_rate = round(series.notna().mean() * 100, 2)

            if required and f_rate < 50.0:
                report.warn(
                    f"[{table_name}.{col_name}] required kolona ima fill_rate={f_rate}% — provjeri izvor."
                )

            nunique = series.nunique()

            if nunique / len(df) > 0.95:
                report.warn(f"[{table_name}.{col_name}] vjerovatno predstavlja neki vrstu id-a")

            if series.notna().any():
                most_frequent_count = series.value_counts().max()
                top_share = most_frequent_count / len(series.dropna())
                if nunique == 1:
                    report.warn(f"[{table_name}.{col_name}] Konstantna kolona (nunique=1) — beskoristan feature.")
                elif top_share > 0.99:
                    report.warn(f"[{table_name}.{col_name}] Dominantna vrijednost {top_share:.1%} — skoro konstantna.")

            if expected_type in ("integer", "float") and pd.api.types.is_numeric_dtype(series):
                
                n_valid = series.dropna()

                if len(n_valid) > 0:
                    n_out = self.__detect_outliers_iqr(n_valid)
                    if n_out > 0:
                        report.warn(
                            f"[{table_name}.{col_name}] {n_out} IQR outliera "
                            f"({n_out / len(series):.1%} redova)."
                        )
                        
                if np.isinf(series).sum() > 0:
                    report.warn(f"[{table_name}.{col_name}] sadrzi infinity vrijednosti.")

            # empty_spaces = (series.astype(str).str.strip() == '').sum()

            report.info_add_used_column(UsedColumnReport(table_name=table_name, column_name=col_name, fill_rate = f_rate, nunique = nunique))

        # 6) Kolone u fajlu koje NISU u schemi (novododate/rename u izvoru)
        extra_cols = set(df.columns) - set(columns.keys())
        
        if extra_cols:

            report.warn(
                f"[{table_name}] Kolone u CSV-u koje NISU definisane u schema.yaml: "
                f"{sorted(extra_cols)}"
            )
            report.info_add_excess_column(f"[{table_name}] {sorted(extra_cols)}")

        return _STATUS




    # quantile(p) vraća vrijednost ispod koje se nalazi približno p% podataka.
    #
    # Interno se podaci sortiraju i računa se pozicija:
    # position = (n - 1) * p
    #
    # gdje je:
    #   n - broj elemenata
    #   p - percentil (npr. 0.25 za 25%)
    #
    # Ako pozicija nije cijeli broj, koristi se interpolacija između
    # susjednih vrijednosti. Funkcija na kraju vraća vrijednost
    # percentila, a ne njegov indeks.
    def __detect_outliers_iqr(self, series):

        # Prvi kvartil (25. percentil) - 25% podataka je ispod ove vrijednosti
        q1 = series.quantile(0.25)

        # Treći kvartil (75. percentil) - 75% podataka je ispod ove vrijednosti
        q3 = series.quantile(0.75)

        # Interkvartilni raspon (IQR) predstavlja širinu srednjih 50% podataka
        iqr = q3 - q1

        # Donja granica ispod koje se vrijednosti smatraju outlierima
        lower = q1 - 1.5 * iqr

        # Gornja granica iznad koje se vrijednosti smatraju outlierima
        upper = q3 + 1.5 * iqr

        # Kreira masku:
        # True  -> vrijednost je outlier
        # False -> vrijednost nije outlier
        #
        # Zatim sum() broji koliko ima True vrijednosti
        return ((series < lower) | (series > upper)).sum()


                

    def run_data_validation(self):

        report = ValidationReport()
        schema = self.config.schema['schema']

        pbar = tqdm(schema.keys(), desc="Processing tables", total=len(schema))

        for table_name in pbar:
            pbar.set_description(f"Processing {table_name}")

            status = self.__validate_table(table_name, report)
            if not status:
                logger.error(f"[{table_name}] Validacija nije prošla — pogledaj report.")

        data_validation_artifact = DataValidationArtifact(self.config.report_file_path, self.config.report_page_file_path,  
                                                          policy_raw_data_path=self.data_ingestion_artifact.policy_raw_data_path, raw_ins_client_data_path=self.data_ingestion_artifact.raw_ins_client_data_path,
                                                          raw_policy_client_data_path=self.data_ingestion_artifact.raw_policy_client_data_path, raw_policy_type_data_path=self.data_ingestion_artifact.raw_policy_type_data_path,
                                                          raw_client_roles_data_path=self.data_ingestion_artifact.raw_client_roles_data_path)

        write_yaml(report.to_dict(), data_validation_artifact.report_file_path)

        html_report = validation_report_to_html(report.__dict__)
        write_into_file(html_report, data_validation_artifact.report_page_file_path)

        return data_validation_artifact


        #business_rule_checks(dfs, report)



