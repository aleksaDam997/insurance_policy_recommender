import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import math
from datetime import date
from tqdm import tqdm
from collections import Counter
import psutil
import shutil
import gc
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from lightgbm import LGBMRanker, early_stopping, log_evaluation
tqdm.pandas()

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_rows', 20)

# ============================================================
# UCITAVANJE
# ============================================================
policy_data = pd.read_csv('../data/data_from_db_as_csv/new_polisa_202603141519.csv', dtype={
    'ponuda_id': 'Int32', 'ugo_jmbg': str
})
ins_cli_data = pd.read_csv('../data/data_from_db_as_csv/__ins_klijenti__202603141320.csv', dtype={
    'mat_br': str, 'klijent_id': 'Int32'
})
np_cli_data = pd.read_csv('../data/data_from_db_as_csv/new_polisa_klijent_202603141515.csv', dtype={
    'osig_jmbg': str, 'klijent_id': 'Int32', 'ponuda_id': 'Int32'
})
cli_roles = pd.read_csv('../data/data_from_db_as_csv/new_polisa_uloga_202603172039.csv')

# ============================================================
# POMOCNE FUNKCIJE
# ============================================================
process = psutil.Process(os.getpid())

def get_ram_mb():
    return process.memory_info().rss / 1024 / 1024

def print_duplicates(df, subset):
    print(f"\n### DUPLICATES: {subset} ###")
    print("Ukupno:", df.duplicated(subset=subset).sum())
    print("Grupa:", df.groupby(subset).size().gt(1).sum())
    print("Redova u grupama:", df[df.duplicated(subset=subset, keep=False)].shape[0])

def show_cli_policy_distribution(df):
    sns.set_style("darkgrid")
    policy_counts = df.groupby('klijent_id').size()
    data = {"Only 1 policy": (policy_counts == 1).sum(),
            "More than 1 policy": (policy_counts > 1).sum()}
    plot_df = pd.DataFrame({"category": list(data.keys()), "value": list(data.values())})
    plt.figure(figsize=(8, 6))
    ax = sns.barplot(data=plot_df, x="category", y="value", hue="category",
                     palette=["#4C78A8", "#F58518"], legend=False)
    for p in ax.patches:
        ax.annotate(f'{int(p.get_height()):,}',
                    (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='bottom', fontsize=11)
    plt.title("Distribution of Clients by Number of Policies", fontsize=14, weight='bold')
    plt.tight_layout()
    plt.show()

# ============================================================
# CISCENJE POLICY DATA
# ============================================================
policy_data = policy_data[(policy_data['polisa_id'].notna() & policy_data['polisa_id'] != 0)]
policy_data = policy_data.drop_duplicates('polisa_id', keep='first')
policy_data['dat_izdavanja'] = pd.to_datetime(policy_data['dat_izdavanja'])
policy_data['godina']    = policy_data['dat_izdavanja'].dt.year
policy_data['days_old']  = (pd.Timestamp.today() - policy_data['dat_izdavanja']).dt.days
policy_data['years_old'] = policy_data['days_old'] / 365.25

# ============================================================
# KLIJENTI
# ============================================================
def gather_cli_info_fastest(df):
    df = df.sort_values('klijent_id')
    df_filled = df.groupby('klijent_id').transform('bfill')
    df_filled['klijent_id'] = df['klijent_id'].values
    return df_filled.drop_duplicates('klijent_id', keep='first')

def extract_serial_num_data(serial_number):
    if pd.isna(serial_number) or serial_number == '' or len(serial_number) != 13:
        return np.nan, np.nan, np.nan
    sn = str(serial_number).zfill(13)
    year = int(sn[4:7])
    year = year + 2000 if year < 800 else 1000 + year
    age = date.today().year - year
    birth_place = sn[7:9]
    gender = 1 if int(sn[9:12]) < 500 else 0
    return age, birth_place, gender

def clear_data(df):
    df = df.copy()
    df['is_foreign'] = df['br_pasosa_y'].apply(lambda x: 1 if pd.notna(x) and x != '' else 0)
    df['ind_rezident'] = df['ind_rezident'].apply(lambda x: 1 if x == 'D' else 0)
    df['ind_stranac']  = df['ind_stranac'].apply(lambda x: 1 if x == 'D' else 0)
    df['is_foreign'] = df['is_foreign'].fillna(df['ind_rezident']).fillna(df['ind_stranac'])
    df.drop(['ind_rezident', 'ind_stranac', 'drzava_id_x', 'drzava_id_y',
             'br_pasosa_x', 'br_pasosa_y'], axis=1, inplace=True)
    df['ownerType'] = df['sif_svojina'].fillna(df['osig_svojina'])
    df.loc[df['ownerType'] == 2, 'ownerType'] = 0
    df.drop(['sif_svojina', 'osig_svojina'], axis=1, inplace=True)
    df[['age', 'birth_place', 'gender']] = (
        df.loc[(df['ownerType'] == 1) & (df['is_foreign'] == 0), 'mat_br']
        .apply(extract_serial_num_data).apply(pd.Series)
    )
    df['datum_rodjenja'] = pd.to_datetime(
        df['datum_rodjenja_x'].fillna(df['datum_rodjenja_y']), errors='coerce'
    )
    df['years'] = date.today().year - df['datum_rodjenja'].dt.year
    df['age']   = df['age'].fillna(df['years'])
    df.drop(['datum_rodjenja_x', 'datum_rodjenja_y', 'datum_rodjenja', 'years'], axis=1, inplace=True)
    df.loc[df['pol_id_x'] == 2, 'pol_id_x'] = 0
    df.loc[df['pol_id_y'] == 2, 'pol_id_y'] = 0
    df['gender'] = df['gender'].fillna(df['pol_id_x']).fillna(df['pol_id_y'])
    df.drop(['pol_id_x', 'pol_id_y'], axis=1, inplace=True)
    df['merrige_status'] = df['sif_bracni_status_x'].fillna(df['sif_bracni_status_y'])
    df.loc[df['merrige_status'] == 2, 'merrige_status'] = 0
    df.drop(['sif_bracni_status_x', 'sif_bracni_status_y'], axis=1, inplace=True)
    df['unknown_job'] = df['nedef_delatnost_y'].fillna(df['nedef_delatnost_x'])
    df.drop(['nedef_delatnost_y', 'nedef_delatnost_x'], axis=1, inplace=True)
    df['job_type'] = df['sif_delatnost_y'].fillna(df['sif_delatnost_x'])
    df.drop(['sif_delatnost_y', 'sif_delatnost_x'], axis=1, inplace=True)
    df['driving_licence_date'] = df['dat_vozacke_y'].fillna(df['dat_vozacke_x'])
    df.drop(['dat_vozacke_y', 'dat_vozacke_x'], axis=1, inplace=True)
    text_cols = [
        'mat_br', 'naziv', 'naziv1', 'king_id_x', 'mesto_rodj_x', 'osig_jmbg', 'osig_naziv',
        'osig_naziv1', 'osig_ulica', 'osig_mesto', 'osig_telefon2', 'ind_info_ponuda',
        'king_id_y', 'osig_telefon1', 'osig_mail', 'mesto_rodj_y', 'procenat', 'sif_mj'
    ]
    df.drop([c for c in text_cols if c in df.columns], axis=1, inplace=True)
    return df

def feature_engineering(df):
    df = df.copy()
    df['age_bucket'] = pd.cut(df['age'], bins=[0, 25, 35, 50, 65, 100], labels=[0, 1, 2, 3, 4])
    df['driving_licence_date'] = pd.to_datetime(df['driving_licence_date'], errors='coerce')
    today_year = pd.Timestamp.today().year
    df['driving_experience'] = (today_year - df['driving_licence_date'].dt.year).astype(float)
    df['driving_experience'] = (
        df['driving_experience']
        .fillna(df.groupby('age_bucket', observed=True)['driving_experience'].transform('median'))
        .fillna(df['driving_experience'].median())
    )
    df['merrige_status'] = df['merrige_status'].astype(float)
    df['merrige_status'] = (
        df['merrige_status']
        .fillna(df.groupby('age_bucket', observed=True)['merrige_status'].transform('median'))
        .fillna(df['merrige_status'].median())
    )
    df = df.drop('driving_licence_date', axis=1)
    return df

cli_data = ins_cli_data.merge(np_cli_data, on="klijent_id", how="inner")
cli_data = gather_cli_info_fastest(cli_data)
cli_data = clear_data(cli_data)

corrupted_ids = cli_data[(cli_data['age'] < 18) | (cli_data['age'] > 90)]['klijent_id'].values
cli_data.loc[cli_data['klijent_id'].isin(corrupted_ids), 'age'] = \
    cli_data.groupby(['merrige_status', 'osig_opstina'])['age'].transform('median')

cli_data = cli_data.drop(['unknown_job', 'job_type'], axis=1)
cli_data = feature_engineering(cli_data)

cli_data = cli_data.merge(
    np_cli_data[['klijent_id', 'ponuda_id', 'sif_uloga']], on='klijent_id', how='inner'
)
cli_data['ponuda_id'] = cli_data['ponuda_id_y']
cli_data['sif_uloga'] = cli_data['sif_uloga_y']
cli_data = cli_data.drop(['ponuda_id_y', 'ponuda_id_x', 'sif_uloga_y', 'sif_uloga_x'], axis=1)

cli_duplicates = cli_data[cli_data.duplicated(['klijent_id', 'ponuda_id', 'sif_uloga'])].shape[0]
if cli_duplicates > 0:
    cli_data = cli_data.drop_duplicates(['klijent_id', 'ponuda_id', 'sif_uloga'], keep='first')

policy_client_data = policy_data.merge(cli_data, on='ponuda_id', how='inner')
cli_roles = cli_roles[cli_roles['opis'].str.contains('Ugovarač', na=False)]
policy_client_data = policy_client_data[
    policy_client_data['sif_uloga'].isin(cli_roles['sif_uloga'].values)
]

def clean_policy_client_data(df):
    cols_to_delete = [
        'sif_preuzmi', 'preuzmi_no', 'preuzmi_id', 'ugo_jmbg', 'ugo_svojina', 'ugo_naziv',
        'ugo_naziv1', 'ugo_ulica', 'ugo_kuc_br', 'ugo_mesto', 'ugo_posta', 'ugo_kanton',
        'ugo_opstina', 'ugo_mesto_id', 'ugo_telefon1', 'ugo_telefon2', 'ugo_mail',
        'osig_jmbg', 'osig_svojina', 'osig_naziv', 'osig_naziv1', 'osig_ulica',
        'osig_kuc_br_x', 'osig_mesto', 'osig_posta_x', 'osig_kanton_x', 'osig_opstina_x',
        'osig_mesto_id_x', 'osig_telefon1', 'osig_telefon2', 'osig_mail', 'mesto_izdavanja',
        'miro_polisa_no', 'sif_ikanton', 'sif_iopstina', 'ugo_del', 'king_id',
        'ugo_br_pasosa', 'osig_br_pasosa', 'registarski_broj_polise', 'akcija_id'
    ]
    return df.drop([c for c in cols_to_delete if c in df.columns], axis=1)

policy_client_data = clean_policy_client_data(policy_client_data)

ins_cli_data = None
np_cli_data  = None
cli_roles    = None
cli_data     = None
gc.collect()

# ============================================================
# NOVO: KMEANS KLIJENTSKI KLASTERI
# Grupiramo klijente po ponašanju - koje tipove polisa imaju,
# starost, regija. Model tada uci per-klaster obrasce.
# Gradi se na CIJELOM df prije splita (demografija ne leakuje).
# ============================================================
def build_client_clusters(df, n_clusters=8, random_state=42):
    """
    Kreira KMeans klastere klijenata na osnovu:
    - Portfolio profila (udio svakog tipa polise)
    - Demografije (age, gender, ownerType, merrige_status)
    - Geografije (osig_opstina_y)
    - Aktivnosti (broj polisa ukupno)

    Vraca dict: klijent_id -> cluster_id
    """
    print(f"   Gradim {n_clusters} klijentskih klastera...")

    # Portfolio: udio svakog tipa polise po klijentu
    portfolio = (
        df.groupby(['klijent_id', 'sif_vrsta'])
        .size()
        .unstack(fill_value=0)
    )
    portfolio = portfolio.div(portfolio.sum(axis=1), axis=0)
    portfolio.columns = [f'portfolio_type_{c}' for c in portfolio.columns]

    # Demografija - uzmi zadnji poznati red po klijentu
    demo_cols = ['klijent_id', 'age', 'gender', 'ownerType', 'merrige_status']
    demo = (
        df[demo_cols]
        .sort_values('klijent_id')
        .drop_duplicates('klijent_id', keep='last')
        .set_index('klijent_id')
        .fillna(0)
    )

    # Aktivnost
    activity = df.groupby('klijent_id').agg(
        total_policies=('polisa_id', 'count'),
        unique_types=('sif_vrsta', 'nunique'),
        avg_premium=('premija_ukupno', 'mean')
    )

    # Spoji sve
    cluster_df = portfolio.join(demo, how='left').join(activity, how='left').fillna(0)

    # Skaliraj
    scaler    = StandardScaler()
    X_cluster = scaler.fit_transform(cluster_df)

    # KMeans
    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    kmeans.fit(X_cluster)

    cluster_map = dict(zip(cluster_df.index, kmeans.labels_))
    print(f"   Klasteri velicina: {pd.Series(kmeans.labels_).value_counts().sort_index().to_dict()}")

    return cluster_map, kmeans, scaler, cluster_df.columns.tolist()

# ============================================================
# MARKOV SA VREMENSKIM DECAY-OM (ukljucuje obnove)
# ============================================================
def _build_markov_with_decay(df, half_life_days=365):
    today = df['dat_izdavanja'].max()
    rows  = []
    for _, g in df.groupby('klijent_id'):
        g     = g.sort_values('dat_izdavanja')
        types = g['sif_vrsta'].tolist()
        dates = g['dat_izdavanja'].tolist()
        for i in range(len(types) - 1):
            days_ago   = (today - dates[i + 1]).days
            weight     = 2 ** (-days_ago / half_life_days)
            is_renewal = 1 if types[i] == types[i + 1] else 0
            rows.append((types[i], types[i + 1], weight, is_renewal))

    out = pd.DataFrame(rows, columns=['from_type', 'to_type', 'weight', 'is_renewal'])
    grouped = out.groupby(['from_type', 'to_type']).agg(
        weight=('weight', 'sum'),
        is_renewal=('is_renewal', 'first')
    ).reset_index()
    grouped['prob'] = grouped.groupby('from_type')['weight'].transform(lambda x: x / x.sum())
    return grouped.drop('weight', axis=1)

# ============================================================
# FUTURE PAIRS (ukljucuje obnove)
# ============================================================
def _build_future_pairs(df):
    df   = df.sort_values(['klijent_id', 'dat_izdavanja', 'ponuda_id']).copy()
    rows = []
    for _, g in df.groupby('klijent_id'):
        g          = g.sort_values(['dat_izdavanja', 'ponuda_id'])
        ponuda_ids = g['ponuda_id'].tolist()
        types      = g['sif_vrsta'].tolist()
        for i in range(len(types) - 1):
            is_renewal = 1 if types[i] == types[i + 1] else 0
            rows.append((ponuda_ids[i], types[i + 1], is_renewal))
    return (
        pd.DataFrame(rows, columns=['ponuda_id', 'candidate_type', 'is_renewal'])
        .drop_duplicates(subset=['ponuda_id', 'candidate_type'])
        .assign(label=1)
    )

# ============================================================
# CLIENT HISTORY MATRIX (odvojeno za svaki fold - nema leakage-a)
# ============================================================
def _build_client_history_matrix(df):
    df        = df.sort_values(['klijent_id', 'dat_izdavanja']).copy()
    dummies   = pd.get_dummies(df['sif_vrsta'], prefix='type')
    hist      = pd.concat(
        [df[['klijent_id', 'dat_izdavanja', 'ponuda_id']].reset_index(drop=True),
         dummies.reset_index(drop=True)], axis=1
    )
    feat_cols = dummies.columns
    hist[feat_cols] = (
        hist.groupby(hist['klijent_id'])[feat_cols]
        .cumsum()
        .groupby(hist['klijent_id'])
        .shift(1)
        .fillna(0)
    )
    return hist.drop(columns=['klijent_id', 'dat_izdavanja'])

# ============================================================
# RENEWAL FEATURES
# ============================================================
def add_renewal_features(df):
    df = df.copy().sort_values(['klijent_id', 'sif_vrsta', 'dat_izdavanja'])
    df['days_since_same_type'] = (
        df.groupby(['klijent_id', 'sif_vrsta'])['dat_izdavanja'].diff().dt.days
    )
    df['likely_annual_renewal'] = (
        (df['days_since_same_type'] >= 330) & (df['days_since_same_type'] <= 400)
    ).astype(int)
    df['likely_semi_renewal'] = (
        (df['days_since_same_type'] >= 150) & (df['days_since_same_type'] <= 200)
    ).astype(int)
    df['days_since_same_type'] = df['days_since_same_type'].fillna(-1)
    return df

# ============================================================
# SEASONAL FEATURES
# ============================================================
def add_seasonal_features(df):
    df            = df.copy()
    df['month']   = df['dat_izdavanja'].dt.month
    df['quarter'] = df['dat_izdavanja'].dt.quarter
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
    return df

# ============================================================
# POPULARITY FEATURES (gradi se samo na train foldu)
# ============================================================
def build_popularity_features(train_df):
    global_pop = train_df['sif_vrsta'].value_counts(normalize=True).to_dict()
    regional_counts = (
        train_df.groupby(['osig_opstina_y', 'sif_vrsta']).size().reset_index(name='cnt')
    )
    regional_counts['regional_pop'] = regional_counts.groupby('osig_opstina_y')['cnt'].transform(
        lambda x: x / x.sum()
    )
    regional_pop = (
        regional_counts.set_index(['osig_opstina_y', 'sif_vrsta'])['regional_pop'].to_dict()
    )
    return global_pop, regional_pop

def apply_popularity_features(df, global_pop, regional_pop):
    df = df.copy()
    df['candidate_global_pop']   = df['candidate_type'].map(global_pop).fillna(0)
    df['candidate_regional_pop'] = (
        df.set_index(['osig_opstina_y', 'candidate_type']).index.map(regional_pop)
    )
    df['candidate_regional_pop'] = df['candidate_regional_pop'].fillna(df['candidate_global_pop'])
    return df

# ============================================================
# SEGMENT MARKOV (gradi se samo na train foldu)
# ============================================================
def build_segment_markov(train_df):
    train_df = train_df.copy()
    train_df['segment'] = (
        train_df['age_bucket'].astype(str) + '_' +
        train_df['ownerType'].astype(str) + '_' +
        train_df['osig_opstina_y'].astype(str)
    )
    rows = []
    for _, g in train_df.groupby('klijent_id'):
        g        = g.sort_values('dat_izdavanja')
        types    = g['sif_vrsta'].tolist()
        segments = g['segment'].tolist()
        for i in range(len(types) - 1):
            rows.append((segments[i], types[i], types[i + 1]))

    out = pd.DataFrame(rows, columns=['segment', 'from_type', 'to_type'])
    out = out.groupby(['segment', 'from_type', 'to_type']).size().reset_index(name='cnt')
    out['segment_markov_prob'] = out.groupby(['segment', 'from_type'])['cnt'].transform(
        lambda x: x / x.sum()
    )
    return out.set_index(['segment', 'from_type', 'to_type'])['segment_markov_prob'].to_dict()

def apply_segment_markov(df, segment_markov_dict):
    df = df.copy()
    df['segment'] = (
        df['age_bucket'].astype(str) + '_' +
        df['ownerType'].astype(str) + '_' +
        df['osig_opstina_y'].astype(str)
    )
    df['segment_markov_prob'] = (
        df.set_index(['segment', 'sif_vrsta', 'candidate_type']).index.map(segment_markov_dict)
    )
    df['segment_markov_prob'] = df['segment_markov_prob'].fillna(0)
    return df.drop('segment', axis=1)

# ============================================================
# HARD NEGATIVE SAMPLING (samo na train foldu)
# ============================================================
def sample_negatives(df, n_hard=3, n_random=2, random_state=42):
    pos = df[df['label'] == 1]
    neg = df[df['label'] == 0]

    hard_neg = (
        neg.groupby(['klijent_id', 'dat_izdavanja'], group_keys=False)
        .apply(lambda x: x.nlargest(n_hard, 'markov_prob'))
    )
    random_neg = (
        neg.groupby(['klijent_id', 'dat_izdavanja'], group_keys=False)
        .apply(lambda x: x.sample(min(n_random, len(x)), random_state=random_state))
    )
    sampled = (
        pd.concat([pos, hard_neg, random_neg])
        .drop_duplicates(subset=['klijent_id', 'dat_izdavanja', 'candidate_type'])
        .sort_values(['klijent_id', 'dat_izdavanja'])
        .reset_index(drop=True)
    )
    print(f"   Sampling: {len(df):,} -> {len(sampled):,} "
          f"(-{(1-len(sampled)/len(df))*100:.1f}%) | "
          f"label rate: {df['label'].mean():.4f} -> {sampled['label'].mean():.4f}")
    return sampled

# ============================================================
# CHUNK BUILDER
# ============================================================
def _build_training_chunks(
    df, future_pairs, mt_dict, candidates, client_history,
    global_pop, regional_pop, segment_markov_dict,
    cluster_map, features, chunk_size=5000, chunks_dir='chunks_temp'
):
    df = df.copy()
    os.makedirs(chunks_dir, exist_ok=True)
    n_chunks     = math.ceil(len(df) / chunk_size)
    saved_chunks = 0

    for i, start in enumerate(tqdm(range(0, len(df), chunk_size), total=n_chunks, desc=chunks_dir)):
        chunk = df.iloc[start:start + chunk_size].copy()

        chunk_dataset = chunk.assign(_key=1).merge(
            candidates.assign(_key=1), on='_key'
        ).drop('_key', axis=1)

        chunk_dataset['markov_prob'] = (
            chunk_dataset.set_index(['sif_vrsta', 'candidate_type']).index.map(mt_dict)
        )
        chunk_dataset['markov_prob'] = chunk_dataset['markov_prob'].fillna(0)

        chunk_dataset = apply_segment_markov(chunk_dataset, segment_markov_dict)
        chunk_dataset = apply_popularity_features(chunk_dataset, global_pop, regional_pop)

        # KMeans cluster feature
        chunk_dataset['client_cluster'] = chunk_dataset['klijent_id'].map(cluster_map).fillna(-1)

        chunk_dataset = chunk_dataset.merge(client_history, on='ponuda_id', how='inner')
        history_cols  = [c for c in client_history.columns if c != 'ponuda_id']
        chunk_dataset[history_cols] = chunk_dataset[history_cols].fillna(0)

        fp_chunk = future_pairs[future_pairs['ponuda_id'].isin(chunk['ponuda_id'])]
        chunk_dataset = chunk_dataset.merge(
            fp_chunk[['ponuda_id', 'candidate_type', 'label', 'is_renewal']],
            on=['ponuda_id', 'candidate_type'], how='left'
        )
        chunk_dataset['label']      = chunk_dataset['label'].fillna(0).astype(int)
        chunk_dataset['is_renewal'] = chunk_dataset['is_renewal'].fillna(0).astype(int)

        available = [c for c in features if c in chunk_dataset.columns]
        chunk_dataset[available].to_pickle(f'{chunks_dir}/chunk_{i}.pkl')
        saved_chunks += 1

        del chunk, chunk_dataset, fp_chunk
        gc.collect()

    return saved_chunks, chunks_dir

def merge_chunks(saved_chunks, chunks_dir):
    dataset = pd.concat(
        [pd.read_pickle(f'{chunks_dir}/chunk_{i}.pkl') for i in range(saved_chunks)],
        ignore_index=True
    )
    print(f"   Shape: {dataset.shape}")
    shutil.rmtree(chunks_dir)
    return dataset

def cap_candidates(df, max_per_group):
    return df.groupby(['klijent_id', 'dat_izdavanja'], group_keys=False).head(max_per_group)

# ============================================================
# FEATURE LISTE
# ============================================================
BASE_FEATURES = [
    'label', 'klijent_id', 'ponuda_id', 'sif_vrsta', 'dat_izdavanja',
    'n_policies_before', 'had_type_before', 'cnt_type_before', 'days_since_last_policy',
    'candidate_type',
    'markov_prob', 'segment_markov_prob',
    'candidate_global_pop', 'candidate_regional_pop',
    'likely_annual_renewal', 'likely_semi_renewal', 'days_since_same_type',
    'month_sin', 'month_cos', 'quarter',
    'is_renewal',
    'client_cluster',   # NOVO: KMeans klaster
    'avg_premium_past', 'avg_insurance_sum_past',
    'age', 'gender', 'ownerType', 'merrige_status', 'is_foreign',
    'birth_place', 'osig_mesto_id_y', 'osig_opstina_y',
    'osig_kanton_y', 'osig_posta_y', 'sif_uloga', 'age_bucket'
]

TRAINING_FEATURES = [
    'n_policies_before', 'had_type_before', 'cnt_type_before', 'days_since_last_policy',
    'candidate_type',
    'markov_prob', 'segment_markov_prob',
    'candidate_global_pop', 'candidate_regional_pop',
    'likely_annual_renewal', 'likely_semi_renewal', 'days_since_same_type',
    'month_sin', 'month_cos', 'quarter',
    'is_renewal',
    'client_cluster',
    'avg_premium_past', 'avg_insurance_sum_past',
    'age', 'gender', 'ownerType', 'merrige_status', 'is_foreign',
    'birth_place', 'osig_mesto_id_y', 'osig_opstina_y',
    'osig_kanton_y', 'osig_posta_y', 'sif_uloga', 'age_bucket'
]

CATEGORICAL_FEATURES = [
    'had_type_before', 'candidate_type', 'gender', 'ownerType', 'merrige_status',
    'is_foreign', 'birth_place', 'osig_mesto_id_y', 'osig_opstina_y',
    'osig_kanton_y', 'osig_posta_y', 'sif_uloga', 'age_bucket', 'client_cluster'
]

# ============================================================
# EVALUACIJSKE FUNKCIJE
# ============================================================
def hit_rate_at_k(preds_all, y_all, group, k=1):
    start = 0; hits = 0; total = 0
    for g in group:
        end       = start + g
        preds     = preds_all[start:end]
        labels    = y_all[start:end]
        top_k_idx = np.argsort(-preds)[:k]
        if np.any(labels[top_k_idx] == 1):
            hits += 1
        total += 1
        start = end
    return hits / total if total > 0 else 0.0

def mrr_at_k(preds_all, y_all, group, k=5):
    start = 0; rr = []
    for g in group:
        end        = start + g
        sorted_idx = np.argsort(-preds_all[start:end])
        labels     = y_all[start:end]
        found      = False
        for rank, idx in enumerate(sorted_idx[:k], 1):
            if labels[idx] == 1:
                rr.append(1.0 / rank); found = True; break
        if not found: rr.append(0.0)
        start = end
    return np.mean(rr) if rr else 0.0

def ndcg_at_k(preds_all, y_all, group, k=3):
    start = 0; total = 0; n = 0
    for g in group:
        end           = start + g
        order         = np.argsort(-preds_all[start:end])
        labels        = y_all[start:end]
        labels_sorted = labels[order][:k]
        dcg           = np.sum(labels_sorted / np.log2(np.arange(2, k + 2)))
        ideal         = np.sort(labels)[::-1][:k]
        idcg          = np.sum(ideal / np.log2(np.arange(2, k + 2)))
        if idcg > 0:
            total += dcg / idcg; n += 1
        start = end
    return total / n if n > 0 else 0.0

def renewal_hit_rate(preds_all, y_all, group, is_renewal_arr, k=1):
    start = 0; hits = 0; total = 0
    for g in group:
        end    = start + g
        labels = y_all[start:end]
        ren    = is_renewal_arr[start:end]
        pos    = np.where(labels == 1)[0]
        if len(pos) > 0 and ren[pos[0]] == 1:
            top_k = np.argsort(-preds_all[start:end])[:k]
            if np.any(labels[top_k] == 1):
                hits += 1
            total += 1
        start = end
    return hits / total if total > 0 else 0.0

def evaluate(model, X, y_series, group, dataset=None, label=''):
    preds  = model.predict(X)
    y      = y_series.values
    print(f"\n{'='*50}")
    print(f"EVALUACIJA: {label}")
    print(f"{'='*50}")
    for k in [1, 3, 5]:
        hr   = hit_rate_at_k(preds, y, group, k)
        mrr  = mrr_at_k(preds, y, group, k)
        ndcg = ndcg_at_k(preds, y, group, k)
        print(f"HR@{k}: {hr:.4f} | MRR@{k}: {mrr:.4f} | NDCG@{k}: {ndcg:.4f}")
    if dataset is not None and 'is_renewal' in dataset.columns:
        rhr = renewal_hit_rate(preds, y, group, dataset['is_renewal'].values)
        print(f"Renewal HR@1: {rhr:.4f}")
    return preds

# ============================================================
# GLAVNI PIPELINE
# ============================================================
print("\n" + "=" * 60)
print("POCETAK PIPELINE-A")
print("=" * 60)

df = policy_client_data.copy()
df = df.groupby('klijent_id').filter(lambda x: len(x) > 1)
print(f'Polisa: {len(df):,} | Klijenata: {df["klijent_id"].nunique():,}')

df['dat_izdavanja'] = pd.to_datetime(df['dat_izdavanja'])
df = df.sort_values(['klijent_id', 'dat_izdavanja']).reset_index(drop=True)

# History features
df['days_since_last_policy'] = df.groupby('klijent_id')['dat_izdavanja'].diff().dt.days
df['n_policies_before']      = df.groupby('klijent_id').cumcount()
df['cnt_type_before']        = df.groupby(['klijent_id', 'sif_vrsta']).cumcount()
df['had_type_before']        = (df['cnt_type_before'] > 0).astype(int)
g = df.groupby('klijent_id')
df['avg_premium_past']       = g['premija_ukupno'].transform(
    lambda x: x.shift(1).rolling(3, min_periods=1).mean()
)
df['avg_insurance_sum_past'] = g['suma_osiguranja'].transform(
    lambda x: x.shift(1).rolling(3, min_periods=1).mean()
)
df = add_renewal_features(df)
df = add_seasonal_features(df)

# NOVO: KMeans klasteri - gradi se na cijelom df (demografija ne leakuje)
print("\n✅ Gradim KMeans klastere...")
cluster_map, kmeans_model, cluster_scaler, cluster_feature_cols = build_client_clusters(
    df, n_clusters=8
)
df['client_cluster'] = df['klijent_id'].map(cluster_map).fillna(-1)

# Kandidati
all_types  = df['sif_vrsta'].unique()
candidates = pd.DataFrame({'candidate_type': all_types})
print(f"\nUnique policy types: {len(all_types)}")
print(f"Distribucija tipova polisa:\n{df['sif_vrsta'].value_counts(normalize=True).round(3)}")

# ============================================================
# TEMPORAL CROSS VALIDATION
# Koristimo TimeSeriesSplit da izbjegnemo problem distribucije.
# Svaki fold: train = sve do datuma X, val = sljedeci period.
# Ovako model vidi razlicite sezonalne periode i generalizuje bolje.
# ============================================================
print("\n" + "=" * 60)
print("TEMPORAL CROSS VALIDATION")
print("=" * 60)

# Sortiraj klijente po vremenu prve polise - osnova za split
unique_dates = df['dat_izdavanja'].sort_values().unique()
n_splits     = 4  # 4 folda = 4 razlicita val perioda

# Rucni temporal split - dijelimo po datumima ne po redovima
total_days  = (unique_dates[-1] - unique_dates[0]).astype('timedelta64[D]').astype(int)
fold_size   = total_days // (n_splits + 1)

fold_results = []

for fold in range(n_splits):
    cutoff_days  = fold_size * (fold + 1)
    cutoff_date  = unique_dates[0] + np.timedelta64(cutoff_days, 'D')
    val_end_days = fold_size * (fold + 2)
    val_end_date = unique_dates[0] + np.timedelta64(val_end_days, 'D')

    train_df = df[df['dat_izdavanja'] < cutoff_date].copy()
    val_df   = df[(df['dat_izdavanja'] >= cutoff_date) &
                  (df['dat_izdavanja'] < val_end_date)].copy()

    if len(train_df) < 500 or len(val_df) < 100:
        print(f"Fold {fold+1}: preskacam (premalo podataka)")
        continue

    print(f"\n--- FOLD {fold+1}/{n_splits} ---")
    print(f"Train: {train_df['dat_izdavanja'].min().date()} -> {train_df['dat_izdavanja'].max().date()} ({len(train_df):,} polisa)")
    print(f"Val:   {val_df['dat_izdavanja'].min().date()} -> {val_df['dat_izdavanja'].max().date()} ({len(val_df):,} polisa)")

    # Provjera distribucije po foldu
    train_dist = train_df['sif_vrsta'].value_counts(normalize=True)
    val_dist   = val_df['sif_vrsta'].value_counts(normalize=True)
    dist_diff  = (train_dist - val_dist).abs().mean()
    print(f"Distribucija razlika train/val: {dist_diff:.4f} (manje = bolje)")

    # Lookup tablice - SAMO na train foldu
    markov_transitions  = _build_markov_with_decay(train_df)
    mt_dict             = markov_transitions.set_index(['from_type', 'to_type'])['prob'].to_dict()
    global_pop, reg_pop = build_popularity_features(train_df)
    seg_markov_dict     = build_segment_markov(train_df)
    future_pairs_train  = _build_future_pairs(train_df)
    future_pairs_val    = _build_future_pairs(val_df)
    client_hist_train   = _build_client_history_matrix(train_df)
    client_hist_val     = _build_client_history_matrix(val_df)

    history_type_cols = [c for c in client_hist_train.columns if c != 'ponuda_id']
    features          = BASE_FEATURES + history_type_cols
    training_features = TRAINING_FEATURES + history_type_cols

    # Ukloni zadnju polisu
    train_df = train_df[train_df.groupby('klijent_id').cumcount(ascending=False) != 0]
    val_df   = val_df[val_df.groupby('klijent_id').cumcount(ascending=False) != 0]

    if len(train_df) < 100 or len(val_df) < 20:
        print(f"Fold {fold+1}: preskacam nakon uklanjanja zadnje polise")
        continue

    gc.collect()

    # Chunks
    sc_train, td = _build_training_chunks(
        train_df, future_pairs_train, mt_dict, candidates, client_hist_train,
        global_pop, reg_pop, seg_markov_dict, cluster_map, features,
        chunks_dir=f'chunks_train_f{fold}'
    )
    sc_val, vd = _build_training_chunks(
        val_df, future_pairs_val, mt_dict, candidates, client_hist_val,
        global_pop, reg_pop, seg_markov_dict, cluster_map, features,
        chunks_dir=f'chunks_val_f{fold}'
    )

    train_dataset = merge_chunks(sc_train, td)
    val_dataset   = merge_chunks(sc_val, vd)

    for col in CATEGORICAL_FEATURES:
        if col in train_dataset.columns:
            train_dataset[col] = train_dataset[col].astype('category')
        if col in val_dataset.columns:
            val_dataset[col] = val_dataset[col].astype('category')

    max_pg        = len(all_types) * 7
    train_dataset = cap_candidates(train_dataset, max_pg)
    val_dataset   = cap_candidates(val_dataset, max_pg)
    train_dataset = train_dataset.sort_values(['klijent_id', 'dat_izdavanja']).reset_index(drop=True)
    val_dataset   = val_dataset.sort_values(['klijent_id', 'dat_izdavanja']).reset_index(drop=True)

    # Negative sampling - samo train
    train_dataset = sample_negatives(train_dataset)
    train_dataset = train_dataset.sort_values(['klijent_id', 'dat_izdavanja']).reset_index(drop=True)

    avail_train = [c for c in training_features if c in train_dataset.columns]
    avail_val   = [c for c in training_features if c in val_dataset.columns]

    X_train = train_dataset[avail_train].copy()
    X_val   = val_dataset[avail_val].copy()

    for col in CATEGORICAL_FEATURES:
        if col in X_train.columns:
            X_train[col] = X_train[col].astype('category').cat.codes
        if col in X_val.columns:
            X_val[col] = X_val[col].astype('category').cat.codes

    y_train = train_dataset['label'].astype(int)
    y_val   = val_dataset['label'].astype(int)

    group_train = train_dataset.groupby(['klijent_id', 'dat_izdavanja']).size().to_numpy()
    group_val   = val_dataset.groupby(['klijent_id', 'dat_izdavanja']).size().to_numpy()

    assert sum(group_train) == len(X_train)
    assert sum(group_val)   == len(X_val)

    # MODEL
    model = LGBMRanker(
        objective='lambdarank',
        n_estimators=500,
        learning_rate=0.05,
        num_leaves=20,
        min_child_samples=15,
        reg_alpha=0.1,
        reg_lambda=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
    )
    model.fit(
        X_train, y_train,
        group=group_train,
        eval_set=[(X_val, y_val)],
        eval_group=[group_val],
        eval_at=[1, 3, 5],
        callbacks=[log_evaluation(20), early_stopping(stopping_rounds=50, verbose=False)]
    )

    preds_val = evaluate(model, X_val, y_val, group_val,
                         dataset=val_dataset, label=f'Fold {fold+1} VAL')

    fold_results.append({
        'fold':  fold + 1,
        'hr1':   hit_rate_at_k(preds_val, y_val.values, group_val, k=1),
        'hr3':   hit_rate_at_k(preds_val, y_val.values, group_val, k=3),
        'hr5':   hit_rate_at_k(preds_val, y_val.values, group_val, k=5),
        'mrr5':  mrr_at_k(preds_val, y_val.values, group_val, k=5),
        'model': model,
        'features': avail_train
    })

    del train_dataset, val_dataset, X_train, X_val
    gc.collect()

# ============================================================
# FINALNI REZULTATI KROZ SVE FOLDOVE
# ============================================================
print("\n" + "=" * 60)
print("FINALNI REZULTATI CROSS VALIDACIJE")
print("=" * 60)

results_df = pd.DataFrame([{k: v for k, v in r.items() if k != 'model' and k != 'features'}
                            for r in fold_results])
print(results_df.to_string(index=False))
print(f"\nProsjecni HR@1: {results_df['hr1'].mean():.4f} ± {results_df['hr1'].std():.4f}")
print(f"Prosjecni HR@3: {results_df['hr3'].mean():.4f} ± {results_df['hr3'].std():.4f}")
print(f"Prosjecni HR@5: {results_df['hr5'].mean():.4f} ± {results_df['hr5'].std():.4f}")

# Uzmi model sa najboljim HR@3 kao finalni
best_fold   = max(fold_results, key=lambda x: x['hr3'])
final_model = best_fold['model']
print(f"\nNajbolji model: Fold {best_fold['fold']} (HR@3={best_fold['hr3']:.4f})")

# Feature importance finalnog modela
fi = pd.DataFrame({
    'feature':    best_fold['features'],
    'importance': final_model.feature_importances_
}).sort_values('importance', ascending=False)
print("\nTop 15 feature importances:")
print(fi.head(15).to_string(index=False))

# ============================================================
# INFERENCE FUNKCIJA
# ============================================================
def predict_next_policy(
    klijent_id, current_ponuda_id, current_type,
    model, candidates, mt_dict, global_pop, regional_pop,
    segment_markov_dict, cluster_map, client_row, training_features
):
    pred_df = candidates.copy()
    pred_df['klijent_id'] = klijent_id
    pred_df['ponuda_id']  = current_ponuda_id
    pred_df['sif_vrsta']  = current_type

    for col in client_row.index:
        if col not in pred_df.columns:
            pred_df[col] = client_row[col]

    pred_df['markov_prob'] = (
        pred_df.set_index(['sif_vrsta', 'candidate_type']).index.map(mt_dict)
    )
    pred_df['markov_prob']   = pred_df['markov_prob'].fillna(0)
    pred_df['client_cluster'] = cluster_map.get(klijent_id, -1)
    pred_df['is_renewal']    = (pred_df['candidate_type'] == current_type).astype(int)

    pred_df = apply_segment_markov(pred_df, segment_markov_dict)
    pred_df = apply_popularity_features(pred_df, global_pop, regional_pop)

    avail  = [c for c in training_features if c in pred_df.columns]
    X_pred = pred_df[avail].copy()
    for col in CATEGORICAL_FEATURES:
        if col in X_pred.columns:
            X_pred[col] = X_pred[col].astype('category').cat.codes

    pred_df['score'] = model.predict(X_pred)

    return (
        pred_df[['candidate_type', 'score', 'markov_prob',
                 'segment_markov_prob', 'candidate_global_pop', 'is_renewal']]
        .sort_values('score', ascending=False)
        .reset_index(drop=True)
    )

print("\n✅ Script spreman za pokretanje.")
