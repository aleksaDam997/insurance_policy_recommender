import pandas as pd
import numpy as np
from datetime import datetime, date

class ClientFeatureSelection:
    def __init__(self, policy_client_data):
        self.policy_client_data = policy_client_data
        self.schema = dict()


    def clear_data(self):
        
        df = self.policy_client_data
        schema = self.schema

        # stranac
        # ne = not equal
        df["is_foreign"] = (
            df["br_pasosa_y"].notna() &
            df["br_pasosa_y"].str.strip().ne("")
        ).astype("int8")

        df['ind_rezident'] = df['ind_rezident'].apply(lambda x: 1 if x == 'D' else 0)
        df['ind_stranac']  = df['ind_stranac'].apply(lambda x: 1 if x == 'D' else 0)
        df['is_foreign'] = df['is_foreign'].fillna(df['ind_rezident']).fillna(df['ind_stranac'])
        
        df.drop(['ind_rezident', 'ind_stranac', 'drzava_id_x', 'drzava_id_y',
                'br_pasosa_x', 'br_pasosa_y'], axis=1, inplace=True)

        # svojina
        df['ownerType'] = df['sif_svojina'].fillna(df['osig_svojina'])
        df.loc[df['ownerType'] == 2, 'ownerType'] = 0
        
        df.drop(['sif_svojina', 'osig_svojina'], axis=1, inplace=True)

        df[['age', 'birth_place', 'gender']] = (
            df.loc[(df['ownerType'] == 1) & (df['is_foreign'] == 0), 'mat_br']
            .apply(self.extract_serial_num_data).apply(pd.Series)
        )

        # godine
        df['datum_rodjenja'] = pd.to_datetime(
            df['datum_rodjenja_x'].fillna(df['datum_rodjenja_y']), errors='coerce'
        )

        df['years'] = date.today().year - df['datum_rodjenja'].dt.year
        df['age']   = df['age'].fillna(df['years'])
        
        df.drop(['datum_rodjenja_x', 'datum_rodjenja_y', 'datum_rodjenja', 'years'], axis=1, inplace=True)

        # pol
        df.loc[df['pol_id_x'] == 2, 'pol_id_x'] = 0
        df.loc[df['pol_id_y'] == 2, 'pol_id_y'] = 0
        df['gender'] = df['gender'].fillna(df['pol_id_x']).fillna(df['pol_id_y'])
        
        df.drop(['pol_id_x', 'pol_id_y'], axis=1, inplace=True)

        # bracni status
        df['merrige_status'] = df['sif_bracni_status_x'].fillna(df['sif_bracni_status_y'])
        df.loc[df['merrige_status'] == 2, 'merrige_status'] = 0
        
        df.drop(['sif_bracni_status_x', 'sif_bracni_status_y'], axis=1, inplace=True)

        # posao
        df['unknown_job'] = df['nedef_delatnost_y'].fillna(df['nedef_delatnost_x'])
        
        df.drop(['nedef_delatnost_y', 'nedef_delatnost_x'], axis=1, inplace=True)
        
        df['job_type'] = df['sif_delatnost_y'].fillna(df['sif_delatnost_x'])
        
        df.drop(['sif_delatnost_y', 'sif_delatnost_x'], axis=1, inplace=True)

        # Vozacka dozvola
        df['driving_licence_date'] = df['dat_vozacke_y'].fillna(df['dat_vozacke_x'])
        df.drop(['dat_vozacke_y', 'dat_vozacke_x'], axis=1, inplace=True)
        
        text_cols = [
            'mat_br', 'naziv', 'naziv1', 'king_id_x', 'mesto_rodj_x', 'osig_jmbg', 'osig_naziv',
            'osig_naziv1', 'osig_ulica', 'osig_mesto', 'osig_telefon2', 'ind_info_ponuda',
            'king_id_y', 'osig_telefon1', 'osig_mail', 'mesto_rodj_y', 'procenat', 'sif_mj'
        ]
        
        df.drop([c for c in text_cols if c in df.columns], axis=1, inplace=True)
        return df

    def feature_engineering(self):
        
        df = self.policy_client_data

        # Grupe po godinama
        df['age_bucket'] = pd.cut(df['age'], bins=[0, 25, 35, 50, 65, 100], labels=[0, 1, 2, 3, 4])
        print(f'Vrijednosti age_bucket: {df["age_bucket"].value_counts()}')

        # Koliko dugo vozi + popunjavanje praznih redova
        df['driving_licence_date'] = pd.to_datetime(df['driving_licence_date'], errors='coerce')
        today_year = pd.Timestamp.today().year
        
        df['driving_experience'] = (today_year - df['driving_licence_date'].dt.year).astype(float)
        
        df['driving_experience'] = (
            df.loc[df['ownerType'] == 1, 'driving_experience']
            .fillna(df.groupby('age_bucket', observed=True)['driving_experience'].transform('median'))
            .fillna(df['driving_experience'].median())
        )

        # Bracni status popunjavanje praznih redova
        df['merrige_status'] = df['merrige_status'].astype(float)
        df['merrige_status'] = (
            df.loc[df['ownerType'] == 1, 'merrige_status']
            .fillna(
                df.groupby('age_bucket', observed=True)['merrige_status']
                .transform(lambda x: x.mode().iloc[0] if not x.mode().empty else np.nan)
            )
            .fillna(df['merrige_status'].mode().iloc[0])
        )
        
        df = df.drop('driving_licence_date', axis=1)

        return df
    
    def fix_corupted_age_values(self):

        df = self.policy_client_data

        corrupted_ids = df[(df['age'] < 18) | (df['age'] > 90)]['klijent_id'].values

        df.loc[df['klijent_id'].isin(corrupted_ids), 'age'] = \
            df.groupby(['merrige_status', 'osig_opstina'])['age'].transform('median')
        
        return df
    
    def clear_duplicates(self):

        df = self.policy_client_data

        cli_duplicates = df[df.duplicated(['klijent_id', 'ponuda_id', 'sif_uloga'])].shape[0]
        print(f' Duplikati: {cli_duplicates}')

        if cli_duplicates > 0:
            df = df.drop_duplicates(['klijent_id', 'ponuda_id', 'sif_uloga'], keep='first')

        return df
    
    def extract_serial_num_data(self, serial_number):
        
        if pd.isna(serial_number) or serial_number == '' or len(serial_number) != 13:
            return np.nan, np.nan, np.nan
            
        sn = str(serial_number).zfill(13)
        year = int(sn[4:7])
        year = year + 2000 if year < 800 else 1000 + year
        age = date.today().year - year
        birth_place = sn[7:9]
        gender = 1 if int(sn[9:12]) < 500 else 0
        return age, birth_place, gender