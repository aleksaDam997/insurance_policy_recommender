import pandas as pd

class PolicyClientFeatureSelection:
    def __init__(self, policy_client_data: pd.DataFrame):
        self.policy_client_data = policy_client_data

    def clear_policy_client_data_excess_columns(self):
    
        df = self.policy_client_data

        cols_to_delete = [
            'sif_preuzmi', 'preuzmi_no', 'preuzmi_id', 'ugo_jmbg', 'ugo_svojina', 'ugo_naziv',
            'ugo_naziv1', 'ugo_ulica', 'ugo_kuc_br', 'ugo_mesto', 'ugo_posta', 'ugo_kanton',
            'ugo_opstina', 'ugo_mesto_id', 'ugo_telefon1', 'ugo_telefon2', 'ugo_mail',
            'osig_jmbg', 'osig_svojina', 'osig_naziv', 'osig_naziv1', 'osig_ulica',
            'osig_kuc_br_x', 'osig_mesto', 'osig_posta_x', 'osig_kanton_x', 'osig_opstina_x',
            'osig_mesto_id_x', 'osig_telefon1', 'osig_telefon2', 'osig_mail', 'mesto_izdavanja',
            'miro_polisa_no', 'sif_ikanton', 'sif_iopstina', 'ugo_del', 'king_id',
            'ugo_br_pasosa', 'osig_br_pasosa', 'registarski_broj_polise', 'akcija_id', 
            'polisa_id', 'polisa_no', 'broker_id', 'sif_trajanja',
            # 'dat_od_ug', 'dat_do_ug', 
            'dat_od', 'dat_do', 'time_od', 'time_do',
            'br_dana', 'mjesto_izdavanja', 'napomena',
            'napomena_auto', 'napomena1', 'p_oper', 'p_date', 'p_session_id',  'sif_napomena', 'opis_osiguravac', 
            'veza_polise_no', 'ind_uw_kontrola', 'ugo_isprava',
            'osig_isprava', 'sif_datum_dospeca', 'sif_bankovni_racun', 'redni_br', 'osig_kuc_br_y',
            'osig_posta_y', 
            #'osig_kanton_y', 'osig_opstina_y', 
            'osig_mesto_id_y',
            'dat_prve_rate', 'ind_obracun', 'ind_nepravilni_otp_plan'
        ]

        return df.drop([c for c in cols_to_delete if c in df.columns], axis=1)