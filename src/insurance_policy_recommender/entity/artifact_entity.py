from pathlib import Path
class DataIngestionArtifact:
    def __init__(self, policy_raw_data_path: Path, raw_ins_client_data_path: Path, raw_policy_client_data_path: Path, raw_policy_type_data_path: Path, raw_client_roles_data_path: Path):
        self.policy_raw_data_path = policy_raw_data_path
        self.raw_ins_client_data_path = raw_ins_client_data_path
        self.raw_policy_client_data_path = raw_policy_client_data_path
        self.raw_policy_type_data_path = raw_policy_type_data_path
        self.raw_client_roles_data_path = raw_client_roles_data_path

class DataValidationArtifact:
    def __init__(self, report_file_path: Path, report_page_file_path: Path, policy_raw_data_path: Path, raw_ins_client_data_path: Path, raw_policy_client_data_path: Path,
                 raw_policy_type_data_path: Path, raw_client_roles_data_path: Path):
        
        self.report_file_path = report_file_path
        self.report_page_file_path = report_page_file_path

        self.policy_raw_data_path = policy_raw_data_path
        self.raw_ins_client_data_path = raw_ins_client_data_path
        self.raw_policy_client_data_path = raw_policy_client_data_path
        self.raw_policy_type_data_path = raw_policy_type_data_path
        self.raw_client_roles_data_path = raw_client_roles_data_path

class DataTransformationArtifact:
    def __init__(self):
        pass