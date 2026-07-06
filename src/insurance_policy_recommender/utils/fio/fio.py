import json
import os
import shutil
import sys
from ensure import ensure_annotations
import yaml
from src.insurance_policy_recommender.logging.logger import logger
from src.insurance_policy_recommender.exception.exception import InsurancePolicyRecommenderException
from pathlib import Path

@ensure_annotations
def read_yaml(file_path: Path) -> dict:
    try:
        with open(file_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Error reading YAML file {file_path}: {e}")
        raise InsurancePolicyRecommenderException(e, sys) from e
    
@ensure_annotations
def write_yaml(data: dict, file_path: Path):
    try:
        with open(file_path, 'w') as file:
            yaml.safe_dump(data, file)
    except Exception as e:
        logger.error(f"Error writing YAML file {file_path}: {e}")
        raise InsurancePolicyRecommenderException(e, sys) from e

@ensure_annotations
def create_directories(path_to_directories: list, verbose: bool = True):
    """Creates directories if they do not exist.

    Args:
        path_to_directories (list[Path]): List of directory paths to create.
        verbose (bool): Whether to log the creation of directories. Defaults to True.
    Returns:
    """
    try:
        for path in path_to_directories:
            os.makedirs(path, exist_ok=True)
            if verbose:
                logger.info(f"Directory created at: {path}")
    except Exception as e:
        logger.error(f"Error creating directories: {e}")
        raise InsurancePolicyRecommenderException(e, sys) from e
    
@ensure_annotations
def make_file (file_path: Path, content: str = None):
    """Creates a file at the specified path with optional content.

    Args:
        file_path (Path): Path to the file to create.
        content (str, optional): Content to write to the file. Defaults to None.
    """
    try:
        os.makedirs(file_path.parent, exist_ok=True)
        with open(file_path, 'w') as f:
            if content:
                f.write(content)
        logger.info(f"File created at: {file_path}")
    except Exception as e:
        logger.error(f"Error creating file at {file_path}: {e}")
        raise InsurancePolicyRecommenderException(e, sys) from e

@ensure_annotations
def copy_file(file_dest: Path, copy_dest: Path):
    """Copies a file from source to destination.

    Args:
        file_dest (Path): Source file path.
        copy_dest (Path): Destination file path.
    """
    try:
        shutil.copy(file_dest, copy_dest)
        logger.info(f"File copied from {file_dest} to {copy_dest}")
    except Exception as e:
        logger.error(f"Error copying file from {file_dest} to {copy_dest}: {e}")
        raise InsurancePolicyRecommenderException(e, sys) from e

@ensure_annotations
def save_json(path: Path, data: dict):
    """Saves a dictionary as a JSON file.

    Args:
        path (Path): Path to save the JSON file.
        data (dict[str, Any]): Dictionary to save as JSON.
    """
    try:
        with open(path, 'w') as json_file:
            json.dump(data, json_file, indent=4)
        logger.info(f"JSON file saved at: {path}")
    except Exception as e:
        logger.exception(f"Error saving JSON file at: {path}")
        raise InsurancePolicyRecommenderException(e, sys) from e

@ensure_annotations
def load_json(path: Path) -> dict[str, any]:
    """Loads a JSON file and returns its contents as a dictionary.

    Args:
        path (Path): Path to the JSON file.
    Returns:
        dict[str, Any]: Dictionary containing the JSON file contents.
    try:
    """
    try:
        with open(path, 'r') as json_file:
            data = json.load(json_file)
        logger.info(f"JSON file loaded from: {path}")
        return data
    except Exception as e:
        logger.exception(f"Error loading JSON file from: {path}")
        raise InsurancePolicyRecommenderException(e, sys) from e
    

@ensure_annotations
def write_into_file(data: str, file_path: Path):
    try:
        with open(file_path, 'w') as file:
            file.write(str(data))
        logger.info(f"Data written to file at: {file_path}")
    except Exception as e:
        logger.error(f"Error writing file {file_path}: {e}")
        raise InsurancePolicyRecommenderException(e, sys) from e