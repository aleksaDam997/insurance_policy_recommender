from src.insurance_policy_recommender.entity.artifact_entity import DataValidationArtifact
from src.insurance_policy_recommender.entity.config_entity import DataTransformationConfig
from src.insurance_policy_recommender.exception.exception import InsurancePolicyRecommenderException
from src.insurance_policy_recommender.utils.fio.dataset import load_csv_with_valid_columns
from src.insurance_policy_recommender.logging.logger import logger
from src.insurance_policy_recommender.utils.utils import build_complete_record
from src.insurance_policy_recommender.components.data_transformation.client_feature_selection import ClientFeatureSelection
from src.insurance_policy_recommender.components.data_transformation.policy_client_feature_selection import PolicyClientFeatureSelection
from src.insurance_policy_recommender.utils.debugg.debugg import plot_column_fill_rate

import sys
from pathlib import Path
import pandas as pd

class DataTransformation:
    def __init__(self, data_validation_artifact: DataValidationArtifact, data_transformation_config: DataTransformationConfig):
        self.data_validation_artifact = data_validation_artifact
        self.data_transformation_config = data_transformation_config

    def start_data_transformation(self):

        schema = self.data_transformation_config.schema['schema']

        np_schema = schema['new_polisa']['columns']
        np_path = self.data_validation_artifact.policy_raw_data_path

        policy_data = load_csv_with_valid_columns(np_schema, np_path)

        npk_schema = schema['new_polisa_klijent']['columns']
        npk_path = self.data_validation_artifact.raw_policy_client_data_path

        np_cli_data = load_csv_with_valid_columns(npk_schema, npk_path)

        ins_cli_schema = schema['ins_klijent']['columns']
        ins_cli_path = self.data_validation_artifact.raw_ins_client_data_path

        ins_cli_data = load_csv_with_valid_columns(ins_cli_schema, ins_cli_path)

        npu_schema = schema['new_polisa_uloga']['columns']
        npu_path = self.data_validation_artifact.raw_client_roles_data_path

        cli_roles = load_csv_with_valid_columns(npu_schema, npu_path)

        policy_type = schema['tsif_vrsta']['columns']
        policy_type_path = self.data_validation_artifact.raw_policy_type_data_path

        policy_types = load_csv_with_valid_columns(policy_type, policy_type_path)

        print(policy_types.head(5))

        # ============================================================
        # POLISE OSTAVLJAMO KVALITET
        # ============================================================

        policy_data = policy_data[(policy_data['polisa_id'].notna() & policy_data['polisa_id'] != 0)]
        policy_data = policy_data.drop_duplicates('polisa_id', keep='first')
        policy_data['dat_izdavanja'] = pd.to_datetime(policy_data['dat_izdavanja'])
        policy_data['godina']    = policy_data['dat_izdavanja'].dt.year
        policy_data['days_old']  = (pd.Timestamp.today() - policy_data['dat_izdavanja']).dt.days
        policy_data['years_old'] = policy_data['days_old'] / 365.25

        # ============================================================
        # KLIJENTI PROCESUIRANJE
        # ============================================================
        cli_data = ins_cli_data.merge(np_cli_data, on="klijent_id", how="inner")
        cli_data = build_complete_record(cli_data, 'klijent_id')

        cli_data = cli_data.merge(
            np_cli_data[['klijent_id', 'ponuda_id', 'sif_uloga']], on='klijent_id', how='inner'
        )

        cli_data['ponuda_id'] = cli_data['ponuda_id_y']
        cli_data['sif_uloga'] = cli_data['sif_uloga_y']
        cli_data = cli_data.drop(['ponuda_id_y', 'ponuda_id_x', 'sif_uloga_y', 'sif_uloga_x'], axis=1)

        feature_selection = ClientFeatureSelection(cli_data)

        cli_data = feature_selection.clear_data()

        cli_data = feature_selection.fix_corupted_age_values()

        cli_data = feature_selection.feature_engineering()

        cli_data = feature_selection.clear_duplicates()

        columns_to_check = [
            c for c in cli_data.columns
            if c not in ['ponuda_id', 'redni_br', 'klijent_id']
        ]
        print("Ukupno kolona: ", len(columns_to_check))
        plot_column_fill_rate(cli_data, columns_to_check)

        cli_data = cli_data.drop(['unknown_job', 'job_type'], axis=1)

        policy_client_data = policy_data.merge(cli_data, on='ponuda_id', how='inner')

        cli_roles = cli_roles[cli_roles['opis'].str.contains('Ugovarač', na=False)]

        policy_client_data = policy_client_data[
            policy_client_data['sif_uloga'].isin(cli_roles['sif_uloga'].values)
        ]

        pc_feature_selection = PolicyClientFeatureSelection(policy_client_data)

        policy_client_data = pc_feature_selection.clear_policy_client_data_excess_columns()

        cols_to_check = [c for c in policy_client_data.columns if c not in ['ponuda_id', 'klijent_id']]
        plot_column_fill_rate(policy_client_data, policy_client_data.columns)




