from pathlib import Path

class DataIngestionConfig:
    def __init__(self, root_dir: Path, source_path: Path, raw_data_dir: Path, policy_data_file_name: Path = None, 
                 inc_client_data_file_name: Path = None, policy_client_data_file_name: Path = None, 
                 policy_type_file_name: Path = None, client_roles_file_name: Path = None):
        
        self.root_dir = root_dir
        self.raw_data_dir = raw_data_dir
        self.source_path = source_path

        self.policy_data_file_name = policy_data_file_name
        self.inc_client_data_file_name = inc_client_data_file_name
        self.policy_client_data_file_name = policy_client_data_file_name
        self.policy_type_file_name = policy_type_file_name
        self.client_roles_file_name = client_roles_file_name

class DataValidationConfig:
    def __init__(self, root_dir: Path, report_file_path: Path, report_page_file_path: Path, schema: dict):
        self.root_dir = root_dir
        self.report_file_path = report_file_path
        self.report_page_file_path = report_page_file_path
        self.schema = schema