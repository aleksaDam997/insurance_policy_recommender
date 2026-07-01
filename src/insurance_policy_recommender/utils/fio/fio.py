import yaml
from insurance_policy_recommender.exception.exception import InsurancePolicyRecommenderException
import src.insurance_policy_recommender.logging.logger as logger
import src.insurance_policy_recommender.exception
from pathlib import Path


def read_yaml(file_path: Path) -> dict:
    try:
        with open(file_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Error reading YAML file {file_path}: {e}")
        raise

def write_yaml(data: dict, file_path: Path) -> None:
    try:
        with open(file_path, 'w') as file:
            yaml.safe_dump(data, file)
    except Exception as e:
        logger.error(f"Error writing YAML file {file_path}: {e}")
        raise

