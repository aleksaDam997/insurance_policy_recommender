#!/usr/bin/env python3
"""
validate_data.py
=================
Validira ulazne CSV fajlove (new_polisa, new_polisa_klijent, ins_klijent,
tsif_vrsta, new_polisa_uloga) protiv schema.yaml PRIJE pokretanja
final_solution_V11.ipynb pipeline-a.

Provjerava:
  1. Da svi fajlovi postoje i da se mogu učitati.
  2. Da su sve kolone iz scheme prisutne (required=true -> hard error,
     required=false + used_by_pipeline=true -> warning).
  3. Da tipovi kolona (grubo) odgovaraju schema['type'].
  4. dtype_cast kompatibilnost (npr. Int32 kolona ne smije imati floatove
     sa decimalama, string kolona koja se cast-uje kao str prolazi uvijek).
  5. pipeline_role == 'join_key'  -> nema null vrijednosti (inner join bi
     ih nečujno izbacio, pa se to prijavljuje kao upozorenje o gubitku
     redova, ne kao hard error).
  6. pipeline_role == 'hard_filter' -> nema null vrijednosti (inner
     filter bi ih izbacio) + fer-check da filter uslov ('D'/'N', 'Ugovarač'
     substring, itd.) stvarno postoji u podacima.
  7. Fill-rate report za sve kolone (isto ono što notebook radi u
     plot_column_fill_rate, samo textualno + moguć CSV export).

Upotreba:
    python validate_data.py --data-dir /path/to/production --schema schema.yaml
    python validate_data.py --data-dir . --schema schema.yaml --fill-rate-csv fillrate.csv

Exit kod:
    0  -> sve prošlo (može biti warning-a, ali nema hard errora)
    1  -> nađen bar jedan hard error (required kolona nedostaje, fajl
          nedostaje, join_key/hard_filter ima nullove, itd.)
"""
from pathlib import Path

import pandas as pd

from src.insurance_policy_recommender.utils.generator.generator import validation_report_to_html
from src.insurance_policy_recommender.utils.fio.fio import write_into_file, write_yaml
from src.insurance_policy_recommender.entity.artifact_entity import DataIngestionArtifact
from src.insurance_policy_recommender.entity.config_entity import DataValidationConfig
from src.insurance_policy_recommender.components.helper.data_validation_helper import *
from src.insurance_policy_recommender.logging.logger import logger
from src.insurance_policy_recommender.exception.exception import InsurancePolicyRecommenderException
from src.insurance_policy_recommender.constants.training_pipeline import TABLE_NAME_TO_PATH_MAP

class DataValidation:
    def __init__(self, config: DataValidationConfig, data_ingestion_artifact: DataIngestionArtifact):
        self.config = config
        self.data_ingestion_artifact = data_ingestion_artifact

    def __validate_table(self,table_name: str, report: ValidationReport, fill_rates: dict) -> bool:

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

        # 1) Provjera prisustva kolona
        for col_name, col_spec in columns.items():

            required = col_spec.get("required", False)
            used = col_spec.get("used_by_pipeline", True)

            if col_name not in df.columns:
                if required:
                    report.error(f"[{table_name}] Nedostaje REQUIRED kolona: '{col_name}'")
                    _STATUS = False
                elif used:
                    report.warn(
                        f"[{table_name}] Nedostaje kolona '{col_name}' koju pipeline koristi "
                        f"(used_by_pipeline=true), ali nije formalno required — provjeri feature engineering."
                    )
                continue

            series = df[col_name]

            # 2) Tip provjera
            expected_type = col_spec.get("type", "UNKNOWN")

            if expected_type == "UNKNOWN":

                report.error(
                    f"[{table_name}.{col_name}] schema.yaml ne sadrži 'type' za ovu kolonu — "
                    f"provjeri da li je feature engineering kompatibilan sa tipom u CSV-u."
                )
                _STATUS = False
                continue


            checker = TYPE_CHECKERS[expected_type]

            if col_name == 'dat_do_ug':
                print(f"DEBUG: [{table_name}.{col_name}] expected_type={expected_type}, dtype={series.dtype}, first_value={series.dropna().iloc[0] if not series.dropna().empty else 'N/A'}")

            if not checker(series):
                report.error(
                    f"[{table_name}.{col_name}] Tip ne odgovara schema['type']={expected_type} "
                    f"Primjer vrijednosti={series.dropna().iloc[0]!r} "
                    f"(pandas dtype={series.dtype})"
                )
                _STATUS = False

            report.info_add_used_column(f"[{table_name}] {col_name}")

            # 3) Fill rate (za report)
            fill_rates[f"{table_name}.{col_name}"] = round(series.notna().mean() * 100, 2)

        # 6) Kolone u fajlu koje NISU u schemi (novododate/rename u izvoru)
        extra_cols = set(df.columns) - set(columns.keys())
        if extra_cols:

            report.warn(
                f"[{table_name}] Kolone u CSV-u koje NISU definisane u schema.yaml: "
                f"{sorted(extra_cols)}"
            )
            report.info_add_excess_column(f"[{table_name}] {sorted(extra_cols)}")

        return _STATUS


    def __business_rule_checks(self, dfs: dict, report: ValidationReport):
        """Provjere specifične za poznate hard_filter/join_key uslove u notebook-u."""

        # polisa_id notna & != 0  (new_polisa)
        pol = dfs.get("new_polisa")
        if pol is not None and "polisa_id" in pol.columns:
            bad = pol["polisa_id"].isna().sum() + (pol["polisa_id"].fillna(-1) == 0).sum()
            if bad > 0:
                report.warn(
                    f"[new_polisa] {bad} redova sa polisa_id null ili 0 — biće izbačeno "
                    f"filterom u ćeliji za čišćenje podataka."
                )
            dup = pol["polisa_id"].duplicated().sum()
            if dup > 0:
                report.warn(f"[new_polisa] {dup} duplikata na polisa_id (drop_duplicates ih uklanja).")

        # new_polisa_uloga.opis mora sadržati 'Ugovarač'
        roles = dfs.get("new_polisa_uloga")
        if roles is not None and "opis" in roles.columns:
            matches = roles["opis"].astype(str).str.contains("Ugovarač", na=False).sum()
            if matches == 0:
                report.error(
                    "[new_polisa_uloga] Nijedan red ne sadrži 'Ugovarač' u koloni 'opis' — "
                    "filter za ugovarače će vratiti 0 redova i cijeli join će biti prazan."
                )

        # tsif_vrsta.ind_polisa mora imati vrijednost 'D' za bar neke tipove
        types = dfs.get("tsif_vrsta")
        if types is not None and "ind_polisa" in types.columns:
            active = (types["ind_polisa"] == "D").sum()
            if active == 0:
                report.warn(
                    "[tsif_vrsta] Nijedan tip polise nema ind_polisa == 'D' — "
                    "predikcija candidate tipova (cell koji filtrira aktivne tipove) će biti prazna."
                )

        # klijent_id mora se poklapati između ins_klijent i new_polisa_klijent
        ins = dfs.get("ins_klijent")
        npk = dfs.get("new_polisa_klijent")
        if ins is not None and npk is not None and "klijent_id" in ins.columns and "klijent_id" in npk.columns:
            overlap = set(ins["klijent_id"].dropna()) & set(npk["klijent_id"].dropna())
            coverage = len(overlap) / max(len(set(npk["klijent_id"].dropna())), 1)
            if coverage < 0.9:
                report.warn(
                    f"[ins_klijent <-> new_polisa_klijent] Samo {coverage:.1%} klijenata iz "
                    f"new_polisa_klijent ima odgovarajući red u ins_klijent — inner join će "
                    f"izbaciti ostatak."
                )

    def run_data_validation(self):

        report = ValidationReport()
        fill_rates: dict[str, float] = {}
        schema = self.config.schema['schema']

        for table_name in schema.keys():

            status = self.__validate_table(table_name, report, fill_rates)
            if not status:
                logger.error(f"[{table_name}] Validacija nije prošla — vidi report.")

            write_yaml(report.__dict__, self.config.report_file_path)

            html_report = validation_report_to_html(report.__dict__)
            write_into_file(html_report, self.config.report_page_file_path)


        #business_rule_checks(dfs, report)



