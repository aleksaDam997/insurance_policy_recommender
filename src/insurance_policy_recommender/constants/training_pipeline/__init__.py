from pathlib import Path

POLICY_DATA_FILE_NAME = Path("new_polisa.csv")
INS_CLIENT_DATA_FILE_NAME = Path("__ins_klijenti.csv")
POLICY_CLIENT_DATA_FILE_NAME = Path("new_polisa_klijent.csv")
POLICY_TYPE_FILE_NAME = Path("tsif_vrsta.csv")
CLIENT_ROLES_FILE_NAME = Path("new_polisa_uloga.csv")





TABLE_NAME_TO_PATH_MAP = {
    "new_polisa": "policy_raw_data_path",
    "ins_klijent": "raw_ins_client_data_path",
    "new_polisa_klijent": "raw_policy_client_data_path",
    "tsif_vrsta": "raw_policy_type_data_path",
    "new_polisa_uloga": "raw_client_roles_data_path"
}