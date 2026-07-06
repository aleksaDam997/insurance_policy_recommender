import os
from pathlib import Path
from src.insurance_policy_recommender.utils.fio.fio import read_yaml
from src.insurance_policy_recommender.logging.logger import logger
from src.insurance_policy_recommender.constants import *
from src.insurance_policy_recommender.constants.training_pipeline import *
from src.insurance_policy_recommender.entity.config_entity import DataIngestionConfig, DataValidationConfig
from src.insurance_policy_recommender.utils.fio.fio import create_directories, read_yaml, write_yaml, copy_file

class ConfigurationManager:

    def __init__(self, config_filepath = CONFIG_FILE_PATH, params_filepath = PARAMS_FILE_PATH, schema_filepath = SCHEMA_FILE_PATH):
        self.config = read_yaml(config_filepath)
        self.params = read_yaml(params_filepath)
        self.schema = read_yaml(schema_filepath)
      
        os.makedirs(self.config['artifacts_root'], exist_ok=True)
        logger.info(f"Created artifacts root directory at: {self.config['artifacts_root']}")

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