import os
from pathlib import Path
from src.insurance_policy_recommender.utils.fio.fio import read_yaml
from src.insurance_policy_recommender.logging.logger import logger
from src.insurance_policy_recommender.constants import *
from src.insurance_policy_recommender.constants.training_pipeline import *
from src.insurance_policy_recommender.entity.config_entity import DataIngestionConfig, DataValidationConfig, DataTransformationConfig
from src.insurance_policy_recommender.utils.fio.fio import create_directories, read_yaml, write_yaml, copy_file

class ConfigurationManager:

    def __init__(self, config_filepath = CONFIG_FILE_PATH, params_filepath = PARAMS_FILE_PATH, schema_filepath = SCHEMA_FILE_PATH):
        self.config = read_yaml(config_filepath)
        self.params = read_yaml(params_filepath)
        self.schema = read_yaml(schema_filepath)
      
        os.makedirs(self.config['artifacts_root'], exist_ok=True)
        logger.info(f"Created artifacts root directory at: {self.config['artifacts_root']}")
        self.log_system_params()

    def get_data_ingestion_config(self) -> DataIngestionConfig:

        config = self.config['data_ingestion']

        create_directories([Path(config['root_dir']), Path(config['raw_data_dir'])], verbose=True)

        data_ingestion_config = DataIngestionConfig(
            root_dir=Path(config['root_dir']),
            raw_data_dir=Path(config['raw_data_dir']),

            source_path = Path(config['source_path']),

            policy_data_file_name = POLICY_DATA_FILE_NAME,
            inc_client_data_file_name= INS_CLIENT_DATA_FILE_NAME,
            policy_client_data_file_name= POLICY_CLIENT_DATA_FILE_NAME,
            policy_type_file_name= POLICY_TYPE_FILE_NAME,
            client_roles_file_name=CLIENT_ROLES_FILE_NAME
        )

        return data_ingestion_config
    
    def get_data_validation_config(self):
        config = self.config['data_validation']

        create_directories([Path(config['root_dir'])], verbose=True)

        data_validation_config = DataValidationConfig(
            root_dir=Path(config['root_dir']),
            report_file_path=Path(config['report_file_path']),
            report_page_file_path=Path(config['report_page_file_path']),
            schema=self.schema
        )

        return data_validation_config
    
    def get_data_transformation_config(self):
        
        config = self.config['data_transformation']
        create_directories([Path(config['root_dir'])], verbose=True)

        data_transformation_config = DataTransformationConfig(
            root_dir=Path(config['root_dir']),
            training_data=Path(config['training_data']),
            schema=self.schema
        )

        return data_transformation_config
    

    def log_system_params(self):

        params = self.params
        __TRAIN_MODEL = True

        # Validacija konfiguracije
        assert not (
            params["USE_APRIORI_AS_FEATURE"]
            and params["BLEND_APRIORI"]
        ), "Odaberi jedan mod: USE_APRIORI_AS_FEATURE ili BLEND_APRIORI, ne oba."

        assert not (
            params["USE_MARKOV_PROBS_AS_FEATURE"]
            and params["BLEND_MARKOV_PROBS"]
        ), "Markov ne može biti i feature i blend signal istovremeno."

        assert not (
            params["INCLUDE_SEGMENT_MARKOV"]
            and params["BLEND_MARKOV_PROBS"]
        ), "Segment Markov kao feature i BLEND_MARKOV_PROBS su redundantni."

        total_weight = (
            params["HR3_WEIGHT"]
            + params["MRR5_WEIGHT"]
            + params["NDCG3_WEIGHT"]
        )

        assert abs(total_weight - 1.0) < 1e-9, (
            f"HR3_WEIGHT + MRR5_WEIGHT + NDCG3_WEIGHT "
            f"mora biti 1.0, trenutno: {total_weight}"
        )

        assert (
            0.0 <= params["HR3_WEIGHT"] <= 1.0
            and 0.0 <= params["MRR5_WEIGHT"] <= 1.0
            and 0.0 <= params["NDCG3_WEIGHT"] <= 1.0
        ), "Weightovi moraju biti između 0 i 1."

        print("✅ Konstante validne:")
        print(f"   USE_APRIORI_AS_FEATURE      = {params['USE_APRIORI_AS_FEATURE']}")
        print(f"   BLEND_APRIORI               = {params['BLEND_APRIORI']}")
        print(f"   BLEND_MARKOV_PROBS          = {params['BLEND_MARKOV_PROBS']}")
        print(f"   INCLUDE_SEGMENT_MARKOV      = {params['INCLUDE_SEGMENT_MARKOV']}")
        print(f"   USE_MARKOV_PROBS_AS_FEATURE = {params['USE_MARKOV_PROBS_AS_FEATURE']}")
        print(f"   INCLUDE_CLIENT_CLUSTERS     = {params['INCLUDE_CLIENT_CLUSTERS']}")
        print(f"   INCLUDE_RENEWAL_FEATURES    = {params['INCLUDE_RENEWAL_FEATURES']}")
        print(f"   INCLUDE_SEASONAL_FEATURES   = {params['INCLUDE_SEASONAL_FEATURES']}")
        print(f"   INCLUDE_POPULARITY_FEATURES = {params['INCLUDE_POPULARITY_FEATURES']}")
        print(f"   DO_NEGATIVE_SAMPLING        = {params['DO_NEGATIVE_SAMPLING']}")
        print(f"   EMB_COMPONENTS              = {params['EMB_COMPONENTS']}")

        logger.info("✅ Konstante validne:")
        logger.info(f"   USE_APRIORI_AS_FEATURE      = {params['USE_APRIORI_AS_FEATURE']}")
        logger.info(f"   BLEND_APRIORI               = {params['BLEND_APRIORI']}")
        logger.info(f"   BLEND_MARKOV_PROBS          = {params['BLEND_MARKOV_PROBS']}")
        logger.info(f"   INCLUDE_SEGMENT_MARKOV      = {params['INCLUDE_SEGMENT_MARKOV']}")
        logger.info(f"   USE_MARKOV_PROBS_AS_FEATURE = {params['USE_MARKOV_PROBS_AS_FEATURE']}")
        logger.info(f"   INCLUDE_CLIENT_CLUSTERS     = {params['INCLUDE_CLIENT_CLUSTERS']}")
        logger.info(f"   INCLUDE_RENEWAL_FEATURES    = {params['INCLUDE_RENEWAL_FEATURES']}")
        logger.info(f"   INCLUDE_SEASONAL_FEATURES   = {params['INCLUDE_SEASONAL_FEATURES']}")
        logger.info(f"   INCLUDE_POPULARITY_FEATURES = {params['INCLUDE_POPULARITY_FEATURES']}")
        logger.info(f"   DO_NEGATIVE_SAMPLING        = {params['DO_NEGATIVE_SAMPLING']}")
        logger.info(f"   EMB_COMPONENTS              = {params['EMB_COMPONENTS']}")

        print(
            f"   Optuna loss: "
            f"{params['HR3_WEIGHT']}×HR@3 + "
            f"{params['MRR5_WEIGHT']}×MRR@5 + "
            f"{params['NDCG3_WEIGHT']}×NDCG@3"
        )

        print(
            f"   MODEL PARTICIPATION:"
            f" W_LGBM={params['W_LGBM']},"
            f" W_XGBM={params['W_XGBM']},"
            f" W_CAT={params['W_CAT']},"
            f" W_MARKOV={params['W_MARKOV']},"
            f" W_APRIORI={params['W_APRIORI']}"
        )

        logger.info(
            f"   Optuna loss: "
            f"{params['HR3_WEIGHT']}×HR@3 + "
            f"{params['MRR5_WEIGHT']}×MRR@5 + "
            f"{params['NDCG3_WEIGHT']}×NDCG@3"
        )

        logger.info(
            f"   MODEL PARTICIPATION:"
            f" W_LGBM={params['W_LGBM']},"
            f" W_XGBM={params['W_XGBM']},"
            f" W_CAT={params['W_CAT']},"
            f" W_MARKOV={params['W_MARKOV']},"
            f" W_APRIORI={params['W_APRIORI']}"
        )

        print("\n" + "=" * 80)
        logger.info("\n" + "=" * 80)

        if __TRAIN_MODEL:
            print("MODUL: TRENIRANJE MODELA (od početka)")
            logger.info("MODUL: TRENIRANJE MODELA (od početka)")
        else:
            print("MODUL: UČITAVANJE PRE-TRENIRANIH MODELA (preskakanje treniranja)")
            logger.info("MODUL: UČITAVANJE PRE-TRENIRANIH MODELA (preskakanje treniranja)")

        print("=" * 80)
        logger.info("=" * 80)