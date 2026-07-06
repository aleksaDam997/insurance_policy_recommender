import os
import sys

from src.insurance_policy_recommender.constants.training_pipeline import *
from src.insurance_policy_recommender.entity.artifact_entity import DataIngestionArtifact
from src.insurance_policy_recommender.entity.config_entity import DataIngestionConfig
from src.insurance_policy_recommender.exception.exception import InsurancePolicyRecommenderException
from src.insurance_policy_recommender.logging.logger import logger
from src.insurance_policy_recommender.utils.fio.fio import create_directories, copy_file

class DataIngestion: 
    def __init__(self, config: DataIngestionConfig):
        self.config = config

    def initiate_data_ingestion(self) -> DataIngestionArtifact:

        logger.info("Starting data ingestion process...")

        policy_raw_data_destination_path = self.config.raw_data_dir / POLICY_DATA_FILE_NAME
        ins_client_data_destination_path = self.config.raw_data_dir / INS_CLIENT_DATA_FILE_NAME
        policy_client_data_destination_path = self.config.raw_data_dir / POLICY_CLIENT_DATA_FILE_NAME
        policy_type_data_destination_path = self.config.raw_data_dir / POLICY_TYPE_FILE_NAME
        client_roles_data_destination_path = self.config.raw_data_dir / CLIENT_ROLES_FILE_NAME
        try:

            # Copying the source files to the raw data directory
            copy_file(self.config.source_path / self.config.policy_data_file_name, policy_raw_data_destination_path)
            copy_file(self.config.source_path / self.config.inc_client_data_file_name, ins_client_data_destination_path)
            copy_file(self.config.source_path / self.config.policy_client_data_file_name, policy_client_data_destination_path)
            copy_file(self.config.source_path / self.config.policy_type_file_name, policy_type_data_destination_path)
            copy_file(self.config.source_path / self.config.client_roles_file_name, client_roles_data_destination_path)

            logger.info("Data ingestion process completed successfully.")

        except Exception as e:
            logger.error(f"Error during data ingestion: {e}")
            raise InsurancePolicyRecommenderException(e, sys) from e

        return DataIngestionArtifact(
            policy_raw_data_destination_path,
            raw_ins_client_data_path=ins_client_data_destination_path,
            raw_policy_client_data_path=policy_client_data_destination_path,
            raw_policy_type_data_path=policy_type_data_destination_path,
            raw_client_roles_data_path=client_roles_data_destination_path
        )