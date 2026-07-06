from pathlib import Path
class DataIngestionArtifact:
    def __init__(self, policy_raw_data_path: Path, raw_ins_client_data_path: Path, raw_policy_client_data_path: Path, raw_policy_type_data_path: Path, raw_client_roles_data_path: Path):
        self.policy_raw_data_path = policy_raw_data_path
        self.raw_ins_client_data_path = raw_ins_client_data_path
        self.raw_policy_client_data_path = raw_policy_client_data_path
        self.raw_policy_type_data_path = raw_policy_type_data_path
        self.raw_client_roles_data_path = raw_client_roles_data_path