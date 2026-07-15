from src.insurance_policy_recommender.components.data_validation import DataValidation
from src.insurance_policy_recommender.components.data_ingestion import DataIngestion
from src.insurance_policy_recommender.components.data_transformation.data_transformation import DataTransformation
from src.insurance_policy_recommender.logging.logger import logger
from src.insurance_policy_recommender.exception.exception import InsurancePolicyRecommenderException
from src.insurance_policy_recommender.config.configuration import ConfigurationManager
import sys

if __name__=='__main__':

    try:
        configuration_manager = ConfigurationManager()
    except Exception as e:
        logger.exception("An error occurred in the Insurance Policy Recommender application.")
        raise InsurancePolicyRecommenderException(str(e), sys)
    
    STAGE_NAME = "Data Ingestion Stage"

    try:
        logger.info(f">>>>>> Stage {STAGE_NAME} started <<<<<<")
        # Add your main application logic here

        data_ingestion_config = configuration_manager.get_data_ingestion_config()
        data_ingestion = DataIngestion(config=data_ingestion_config)
        data_ingestion_artifact = data_ingestion.initiate_data_ingestion()

        logger.info(f">>>>>> Stage {STAGE_NAME} completed <<<<<<\n\nx==========x")
    except Exception as e:
        logger.exception("An error occurred in the Insurance Policy Recommender application.")
        raise InsurancePolicyRecommenderException(str(e), sys)
    
    STAGE_NAME = "Data Validation Stage"

    try:
        logger.info(f">>>>>> Stage {STAGE_NAME} started <<<<<<")
        # Add your main application logic here

        data_validation_config = configuration_manager.get_data_validation_config()
        data_validation = DataValidation(config=data_validation_config, data_ingestion_artifact=data_ingestion_artifact)
        data_validation_artifact = data_validation.run_data_validation()

        logger.info(f">>>>>> Stage {STAGE_NAME} completed <<<<<<\n\nx==========x")
    except Exception as e:
        logger.exception("An error occurred in the Insurance Policy Recommender application.")
        raise InsurancePolicyRecommenderException(str(e), sys)
    
    STAGE_NAME = "Data Transformation Stage"

    try:
        logger.info(f">>>>>> Stage {STAGE_NAME} started <<<<<<")
        # Add your main application logic here

        data_transformation_config = configuration_manager.get_data_transformation_config()
        data_transformation = DataTransformation(data_transformation_config=data_transformation_config, data_validation_artifact=data_validation_artifact)
        data_transformation.start_data_transformation()

        logger.info(f">>>>>> Stage {STAGE_NAME} completed <<<<<<\n\nx==========x")
    except Exception as e:
        logger.exception("An error occurred in the Insurance Policy Recommender application.")
        raise InsurancePolicyRecommenderException(str(e), sys)